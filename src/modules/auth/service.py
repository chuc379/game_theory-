"""
Authentication service - validates MC credentials and issues access tokens.
"""
import logging
import secrets
from typing import Optional

from config.settings import settings
from src.modules.auth.password import verify_password
from src.modules.auth.tokens import TokenError, create_access_token

logger = logging.getLogger(__name__)


class AuthService:
    """Handles MC credentials. There is no user database: the single MC
    account is configured through environment variables."""

    def is_configured(self) -> bool:
        return bool(settings.MC_USERNAME and settings.MC_PASSWORD_HASH and settings.JWT_SECRET)

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Return an access token when the credentials are valid, else None."""
        if not self.is_configured():
            logger.error("MC credentials or JWT_SECRET are not configured")
            return None
        if not username or not password:
            return None
        if not secrets.compare_digest(str(username), settings.MC_USERNAME):
            return None
        if not verify_password(str(password), settings.MC_PASSWORD_HASH):
            return None
        try:
            return create_access_token(settings.MC_USERNAME)
        except TokenError as e:
            logger.error(f"Cannot issue token: {e}")
            return None


auth_service = AuthService()
