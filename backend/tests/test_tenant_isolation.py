import pytest
from backend.tests.conftest import generate_token


# ==============================================================================
# 1. Application-Layer Tenant Isolation Tests
# ==============================================================================

def test_company_a_user_retrieves_only_company_a(client):
    """User belonging to Company A accesses /api/v1/companies/me and receives Company A data."""
    token = generate_token(user_id="user-a-owner-uuid", email="alice@acme.com")
    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["id"] == "company-a-uuid"
    assert data["name"] == "Acme Corporation"
    assert data["role"] == "owner"


def test_company_b_user_retrieves_only_company_b(client):
    """User belonging to Company B accesses /api/v1/companies/me and receives Company B data."""
    token = generate_token(user_id="user-b-owner-uuid", email="charlie@beta.com")
    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["id"] == "company-b-uuid"
    assert data["name"] == "Beta Dynamics"
    assert data["role"] == "owner"


def test_company_a_employee_receives_correct_role_and_tenant(client):
    """An employee in Company A receives Company A with role = 'employee'."""
    token = generate_token(user_id="user-a-emp-uuid", email="bob@acme.com")
    response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["id"] == "company-a-uuid"
    assert data["role"] == "employee"


def test_existing_member_cannot_create_second_company(client):
    """A user already bound to an active company cannot create a new one (conflict prevention)."""
    token = generate_token(user_id="user-a-owner-uuid", email="alice@acme.com")
    response = client.post(
        "/api/v1/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Duplicate Ventures LLC"}
    )
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"]["code"] == "CONFLICT"
    assert "already associated" in data["error"]["message"].lower()


def test_new_user_can_onboard_new_company(client):
    """An authenticated user without a company can provision a new company and become owner."""
    new_user_id = "new-founder-user-uuid"
    token = generate_token(user_id=new_user_id, email="founder@delta.com")

    create_response = client.post(
        "/api/v1/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Delta Technologies",
            "slug": "delta-tech",
            "owner_name": "Daniel Delta"
        }
    )
    assert create_response.status_code == 201
    created_data = create_response.get_json()["data"]
    assert created_data["name"] == "Delta Technologies"
    assert created_data["slug"] == "delta-tech"
    assert created_data["role"] == "owner"

    # Verify that calling /companies/me now succeeds for this newly onboarded owner
    me_response = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.get_json()["data"]
    assert me_data["id"] == created_data["id"]
    assert me_data["name"] == "Delta Technologies"


def test_identity_cannot_be_spoofed_in_body(client):
    """
    Even if a malicious user passes a different user_id or company_id in the request payload,
    the application strictly relies on the verified JWT claims.
    """
    new_attacker_id = "attacker-user-uuid"
    token = generate_token(user_id=new_attacker_id, email="attacker@evil.com")

    # Attacker tries to impersonate user-a-owner-uuid and hijack company-a
    response = client.post(
        "/api/v1/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Trojan Corp",
            "user_id": "user-a-owner-uuid",
            "company_id": "company-a-uuid",
        }
    )
    assert response.status_code == 201
    created = response.get_json()["data"]
    # The created company belongs to attacker, company-a is unharmed
    assert created["id"] != "company-a-uuid"


def test_company_creation_validation_rules(client):
    """POST /api/v1/companies enforces input validation rules."""
    token = generate_token(user_id="validator-user-uuid", email="validator@test.com")

    # Missing name
    res1 = client.post(
        "/api/v1/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={}
    )
    assert res1.status_code == 400
    assert res1.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Name too short
    res2 = client.post(
        "/api/v1/companies",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "A"}
    )
    assert res2.status_code == 400
    assert res2.get_json()["error"]["code"] == "VALIDATION_ERROR"


# ==============================================================================
# 2. Database & Row Level Security (RLS) Layer Tests
# ==============================================================================

def test_database_rls_companies_table_isolation(mock_db):
    """
    PostgreSQL RLS policy 'companies_select_tenant' ensures:
    - User A sees ONLY Company A row
    - User B sees ONLY Company B row
    Cross-tenant visibility is zero at the database layer.
    """
    user_a_rows = mock_db.evaluate_rls_select("companies", auth_user_id="user-a-owner-uuid")
    assert len(user_a_rows) == 1
    assert user_a_rows[0]["id"] == "company-a-uuid"
    assert user_a_rows[0]["name"] == "Acme Corporation"

    user_b_rows = mock_db.evaluate_rls_select("companies", auth_user_id="user-b-owner-uuid")
    assert len(user_b_rows) == 1
    assert user_b_rows[0]["id"] == "company-b-uuid"
    assert user_b_rows[0]["name"] == "Beta Dynamics"


def test_database_rls_departments_table_isolation(mock_db):
    """
    PostgreSQL RLS policy 'departments_select_tenant' ensures:
    - User A sees ONLY Company A departments ('Engineering')
    - User B sees ONLY Company B departments ('Sales')
    """
    user_a_depts = mock_db.evaluate_rls_select("departments", auth_user_id="user-a-owner-uuid")
    assert len(user_a_depts) == 1
    assert user_a_depts[0]["name"] == "Engineering"
    assert user_a_depts[0]["company_id"] == "company-a-uuid"

    user_b_depts = mock_db.evaluate_rls_select("departments", auth_user_id="user-b-owner-uuid")
    assert len(user_b_depts) == 1
    assert user_b_depts[0]["name"] == "Sales"
    assert user_b_depts[0]["company_id"] == "company-b-uuid"


def test_database_rls_profiles_table_isolation(mock_db):
    """
    PostgreSQL RLS policy 'profiles_select_tenant' ensures:
    - User A (Alice) sees profiles in Company A (Alice, Bob)
    - User B (Charlie) is completely excluded from User A's view
    - User B (Charlie) sees ONLY Company B profiles
    """
    user_a_profiles = mock_db.evaluate_rls_select("profiles", auth_user_id="user-a-owner-uuid")
    assert len(user_a_profiles) == 2
    profile_emails = [p["email"] for p in user_a_profiles]
    assert "alice@acme.com" in profile_emails
    assert "bob@acme.com" in profile_emails
    assert "charlie@beta.com" not in profile_emails

    user_b_profiles = mock_db.evaluate_rls_select("profiles", auth_user_id="user-b-owner-uuid")
    assert len(user_b_profiles) == 1
    assert user_b_profiles[0]["email"] == "charlie@beta.com"


def test_database_foreign_key_integrity(mock_db):
    """Inserting a department or profile pointing to a nonexistent company violates foreign key constraints."""
    with pytest.raises(ValueError, match="Foreign key violation"):
        mock_db.table("departments").insert({
            "name": "Ghost Dept",
            "company_id": "nonexistent-fake-company-uuid"
        }).execute()

    with pytest.raises(ValueError, match="Foreign key violation"):
        mock_db.table("profiles").insert({
            "id": "ghost-user-uuid",
            "email": "ghost@nowhere.com",
            "full_name": "Ghost User",
            "company_id": "nonexistent-fake-company-uuid"
        }).execute()


def test_database_unique_constraints(mock_db):
    """Database constraints prevent duplicate slugs or duplicate department names per company."""
    # Duplicate company slug
    with pytest.raises(ValueError, match="Unique constraint violation: slug 'acme-corp'"):
        mock_db.table("companies").insert({
            "name": "Acme Copycat",
            "slug": "acme-corp"
        }).execute()

    # Duplicate department in Company A
    with pytest.raises(ValueError, match="Unique constraint violation: department 'Engineering'"):
        mock_db.table("departments").insert({
            "name": "Engineering",
            "company_id": "company-a-uuid"
        }).execute()
