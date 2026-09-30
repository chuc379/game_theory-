"""
Socket.io gateway - Real-time communication adapter (ASGI)
"""
import logging
from typing import Callable, Optional, Dict, Any
from socketio import AsyncServer
from engineio.async_drivers.asgi import ASGIApp

logger = logging.getLogger(__name__)


class SocketGateway:
    """Socket.io gateway for real-time communication"""

    def __init__(self):
        self.sio = AsyncServer(
            async_mode="asgi",
            cors_allowed_origins=["http://localhost:3000", "http://localhost:3001", "https://*"],
            ping_timeout=60,
            ping_interval=25,
            engineio_logger=False,
            logger=False,
        )
        # Create ASGI app from Socket.io's engineio
        self.asgi_app = ASGIApp(self.sio.eio)

    async def __call__(self, scope, receive, send):
        """ASGI callable"""
        await self.asgi_app(scope, receive, send)

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
