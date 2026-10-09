import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory if present
backend_dir = Path(__file__).resolve().parent.parent
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()


class Config:
    """Base application configuration."""

    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    TESTING = False
    PORT = int(os.getenv("PORT", "5000"))
    HOST = os.getenv("HOST", "127.0.0.1")

    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # JWT Authentication
    JWT_SECRET = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHMS = ["HS256", "RS256"]

    @classmethod
    def validate(cls):
        """Validate critical configuration in non-testing mode."""
        if not cls.TESTING:
            missing = []
            if not cls.SUPABASE_URL:
                missing.append("SUPABASE_URL")
            if not cls.SUPABASE_ANON_KEY:
                missing.append("SUPABASE_ANON_KEY")
            if not cls.SUPABASE_SERVICE_ROLE_KEY:
                missing.append("SUPABASE_SERVICE_ROLE_KEY")
            if not cls.JWT_SECRET:
                missing.append("JWT_SECRET")
            if missing:
                # Warning rather than hard crash to allow offline development
                import logging
                logging.getLogger(__name__).warning(
                    f"Missing Supabase configuration keys: {', '.join(missing)}. "
                    "Mock/test fallbacks will be required for database operations."
                )


class TestingConfig(Config):
    """Testing environment configuration."""

    TESTING = True
    DEBUG = True
    SUPABASE_URL = "https://mock-testing-project.supabase.co"
    SUPABASE_ANON_KEY = "mock-anon-key-for-testing"
    SUPABASE_SERVICE_ROLE_KEY = "mock-service-role-key-for-testing"
    JWT_SECRET = "super-secret-test-jwt-secret-key-32-bytes-minimum"


def get_config():
    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "testing":
        return TestingConfig
    return Config
