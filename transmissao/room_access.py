"""Shared room access helpers (used by services, signaling and permissions)."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from transmissao.models import ParticipanteSala, Sala

User = get_user_model()


class SalaNotFoundError(Exception):
    """Raised when a room does not exist."""


class SalaAccessDeniedError(Exception):
    """Raised when a user cannot access a room."""


def get_sala_by_identificador(identificador) -> Sala:
    try:
        return Sala.objects.get(identificador=identificador)
    except Sala.DoesNotExist as exc:
        raise SalaNotFoundError("Sala não encontrada.") from exc


def get_sala_by_codigo(codigo: str) -> Sala:
    try:
        return Sala.objects.get(codigo_convite__iexact=codigo.strip())
    except Sala.DoesNotExist as exc:
        raise SalaNotFoundError("Código de convite inválido.") from exc


def user_is_participant(sala: Sala, user: User) -> bool:
    return ParticipanteSala.objects.filter(
        sala=sala,
        usuario=user,
        ativo=True,
    ).exists()


def user_is_owner(sala: Sala, user: User) -> bool:
    return sala.proprietario_id == user.id


def ensure_room_access(sala: Sala, user: User) -> None:
    if not user_is_owner(sala, user) and not user_is_participant(sala, user):
        raise SalaAccessDeniedError("Você não tem acesso a esta sala.")


def list_active_participants(sala: Sala):
    return ParticipanteSala.objects.filter(
        sala=sala,
        ativo=True,
    ).select_related("usuario")
