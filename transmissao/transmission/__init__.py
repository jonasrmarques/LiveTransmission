"""
Transmission transport abstraction.

P2P is the MVP implementation (ETAPA 5). Business rules stay in services.py;
this package isolates how media is transported so an SFU can replace P2P later.

Browser-side media lives in static/js/transmissao/webrtc.js and talks to
Channels only for signaling (offer/answer/ICE). Replacing P2P with LiveKit /
mediasoup / Janus should keep REST room APIs and most of signaling events.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class SignalingMessage:
    """Normalized signaling payload exchanged between peers."""

    type: str
    payload: dict[str, Any]
    sender_id: int | str | None = None
    target_id: int | str | None = None


class TransmissionBackend(ABC):
    """Interface for room media transport (P2P today, SFU tomorrow)."""

    name: str = "abstract"

    @abstractmethod
    def join_room(self, *, room_id: str, user_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def leave_room(self, *, room_id: str, user_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def relay_signaling(self, message: SignalingMessage) -> None:
        raise NotImplementedError


class P2PTransmissionBackend(TransmissionBackend):
    """
    Mesh P2P: presenter creates one RTCPeerConnection per viewer.

    Actual PeerConnections run in the browser. Django only relays signaling
    via WebSockets (see transmissao.signaling / consumers).
    """

    name = "p2p"

    def join_room(self, *, room_id: str, user_id: str) -> None:
        return None

    def leave_room(self, *, room_id: str, user_id: str) -> None:
        return None

    def relay_signaling(self, message: SignalingMessage) -> None:
        # Relay is handled by SalaConsumer + signaling.process_inbound_message.
        return None


def get_transmission_backend() -> TransmissionBackend:
    """Factory for the active transmission backend."""
    return P2PTransmissionBackend()
