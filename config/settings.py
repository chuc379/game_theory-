import os
from urllib.parse import urlparse


class Settings:
    def __init__(self):
        # Redis
        self.REDIS_URL = os.getenv("REDIS_URL", "")
        self.REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        self.REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
        self.REDIS_DB = int(os.getenv("REDIS_DB", 0))
        self.REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

        # RabbitMQ
        self.RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
        self.RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
        self.RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
        self.RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
        self.RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

        # Server
        self.SOCKET_IO_PORT = int(os.getenv("SOCKET_IO_PORT", 5000))
        self.WORKER_PORT = int(os.getenv("WORKER_PORT", 5001))

        # Environment
        self.ENV = os.getenv("ENV", "development")
        self.DEBUG = os.getenv("DEBUG", "true").lower() == "true"

        # Parse URLs if provided
        if self.REDIS_URL:
            self._parse_redis_url()
        
        if self.RABBITMQ_URL:
            self._parse_rabbitmq_url()

    def _parse_redis_url(self):
        """Parse Redis URL (rediss://user:password@host:port/db)"""
        parsed = urlparse(self.REDIS_URL)
        self.REDIS_HOST = parsed.hostname or self.REDIS_HOST
        self.REDIS_PORT = parsed.port or self.REDIS_PORT
        self.REDIS_PASSWORD = parsed.password or ""
        if parsed.path and parsed.path != "/":
            try:
                self.REDIS_DB = int(parsed.path.lstrip("/"))
            except ValueError:
                self.REDIS_DB = 0

    def _parse_rabbitmq_url(self):
        """Parse RabbitMQ URL (amqps://user:password@host:port/vhost)"""
        parsed = urlparse(self.RABBITMQ_URL)
        self.RABBITMQ_HOST = parsed.hostname or self.RABBITMQ_HOST
        self.RABBITMQ_PORT = parsed.port or self.RABBITMQ_PORT
        self.RABBITMQ_USER = parsed.username or self.RABBITMQ_USER
        self.RABBITMQ_PASSWORD = parsed.password or self.RABBITMQ_PASSWORD
        self.RABBITMQ_VHOST = parsed.path.lstrip("/") if parsed.path else "/"


settings = Settings()
