from functools import wraps
from typing import Callable, Sequence
from flask import request, g
from backend.app.services.auth_service import AuthService
from backend.app.utils.errors import UnauthorizedError, ForbiddenError


def _extract_bearer_token() -> str:
    """Extracts and validates the Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise UnauthorizedError("Authorization header is missing")

    parts = auth_header.strip().split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Authorization header must follow 'Bearer <token>' format")

    token = parts[1].strip()
    if not token:
        raise UnauthorizedError("Bearer token is empty")

    return token


def require_auth(fn: Callable) -> Callable:
    """
    Decorator enforcing that an incoming request has a valid Supabase JWT.
    Resolves identity and attaches user context to Flask request globals (g).
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        auth_service = AuthService()
        context = auth_service.resolve_user_context(token)

        # Bind authenticated context to request context
        g.user_id = context["user_id"]
        g.user_email = context["email"]
        g.profile = context["profile"]
        g.company_id = context["company_id"]
        g.role = context["role"]

        return fn(*args, **kwargs)

    return wrapper


def require_company_member(fn: Callable) -> Callable:
    """
    Decorator requiring the authenticated user to be an active member of a company.
    Must be used with or after require_auth.
    """
    @wraps(fn)
    @require_auth
    def wrapper(*args, **kwargs):
        if not g.company_id or not g.profile:
            raise ForbiddenError("User is not associated with any company workspace")

        return fn(*args, **kwargs)

    return wrapper


def require_role(allowed_roles: Sequence[str]) -> Callable:
    """
    Decorator restricting route execution to users with specific roles (e.g. 'owner', 'admin').
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        @require_company_member
        def wrapper(*args, **kwargs):
            if g.role not in allowed_roles:
                raise ForbiddenError(f"Operation requires one of the following roles: {', '.join(allowed_roles)}")

            return fn(*args, **kwargs)

        return wrapper

    return decorator
