"""
Socket.io gateway - Real-time communication adapter (ASGI)
"""
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
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:5000",
                "http://127.0.0.1:5000",
                "http://127.0.0.1:3000",
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
            # Use skip_sid to skip a specific client
            await self.sio.emit(event, data, skip_sid=skip_sid, room=room, namespace=namespace)
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
