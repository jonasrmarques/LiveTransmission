"""WebSocket consumers for room signaling."""

from __future__ import annotations

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from transmissao.signaling import (
    SignalingError,
    authorize_room_connection,
    build_presence_event,
    build_room_state,
    EVENT_PRESENCE_OFFLINE,
    EVENT_PRESENCE_ONLINE,
    process_inbound_message,
    room_group_name,
)

logger = logging.getLogger(__name__)


class SalaConsumer(AsyncWebsocketConsumer):
    """Real-time events and WebRTC signaling for a private room."""

    async def connect(self):
        self.user = self.scope["user"]
        self.room_id = self.scope["url_route"]["kwargs"]["identificador"]
        self.group_name = room_group_name(self.room_id)

        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        try:
            self.sala = await sync_to_async(authorize_room_connection)(
                room_id=self.room_id,
                user=self.user,
            )
        except SignalingError:
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        room_state = await sync_to_async(build_room_state)(self.sala)
        await self.send(text_data=json.dumps(room_state))

        presence_event = await sync_to_async(build_presence_event)(
            event_type=EVENT_PRESENCE_ONLINE,
            sala=self.sala,
            user=self.user,
        )
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "room.event",
                "payload": presence_event,
                "exclude_channel": self.channel_name,
            },
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        if (
            hasattr(self, "sala")
            and hasattr(self, "user")
            and self.user.is_authenticated
        ):
            presence_event = await sync_to_async(build_presence_event)(
                event_type=EVENT_PRESENCE_OFFLINE,
                sala=self.sala,
                user=self.user,
            )
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "room.event",
                    "payload": presence_event,
                },
            )

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            message = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "detail": "JSON inválido."}))
            return

        try:
            event = await sync_to_async(process_inbound_message)(
                sala=self.sala,
                sender=self.user,
                message=message,
            )
        except SignalingError as exc:
            await self.send(text_data=json.dumps({"type": "error", "detail": str(exc)}))
            return

        await self.channel_layer.group_send(
            self.group_name,
            {"type": "room.event", "payload": event},
        )

    async def room_event(self, event):
        if event.get("exclude_channel") == self.channel_name:
            return

        payload = event["payload"]
        target_user_id = payload.get("target_user_id")
        sender_id = payload.get("sender_id")
        if target_user_id is not None:
            if self.user.id not in (target_user_id, sender_id):
                return

        await self.send(text_data=json.dumps(payload))
