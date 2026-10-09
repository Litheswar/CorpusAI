import logging
from typing import Optional, Type
from flask import Flask
from backend.app.config import Config, get_config
from backend.app.utils.errors import register_error_handlers
from backend.app.routes.health import health_bp
from backend.app.routes.companies import companies_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("corpusai")


def create_app(config_class: Optional[Type[Config]] = None) -> Flask:
    """
    Application factory for CorpusAI Flask backend.
    """
    app = Flask(__name__)

    # Load configuration
    cfg = config_class or get_config()
    app.config.from_object(cfg)

    # Validate config
    cfg.validate()

    # Register standardized error handlers
    register_error_handlers(app)

    # Register blueprints under /api/v1 prefix
    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(companies_bp, url_prefix="/api/v1/companies")

    logger.info(f"CorpusAI Application initialized in {app.config.get('FLASK_ENV')} mode")
    return app
