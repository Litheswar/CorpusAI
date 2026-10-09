import logging
from typing import Any, Dict, Optional
import jwt
from backend.app.config import Config
from backend.app.repositories.profile_repository import ProfileRepository
from backend.app.utils.errors import UnauthorizedError, ForbiddenError

logger = logging.getLogger(__name__)


class AuthService:
    """Service handling JWT cryptographic verification and user identity resolution."""

    def __init__(self, profile_repository: Optional[ProfileRepository] = None):
        self.profile_repo = profile_repository or ProfileRepository()

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Cryptographically verifies a Supabase-issued JWT.
        Checks:
        - Signature validity (using JWT_SECRET)
        - Token expiration (`exp`)
        - Token structure and required claims (`sub`)
        """
        if not token:
            raise UnauthorizedError("Authentication token is missing")

        from flask import current_app
        secret = ""
        algorithms = Config.JWT_ALGORITHMS
        if current_app:
            secret = current_app.config.get("JWT_SECRET", "")
            algorithms = current_app.config.get("JWT_ALGORITHMS", Config.JWT_ALGORITHMS)
        if not secret:
            secret = Config.JWT_SECRET

        if not secret:
            logger.error("JWT_SECRET is not configured on server")
            raise UnauthorizedError("Authentication service misconfigured")

        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=algorithms,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": False,
                    "require": ["sub"],
                },
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Authentication token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT presented: {e}")
            raise UnauthorizedError("Invalid authentication token")

    def resolve_user_context(self, token: str) -> Dict[str, Any]:
        """
        Resolves the authenticated user's identity, database profile, company membership, and role.
        Never trusts client-supplied tenant or role headers.
        """
        payload = self.verify_token(token)
        user_id = payload.get("sub")
        email = payload.get("email", "")

        if not user_id:
            raise UnauthorizedError("Token missing user identity claim")

        # Resolve profile from persistent database
        profile = self.profile_repo.get_by_id(user_id)

        context = {
            "user_id": user_id,
            "email": email or (profile.get("email") if profile else ""),
            "profile": profile,
            "company_id": profile.get("company_id") if profile else None,
            "role": profile.get("role") if profile else None,
            "is_active": profile.get("is_active", True) if profile else True,
        }

        if profile and not context["is_active"]:
            raise ForbiddenError("User account has been deactivated")

        return context
