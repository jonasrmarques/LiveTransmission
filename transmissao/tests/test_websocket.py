"""WebSocket tests for room signaling."""

import asyncio

from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings

from transmissao.consumers import SalaConsumer
from transmissao.services import create_sala, join_sala
from usuarios.services import register_user


@override_settings(
    CHANNEL_LAYERS={
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
)
class SalaWebSocketTests(TransactionTestCase):
    def setUp(self):
        self.owner = register_user(
            username="owner",
            email="owner@example.com",
            password="Str0ng-Pass!",
        )
        self.guest = register_user(
            username="guest",
            email="guest@example.com",
            password="Str0ng-Pass!",
        )
        self.outsider = register_user(
            username="outsider",
            email="outsider@example.com",
            password="Str0ng-Pass!",
        )
        self.sala = create_sala(owner=self.owner, nome="WS Sala")
        join_sala(sala=self.sala, user=self.guest)

    async def _connect(self, user):
        communicator = WebsocketCommunicator(
            SalaConsumer.as_asgi(),
            f"/ws/transmissao/sala/{self.sala.identificador}/",
        )
        communicator.scope["user"] = user
        communicator.scope["url_route"] = {
            "kwargs": {"identificador": str(self.sala.identificador)},
        }
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        return communicator

    def test_authenticated_user_receives_room_state(self):
        async def run():
            communicator = await self._connect(self.owner)
            response = await communicator.receive_json_from()
            self.assertEqual(response["type"], "room.state")
            self.assertEqual(response["room"]["nome"], "WS Sala")
            await communicator.disconnect()

        asyncio.run(run())

    def test_unauthenticated_connection_rejected(self):
        async def run():
            from django.contrib.auth.models import AnonymousUser

            communicator = WebsocketCommunicator(
                SalaConsumer.as_asgi(),
                f"/ws/transmissao/sala/{self.sala.identificador}/",
            )
            communicator.scope["user"] = AnonymousUser()
            communicator.scope["url_route"] = {
                "kwargs": {"identificador": str(self.sala.identificador)},
            }
            connected, code = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(code, 4401)

        asyncio.run(run())

    def test_non_participant_connection_rejected(self):
        async def run():
            communicator = WebsocketCommunicator(
                SalaConsumer.as_asgi(),
                f"/ws/transmissao/sala/{self.sala.identificador}/",
            )
            communicator.scope["user"] = self.outsider
            communicator.scope["url_route"] = {
                "kwargs": {"identificador": str(self.sala.identificador)},
            }
            connected, code = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(code, 4403)

        asyncio.run(run())

    def test_presence_online_broadcast_to_other_client(self):
        async def run():
            owner_comm = await self._connect(self.owner)
            await owner_comm.receive_json_from()

            guest_comm = await self._connect(self.guest)
            await guest_comm.receive_json_from()

            event = await owner_comm.receive_json_from()
            self.assertEqual(event["type"], "presence.online")
            self.assertEqual(event["user"]["username"], "guest")

            await owner_comm.disconnect()
            await guest_comm.disconnect()

        asyncio.run(run())

    def test_invalid_signaling_message_returns_error(self):
        async def run():
            communicator = await self._connect(self.owner)
            await communicator.receive_json_from()
            await communicator.send_json_to({"type": "invalid.type", "payload": {}})
            response = await communicator.receive_json_from()
            self.assertEqual(response["type"], "error")
            await communicator.disconnect()

        asyncio.run(run())

    def test_stream_started_broadcast(self):
        async def run():
            owner_comm = await self._connect(self.owner)
            await owner_comm.receive_json_from()
            guest_comm = await self._connect(self.guest)
            await guest_comm.receive_json_from()
            await owner_comm.receive_json_from()  # presence.online

            await owner_comm.send_json_to(
                {"type": "stream.started", "payload": {"has_audio": True}}
            )
            event = await guest_comm.receive_json_from()
            self.assertEqual(event["type"], "stream.started")
            self.assertTrue(event["payload"]["has_audio"])

            await owner_comm.disconnect()
            await guest_comm.disconnect()

        asyncio.run(run())

    def test_viewer_ready_targets_owner(self):
        async def run():
            owner_comm = await self._connect(self.owner)
            await owner_comm.receive_json_from()
            guest_comm = await self._connect(self.guest)
            await guest_comm.receive_json_from()
            await owner_comm.receive_json_from()

            await guest_comm.send_json_to({"type": "viewer.ready", "payload": {}})
            event = await owner_comm.receive_json_from()
            self.assertEqual(event["type"], "viewer.ready")
            self.assertEqual(event["sender_id"], self.guest.id)
            self.assertEqual(event["target_user_id"], self.owner.id)

            await owner_comm.disconnect()
            await guest_comm.disconnect()

        asyncio.run(run())

    def test_guest_cannot_announce_stream(self):
        async def run():
            guest_comm = await self._connect(self.guest)
            await guest_comm.receive_json_from()
            await guest_comm.send_json_to({"type": "stream.started", "payload": {}})
            response = await guest_comm.receive_json_from()
            self.assertEqual(response["type"], "error")
            await guest_comm.disconnect()

        asyncio.run(run())

    def test_webrtc_signaling_relay(self):
        async def run():
            owner_comm = await self._connect(self.owner)
            await owner_comm.receive_json_from()
            guest_comm = await self._connect(self.guest)
            await guest_comm.receive_json_from()
            await owner_comm.receive_json_from()

            await owner_comm.send_json_to(
                {
                    "type": "webrtc.offer",
                    "target_user_id": self.guest.id,
                    "payload": {"sdp": "test-offer"},
                }
            )

            relayed = await guest_comm.receive_json_from()
            self.assertEqual(relayed["type"], "webrtc.offer")
            self.assertEqual(relayed["payload"]["sdp"], "test-offer")

            await owner_comm.disconnect()
            await guest_comm.disconnect()

        asyncio.run(run())
