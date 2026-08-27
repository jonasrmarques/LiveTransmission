"""Business logic for transmission rooms."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from transmissao.models import ParticipanteSala, Sala
from transmissao.room_access import (
    SalaAccessDeniedError,
    SalaNotFoundError,
    get_sala_by_codigo,
    user_is_owner,
)
from transmissao import signaling

User = get_user_model()


class SalaServiceError(Exception):
    """Base error for room operations."""


class SalaClosedError(SalaServiceError):
    """Raised when an operation is invalid on a closed room."""


class ParticipanteNotFoundError(SalaServiceError):
    """Raised when a participant is not in the room."""


def ensure_room_open(sala: Sala) -> None:
    if not sala.is_active:
        raise SalaClosedError("Esta sala foi encerrada.")


@transaction.atomic
def create_sala(*, owner: User, nome: str) -> Sala:
    sala = Sala.objects.create(proprietario=owner, nome=nome.strip())
    ParticipanteSala.objects.create(sala=sala, usuario=owner)
    return sala


@transaction.atomic
def join_sala(*, sala: Sala, user: User) -> ParticipanteSala:
    ensure_room_open(sala)

    participante, created = ParticipanteSala.objects.get_or_create(
        sala=sala,
        usuario=user,
        defaults={"ativo": True},
    )
    if not created and not participante.ativo:
        participante.ativo = True
        participante.left_at = None
        participante.save(update_fields=["ativo", "left_at"])

    signaling.notify_participant_joined(sala=sala, user=user)
    return participante


@transaction.atomic
def join_sala_by_code(*, codigo: str, user: User) -> Sala:
    sala = get_sala_by_codigo(codigo)
    join_sala(sala=sala, user=user)
    return sala


@transaction.atomic
def leave_sala(*, sala: Sala, user: User) -> None:
    """Leave a room. Idempotent: already-left / closed rooms succeed quietly."""
    try:
        participante = ParticipanteSala.objects.get(
            sala=sala,
            usuario=user,
            ativo=True,
        )
    except ParticipanteSala.DoesNotExist:
        # Room may already be encerrada (encerrar marks everyone inactive).
        return

    participante.ativo = False
    participante.left_at = timezone.now()
    participante.save(update_fields=["ativo", "left_at"])

    if user_is_owner(sala, user) and sala.is_active:
        end_transmission(sala=sala, owner=user)
    else:
        signaling.notify_participant_left(sala=sala, user=user)


@transaction.atomic
def remove_participant(*, sala: Sala, owner: User, participant: User) -> None:
    if not user_is_owner(sala, owner):
        raise SalaAccessDeniedError("Apenas o proprietário pode remover participantes.")
    if user_is_owner(sala, participant):
        raise SalaServiceError("O proprietário não pode ser removido da sala.")

    try:
        registro = ParticipanteSala.objects.get(
            sala=sala,
            usuario=participant,
            ativo=True,
        )
    except ParticipanteSala.DoesNotExist as exc:
        raise ParticipanteNotFoundError("Participante não encontrado na sala.") from exc

    registro.ativo = False
    registro.left_at = timezone.now()
    registro.save(update_fields=["ativo", "left_at"])
    signaling.notify_participant_removed(sala=sala, user_id=participant.id)


@transaction.atomic
def start_transmission(*, sala: Sala, owner: User) -> Sala:
    if not user_is_owner(sala, owner):
        raise SalaAccessDeniedError("Apenas o proprietário pode iniciar a transmissão.")
    ensure_room_open(sala)

    sala.status = Sala.Status.TRANSMITINDO
    sala.save(update_fields=["status", "updated_at"])
    signaling.notify_transmission_started(sala)
    return sala


@transaction.atomic
def end_transmission(*, sala: Sala, owner: User) -> Sala:
    if not user_is_owner(sala, owner):
        raise SalaAccessDeniedError("Apenas o proprietário pode encerrar a transmissão.")

    sala.status = Sala.Status.ENCERRADA
    sala.save(update_fields=["status", "updated_at"])

    ParticipanteSala.objects.filter(sala=sala, ativo=True).update(
        ativo=False,
        left_at=timezone.now(),
    )
    signaling.notify_transmission_ended(sala)
    return sala


def list_user_salas(user: User):
    return (
        Sala.objects.filter(participantes__usuario=user, participantes__ativo=True)
        .distinct()
        .select_related("proprietario")
    )
