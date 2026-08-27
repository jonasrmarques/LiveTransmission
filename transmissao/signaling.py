"""WebSocket signaling for room events and WebRTC (ETAPA 4+)."""

from __future__ import annotations

import uuid
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

from transmissao.models import Sala
from transmissao.room_access import (
    SalaNotFoundError,
    ensure_room_access,
    get_sala_by_identificador,
    list_active_participants,
    user_is_owner,
)

User = get_user_model()

# Outbound event types consumed by the browser / future React client.
EVENT_ROOM_STATE = "room.state"
EVENT_PRESENCE_ONLINE = "presence.online"
EVENT_PRESENCE_OFFLINE = "presence.offline"
EVENT_PARTICIPANT_JOINED = "participant.joined"
EVENT_PARTICIPANT_LEFT = "participant.left"
EVENT_TRANSMISSION_STARTED = "transmission.started"
EVENT_TRANSMISSION_ENDED = "transmission.ended"
EVENT_PARTICIPANT_REMOVED = "participant.removed"
EVENT_STREAM_STARTED = "stream.started"
EVENT_STREAM_STOPPED = "stream.stopped"

# WebRTC signaling (relayed P2P).
EVENT_WEBRTC_OFFER = "webrtc.offer"
EVENT_WEBRTC_ANSWER = "webrtc.answer"
EVENT_WEBRTC_ICE = "webrtc.ice_candidate"
EVENT_VIEWER_READY = "viewer.ready"

WEBRTC_EVENT_TYPES = {
    EVENT_WEBRTC_OFFER,
    EVENT_WEBRTC_ANSWER,
    EVENT_WEBRTC_ICE,
    EVENT_VIEWER_READY,
    EVENT_STREAM_STARTED,
    EVENT_STREAM_STOPPED,
}

ALLOWED_INBOUND_TYPES = WEBRTC_EVENT_TYPES


class SignalingError(Exception):
    """Invalid signaling payload or permission failure."""


def room_group_name(room_id: str | uuid.UUID) -> str:
    return f"sala_{room_id}"


def serialize_participant(participante) -> dict[str, Any]:
    return {
        "user_id": participante.usuario_id,
        "username": participante.usuario.username,
        "is_owner": participante.usuario_id == participante.sala.proprietario_id,
    }


def build_room_state(sala: Sala) -> dict[str, Any]:
    participantes = list_active_participants(sala)
    return {
        "type": EVENT_ROOM_STATE,
        "room": {
            "identificador": str(sala.identificador),
            "nome": sala.nome,
            "status": sala.status,
            "codigo_convite": sala.codigo_convite,
            "proprietario_id": sala.proprietario_id,
        },
        "participantes": [serialize_participant(p) for p in participantes],
    }


def authorize_room_connection(*, room_id: str | uuid.UUID, user: User) -> Sala:
    if not user.is_authenticated:
        raise SignalingError("Autenticação necessária.")
    try:
        sala = get_sala_by_identificador(room_id)
    except SalaNotFoundError as exc:
        raise SignalingError(str(exc)) from exc
    try:
        ensure_room_access(sala, user)
    except Exception as exc:
        raise SignalingError(str(exc)) from exc
    return sala


def build_presence_event(*, event_type: str, sala: Sala, user: User) -> dict[str, Any]:
    return {
        "type": event_type,
        "room_id": str(sala.identificador),
        "user": {
            "id": user.id,
            "username": user.username,
            "is_owner": user_is_owner(sala, user),
        },
    }


def process_inbound_message(
    *,
    sala: Sala,
    sender: User,
    message: dict[str, Any],
) -> dict[str, Any]:
    """Validate and normalize an inbound WebSocket message."""
    event_type = message.get("type")
    if event_type not in ALLOWED_INBOUND_TYPES:
        raise SignalingError("Tipo de mensagem não suportado.")

    payload = message.get("payload")
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise SignalingError("Payload inválido.")

    target_user_id = message.get("target_user_id")
    if target_user_id is not None:
        try:
            target_user_id = int(target_user_id)
        except (TypeError, ValueError) as exc:
            raise SignalingError("Destinatário inválido.") from exc
        if not list_active_participants(sala).filter(usuario_id=target_user_id).exists():
            raise SignalingError("Destinatário não está na sala.")

    # Stream announcements are room-wide; WebRTC SDP/ICE is peer-targeted.
    if event_type in {EVENT_WEBRTC_OFFER, EVENT_WEBRTC_ANSWER, EVENT_WEBRTC_ICE}:
        if target_user_id is None:
            raise SignalingError("Sinalização WebRTC exige target_user_id.")
    if event_type == EVENT_VIEWER_READY and target_user_id is None:
        # Default target: room owner (presenter).
        target_user_id = sala.proprietario_id

    if event_type in {EVENT_STREAM_STARTED, EVENT_STREAM_STOPPED}:
        if not user_is_owner(sala, sender):
            raise SignalingError("Apenas o proprietário controla o stream.")

    return {
        "type": event_type,
        "room_id": str(sala.identificador),
        "sender_id": sender.id,
        "sender_username": sender.username,
        "target_user_id": target_user_id,
        "payload": payload,
    }


def broadcast_room_event(*, room_id: str | uuid.UUID, event: dict[str, Any]) -> None:
    """Send an event to every WebSocket connected to the room group."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        room_group_name(room_id),
        {"type": "room.event", "payload": event},
    )


def broadcast_room_state(sala: Sala) -> None:
    broadcast_room_event(room_id=sala.identificador, event=build_room_state(sala))


def notify_transmission_started(sala: Sala) -> None:
    broadcast_room_event(
        room_id=sala.identificador,
        event={
            "type": EVENT_TRANSMISSION_STARTED,
            "room_id": str(sala.identificador),
            "status": sala.status,
        },
    )
    broadcast_room_state(sala)


def notify_transmission_ended(sala: Sala) -> None:
    broadcast_room_event(
        room_id=sala.identificador,
        event={
            "type": EVENT_TRANSMISSION_ENDED,
            "room_id": str(sala.identificador),
            "status": sala.status,
        },
    )
    broadcast_room_state(sala)


def notify_participant_removed(*, sala: Sala, user_id: int) -> None:
    broadcast_room_event(
        room_id=sala.identificador,
        event={
            "type": EVENT_PARTICIPANT_REMOVED,
            "room_id": str(sala.identificador),
            "user_id": user_id,
        },
    )
    broadcast_room_state(sala)


def notify_participant_joined(*, sala: Sala, user: User) -> None:
    broadcast_room_event(
        room_id=sala.identificador,
        event=build_presence_event(
            event_type=EVENT_PARTICIPANT_JOINED,
            sala=sala,
            user=user,
        ),
    )
    broadcast_room_state(sala)


def notify_participant_left(*, sala: Sala, user: User) -> None:
    broadcast_room_event(
        room_id=sala.identificador,
        event=build_presence_event(
            event_type=EVENT_PARTICIPANT_LEFT,
            sala=sala,
            user=user,
        ),
    )
    broadcast_room_state(sala)
