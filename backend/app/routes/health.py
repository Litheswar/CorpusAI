from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Public health check endpoint.
    Guarantees no internal secrets, database credentials, or stack traces are leaked.
    """
    return jsonify({
        "status": "ok",
        "service": "corpusai-api",
    }), 200
