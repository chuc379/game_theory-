"""
Socket.io gateway - Real-time communication adapter
"""
import logging
from typing import Callable, Optional, Dict, Any
from socketio import AsyncServer, ASGIApp
from aiohttp import web

logger = logging.getLogger(__name__)


class SocketGateway:
    """Socket.io gateway for real-time communication"""

    def __init__(self):
        self.sio = AsyncServer(
            async_mode="aiohttp",
            cors_allowed_origins="*",
            ping_timeout=60,
            ping_interval=25,
        )
        self.app = None

    def setup(self, app: web.Application) -> None:
        """Setup Socket.io with aiohttp app"""
        self.app = ASGIApp(self.sio, app)

    @staticmethod
    def create_app() -> web.Application:
        """Create aiohttp application"""
        app = web.Application()
        app.router.add_get("/health", SocketGateway._health_handler)
        app.router.add_get("/api/swagger.json", SocketGateway._swagger_handler)
        return app

    @staticmethod
    async def _health_handler(request):
        """Health check endpoint"""
        return web.json_response({"status": "ok"})

    @staticmethod
    async def _swagger_handler(request):
        """Swagger spec endpoint"""
        from src.shared.infrastructure.swagger import SWAGGER_SPEC
        return web.json_response(SWAGGER_SPEC)

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

    def run(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        """Run Socket.io server"""
        web.run_app(self.app, host=host, port=port)


socket_gateway = SocketGateway()
