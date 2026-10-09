import pytest
from backend.tests.conftest import generate_token


def test_token_missing_sub_claim(client):
    """JWT missing the mandatory 'sub' claim must be rejected."""
    import time
    import jwt
    from backend.app.config import TestingConfig

    payload = {
        "email": "nosub@example.com",
        "aud": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, TestingConfig.JWT_SECRET, algorithm="HS256")

    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_deactivated_user_account_blocked(client, mock_db):
    """A deactivated user (is_active = False) must be rejected with 403 Forbidden."""
    # Seed deactivated user
    mock_db.table("profiles").insert({
        "id": "deactivated-user-uuid",
        "company_id": "company-a-uuid",
        "email": "suspended@acme.com",
        "full_name": "Suspended User",
        "role": "employee",
        "is_active": False,
    }).execute()

    token = generate_token(user_id="deactivated-user-uuid", email="suspended@acme.com")
    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    data = response.get_json()
    assert data["error"]["code"] == "FORBIDDEN"
    assert "deactivated" in data["error"]["message"].lower()
