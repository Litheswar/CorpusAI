import pytest
from backend.tests.conftest import generate_token


def test_duplicate_company_slug_rejected(client):
    """Attempting to create a company with a slug already in use returns 409 Conflict."""
    token = generate_token(user_id="another-user-uuid", email="founder2@test.com")
    response = client.post(
        "/api/v1/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Acme Copycat Ltd",
            "slug": "acme-corp"  # Already used by Company A
        }
    )
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"]["code"] == "CONFLICT"
    assert "already taken" in data["error"]["message"].lower()


def test_company_rollback_on_profile_failure(mock_db):
    """
    If profile creation fails during company onboarding,
    the created company must be rolled back (deleted) to prevent orphan tenants.
    """
    from backend.app.services.company_service import CompanyService
    from backend.app.repositories.company_repository import CompanyRepository
    from unittest.mock import MagicMock

    company_repo = CompanyRepository(client=mock_db)
    # Simulate RPC being unavailable so fallback multi-step flow is executed
    company_repo.create_with_owner_rpc = MagicMock(side_effect=Exception("RPC unavailable"))

    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = None
    # Simulate database failure during profile insert
    mock_profile_repo.create.side_effect = RuntimeError("Database connection lost during profile insertion")

    service = CompanyService(
        company_repository=company_repo,
        profile_repository=mock_profile_repo
    )

    with pytest.raises(RuntimeError):
        service.create_company_with_owner(
            user_id="unlucky-user-uuid",
            user_email="unlucky@test.com",
            company_name="Ghost Company",
            company_slug="ghost-comp"
        )

    # Verify company was not left in the database
    companies = mock_db.get_table_data("companies")
    assert not any(c.get("slug") == "ghost-comp" for c in companies)


def test_company_repository_rpc_direct(mock_db):
    """Verifies direct execution of create_with_owner_rpc via CompanyRepository."""
    from backend.app.repositories.company_repository import CompanyRepository

    repo = CompanyRepository(client=mock_db)
    result = repo.create_with_owner_rpc(
        name="RPC Direct Corp",
        slug="rpc-direct-corp",
        full_name="RPC Owner",
        settings={"tier": "custom"}
    )
    assert result is not None
    assert "company" in result
    assert "profile" in result
    assert result["company"]["name"] == "RPC Direct Corp"
    assert result["profile"]["role"] == "owner"
