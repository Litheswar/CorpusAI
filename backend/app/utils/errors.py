import logging
from typing import Any, Dict, Optional
from flask import jsonify, Flask
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application exception with standardized code and HTTP status."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="UNAUTHORIZED", status_code=401, details=details)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Access forbidden", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="FORBIDDEN", status_code=403, details=details)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=400, details=details)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="NOT_FOUND", status_code=404, details=details)


class ConflictError(AppError):
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="CONFLICT", status_code=409, details=details)


class InternalServerError(AppError):
    def __init__(self, message: str = "An internal error occurred", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="INTERNAL_ERROR", status_code=500, details=details)


def register_error_handlers(app: Flask) -> None:
    """Registers standardized JSON error handlers for the Flask application."""

    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        logger.warning(f"AppError [{err.code}] {err.status_code}: {err.message} (details: {err.details})")
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        code_map = {
            400: "VALIDATION_ERROR",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            500: "INTERNAL_ERROR",
        }
        err_code = code_map.get(err.code or 500, "HTTP_ERROR")
        logger.warning(f"HTTPException [{err_code}] {err.code}: {err.description}")
        return jsonify({
            "error": {
                "code": err_code,
                "message": err.description or "HTTP error occurred",
            }
        }), err.code or 500

    @app.errorhandler(Exception)
    def handle_generic_exception(err: Exception):
        logger.error(f"Unhandled Exception: {str(err)}", exc_info=True)
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected internal server error occurred",
            }
        }), 500
