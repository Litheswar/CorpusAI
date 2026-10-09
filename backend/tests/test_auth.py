import pytest
from backend.tests.conftest import generate_token


def test_missing_authorization_header(client):
    """Missing Authorization header must return 401 Unauthorized."""
    response = client.get("/api/v1/companies/me")
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "missing" in data["error"]["message"].lower()


def test_malformed_authorization_header(client):
    """Malformed Authorization header must return 401 Unauthorized."""
    # Missing 'Bearer' prefix
    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": "Token some-raw-token-value"}
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"

    # Only 'Bearer' without token
    response2 = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": "Bearer "}
    )
    assert response2.status_code == 401


def test_invalid_jwt_signature(client):
    """JWT signed with an incorrect secret key must be rejected with 401."""
    tampered_token = generate_token(
        user_id="user-a-owner-uuid",
        secret="completely-wrong-untrusted-secret-key-32b"
    )
    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {tampered_token}"}
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "invalid" in data["error"]["message"].lower()


def test_expired_jwt(client):
    """Expired JWT must be rejected with 401."""
    expired_token = generate_token(
        user_id="user-a-owner-uuid",
        expired=True
    )
    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "expired" in data["error"]["message"].lower()


def test_authenticated_user_without_company_profile(client):
    """An authenticated user with a valid JWT but without a company profile cannot access tenant routes."""
    # User not present in profiles table
    unregistered_token = generate_token(
        user_id="unregistered-user-999-uuid",
        email="newcomer@example.com"
    )
    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {unregistered_token}"}
    )
    assert response.status_code == 403
    data = response.get_json()
    assert data["error"]["code"] == "FORBIDDEN"
    assert "not associated with any company" in data["error"]["message"].lower()


def test_authenticated_user_resolves_profile_and_role(client):
    """Valid JWT resolves authenticated user, profile, company, and role correctly."""
    valid_token = generate_token(
        user_id="user-a-owner-uuid",
        email="alice@acme.com"
    )
    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["id"] == "company-a-uuid"
    assert data["data"]["name"] == "Acme Corporation"
    assert data["data"]["role"] == "owner"
