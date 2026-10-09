from flask import Blueprint, request, jsonify, g
from backend.app.middleware.auth import require_auth, require_company_member
from backend.app.services.company_service import CompanyService
from backend.app.utils.errors import ValidationError

companies_bp = Blueprint("companies", __name__)


@companies_bp.route("", methods=["POST"])
@require_auth
def create_company():
    """
    POST /api/v1/companies
    Authenticated user creates a new company workspace.
    User's identity is strictly taken from the verified JWT (g.user_id, g.user_email).
    Any user_id or company_id passed in the JSON body is ignored.
    """
    body = request.get_json(silent=True)
    if not body or not isinstance(body, dict):
        raise ValidationError("Request body must be valid JSON")

    name = body.get("name")
    if not name or not isinstance(name, str):
        raise ValidationError("Field 'name' is required and must be a non-empty string")

    owner_name = body.get("owner_name")
    slug = body.get("slug")

    service = CompanyService()
    result = service.create_company_with_owner(
        user_id=g.user_id,
        user_email=g.user_email,
        company_name=name,
        owner_name=owner_name,
        company_slug=slug,
    )

    company = result["company"]
    profile = result["profile"]

    return jsonify({
        "success": True,
        "data": {
            "id": company["id"],
            "name": company["name"],
            "slug": company.get("slug"),
            "role": profile["role"],
        }
    }), 201


@companies_bp.route("/me", methods=["GET"])
@require_company_member
def get_current_company():
    """
    GET /api/v1/companies/me
    Retrieves the company workspace for the authenticated user.
    Uses g.company_id and g.role resolved from the authenticated profile.
    """
    service = CompanyService()
    company_details = service.get_company_details(g.company_id)

    return jsonify({
        "success": True,
        "data": {
            "id": company_details["id"],
            "name": company_details["name"],
            "slug": company_details.get("slug"),
            "role": g.role,
        }
    }), 200
