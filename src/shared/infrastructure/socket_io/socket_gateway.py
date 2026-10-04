"""
Socket.io gateway - Real-time communication adapter (ASGI)
"""
import inspect
import logging
from typing import Callable, Optional, Dict, Any
from socketio import AsyncServer

logger = logging.getLogger(__name__)


class SocketGateway:
    """Socket.io gateway for real-time communication"""

    def __init__(self):
        self.sio = AsyncServer(
            async_mode="asgi",
            cors_allowed_origins=[
                "http://localhost:2000",
                "http://localhost:2500",
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:5000",
                "http://127.0.0.1:2000",
                "http://127.0.0.1:2500",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5000",
                "https://*",
            ],
            ping_timeout=60,
            ping_interval=25,
            engineio_logger=False,
            logger=False,
        )
    def on(self, event: str, namespace: Optional[str] = None) -> Callable:
        """Register event handler"""
        return self.sio.on(event, namespace=namespace)

    def emit(
        self,
        event: str,
        data: Dict[str, Any],
        to: Optional[str] = None,
        skip_sid: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """Emit event to client(s)"""
        self.sio.emit(event, data, to=to, skip_sid=skip_sid, namespace=namespace)

    async def emit_async(
        self,
        event: str,
        data: Dict[str, Any],
        to: Optional[str] = None,
        skip_sid: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """Emit event asynchronously"""
        await self.sio.emit(event, data, to=to, skip_sid=skip_sid, namespace=namespace)

    async def enter_room(self, sid: str, room: str, namespace: Optional[str] = None) -> None:
        """Add a client to a room.

        ``enter_room`` is a plain method up to python-socketio 5.9.x and became
        a coroutine in 5.10, so the result is only awaited when awaitable.
        """
        result = self.sio.enter_room(sid, room, namespace=namespace)
        if inspect.isawaitable(result):
            await result

    async def leave_room(self, sid: str, room: str, namespace: Optional[str] = None) -> None:
        """Remove a client from a room"""
        result = self.sio.leave_room(sid, room, namespace=namespace)
        if inspect.isawaitable(result):
            await result

    async def emit_to_room(
        self,
        event: str,
        data: Dict[str, Any],
        room: str,
        skip_sid: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """Emit event to all clients in a room"""
        try:
            # python-socketio uses 'to' parameter for rooms, not 'room'
            await self.sio.emit(
                event,
                data,
                to=room,
                skip_sid=skip_sid,
                namespace=namespace,
            )
        except Exception as e:
            logger.error(f"Error emitting to room {room}: {e}")
            raise

    async def broadcast(
        self,
        event: str,
        data: Dict[str, Any],
        skip_sid: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """Broadcast event to all clients"""
        await self.sio.emit(event, data, skip_sid=skip_sid, namespace=namespace)

    async def get_client_ids(self, namespace: Optional[str] = None) -> list:
        """Get all connected client IDs"""
        return list(self.sio.rooms(namespace=namespace).keys())


socket_gateway = SocketGateway()
