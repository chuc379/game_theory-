from pydantic_settings import BaseSettings
from urllib.parse import urlparse


class Settings(BaseSettings):
    # Redis - Support both individual config and URL
    REDIS_URL: str = ""
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # RabbitMQ - Support both individual config and URL
    RABBITMQ_URL: str = ""
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"

    # Server
    SOCKET_IO_PORT: int = 5000
    WORKER_PORT: int = 5001

    # Environment
    ENV: str = "development"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **data):
        super().__init__(**data)
        
        # Parse Redis URL if provided
        if self.REDIS_URL:
            self._parse_redis_url()
        
        # Parse RabbitMQ URL if provided
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
