import unittest

from src.shared.infrastructure.socket_io.socket_gateway import SocketGateway


class DummySIO:
    def __init__(self):
        self.calls = []

    def emit(self, event, data, to=None, skip_sid=None, namespace=None, room=None):
        self.calls.append({
            "event": event,
            "data": data,
            "to": to,
            "skip_sid": skip_sid,
            "namespace": namespace,
            "room": room,
        })


class SocketGatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_emit_async_uses_sync_socketio_emit(self):
        gateway = SocketGateway()
        gateway.sio = DummySIO()

        await gateway.emit_async(
            "player_joined",
            {"player_id": "abc"},
            to="room_123",
            skip_sid="sid-1",
        )

        self.assertEqual(len(gateway.sio.calls), 1)
        self.assertEqual(gateway.sio.calls[0]["event"], "player_joined")
        self.assertEqual(gateway.sio.calls[0]["to"], "room_123")
        self.assertEqual(gateway.sio.calls[0]["skip_sid"], "sid-1")


if __name__ == "__main__":
    unittest.main()
