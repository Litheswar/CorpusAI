import logging
from typing import Optional
from supabase import create_client, Client
from backend.app.config import Config

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None


def get_supabase_client(config: Optional[Config] = None) -> Optional[Client]:
    """Returns the anon/public Supabase client."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = (config.SUPABASE_URL if config else Config.SUPABASE_URL)
    key = (
        (getattr(config, "SUPABASE_PUBLISHABLE_KEY", None) or getattr(config, "SUPABASE_ANON_KEY", None))
        if config else (Config.SUPABASE_PUBLISHABLE_KEY or Config.SUPABASE_ANON_KEY)
    )

    if not url or not key:
        return None

    try:
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def get_supabase_admin_client(config: Optional[Config] = None) -> Optional[Client]:
    """
    Returns the privileged service-role Supabase client.
    Used ONLY for server-side trusted operations (e.g. initial tenant onboarding).
    NEVER expose this client or its credentials to the client/frontend.
    """
    global _supabase_admin_client
    if _supabase_admin_client is not None:
        return _supabase_admin_client

    url = (config.SUPABASE_URL if config else Config.SUPABASE_URL)
    key = (config.SUPABASE_SERVICE_ROLE_KEY if config else Config.SUPABASE_SERVICE_ROLE_KEY)

    if not url or not key:
        return None

    try:
        _supabase_admin_client = create_client(url, key)
        return _supabase_admin_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase admin client: {e}")
        return None


def set_supabase_clients(client: Optional[Client], admin_client: Optional[Client]) -> None:
    """Allows testing harnesses to inject mocked clients directly."""
    global _supabase_client, _supabase_admin_client
    _supabase_client = client
    _supabase_admin_client = admin_client
