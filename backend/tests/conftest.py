import os
import time
import uuid
import pytest
import jwt
from typing import Dict, Any, List, Optional

# Set testing environment before importing app
os.environ["FLASK_ENV"] = "testing"

from backend.app import create_app
from backend.app.config import TestingConfig
from backend.app.utils.supabase_client import set_supabase_clients


class MockTable:
    """Simulates a Supabase PostgREST table query builder with RLS policy evaluation."""

    def __init__(self, db: "MockDatabase", table_name: str):
        self.db = db
        self.table_name = table_name
        self._filters = []
        self._select_fields = "*"
        self._pending_insert = None
        self._pending_update = None
        self._pending_delete = False

    def select(self, fields: str = "*"):
        self._select_fields = fields
        return self

    def eq(self, column: str, value: Any):
        self._filters.append((column, value))
        return self

    def insert(self, data: Any):
        if isinstance(data, list):
            self._pending_insert = data
        else:
            self._pending_insert = [data]
        return self

    def update(self, data: Dict[str, Any]):
        self._pending_update = data
        return self

    def delete(self):
        self._pending_delete = True
        return self

    def execute(self):
        rows = self.db.get_table_data(self.table_name)

        if self._pending_insert is not None:
            inserted = []
            for item in self._pending_insert:
                row = dict(item)
                if "id" not in row:
                    row["id"] = str(uuid.uuid4())
                if "created_at" not in row:
                    row["created_at"] = "2026-10-08T15:00:00Z"
                if "updated_at" not in row:
                    row["updated_at"] = "2026-10-08T15:00:00Z"

                # Check unique constraints
                if self.table_name == "companies":
                    for existing in rows:
                        if existing.get("slug") == row.get("slug"):
                            raise ValueError(f"Unique constraint violation: slug '{row.get('slug')}' already exists")
                elif self.table_name == "departments":
                    for existing in rows:
                        if existing.get("company_id") == row.get("company_id") and existing.get("name") == row.get("name"):
                            raise ValueError(f"Unique constraint violation: department '{row.get('name')}' already exists in company")

                # Check Foreign Keys
                if self.table_name in ("departments", "profiles"):
                    comp_id = row.get("company_id")
                    if comp_id and not any(c.get("id") == comp_id for c in self.db.get_table_data("companies")):
                        raise ValueError(f"Foreign key violation: company_id '{comp_id}' does not exist")

                rows.append(row)
                inserted.append(row)
            class MockResponse:
                def __init__(self, data):
                    self.data = data
            return MockResponse(inserted)

        if self._pending_update is not None:
            updated = []
            for row in rows:
                if all(row.get(col) == val for col, val in self._filters):
                    row.update(self._pending_update)
                    row["updated_at"] = "2026-10-08T15:05:00Z"
                    updated.append(row)
            class MockResponse:
                def __init__(self, data):
                    self.data = data
            return MockResponse(updated)

        if self._pending_delete:
            remaining = []
            deleted = []
            for row in rows:
                if all(row.get(col) == val for col, val in self._filters):
                    deleted.append(row)
                else:
                    remaining.append(row)
            self.db.set_table_data(self.table_name, remaining)
            class MockResponse:
                def __init__(self, data):
                    self.data = data
            return MockResponse(deleted)

        # SELECT Query evaluation
        matched = []
        for row in rows:
            if all(row.get(col) == val for col, val in self._filters):
                matched.append(row)

        class MockResponse:
            def __init__(self, data):
                self.data = data
        return MockResponse(matched)


class MockDatabase:
    """In-memory multi-tenant database simulating PostgreSQL tables, constraints, and RLS."""

    def __init__(self):
        self._data: Dict[str, List[Dict[str, Any]]] = {
            "companies": [],
            "departments": [],
            "profiles": [],
        }

    def get_table_data(self, name: str) -> List[Dict[str, Any]]:
        return self._data.setdefault(name, [])

    def set_table_data(self, name: str, data: List[Dict[str, Any]]):
        self._data[name] = data

    def table(self, name: str) -> MockTable:
        return MockTable(self, name)

    def rpc(self, function_name: str, params: Dict[str, Any]):
        """Simulates Supabase PostgREST RPC function execution."""
        class MockRpcBuilder:
            def __init__(self, db: "MockDatabase", fn_name: str, fn_params: Dict[str, Any]):
                self.db = db
                self.fn_name = fn_name
                self.params = fn_params

            def execute(self):
                if self.fn_name == "create_company_with_owner":
                    p_name = self.params.get("p_name")
                    p_slug = self.params.get("p_slug")
                    p_full_name = self.params.get("p_full_name") or f"{p_name} Owner"
                    p_settings = self.params.get("p_settings", {})

                    # Check slug uniqueness
                    for c in self.db.get_table_data("companies"):
                        if c.get("slug") == p_slug:
                            raise ValueError(f"Company slug '{p_slug}' is already taken")

                    # In test context, resolve user_id from active context or generate
                    from flask import has_app_context, g
                    user_id = g.user_id if has_app_context() and hasattr(g, "user_id") else str(uuid.uuid4())
                    user_email = g.user_email if has_app_context() and hasattr(g, "user_email") else "owner@company.internal"

                    # Check existing profile
                    for p in self.db.get_table_data("profiles"):
                        if p.get("id") == user_id and p.get("company_id"):
                            raise ValueError("User is already associated with an existing company workspace")

                    company_id = str(uuid.uuid4())
                    company_row = {
                        "id": company_id,
                        "name": p_name,
                        "slug": p_slug,
                        "subscription_tier": "starter",
                        "settings": p_settings,
                        "created_at": "2026-10-09T19:00:00Z",
                        "updated_at": "2026-10-09T19:00:00Z",
                    }
                    self.db.get_table_data("companies").append(company_row)

                    profile_row = {
                        "id": user_id,
                        "company_id": company_id,
                        "email": user_email,
                        "full_name": p_full_name,
                        "role": "owner",
                        "is_active": True,
                        "created_at": "2026-10-09T19:00:00Z",
                        "updated_at": "2026-10-09T19:00:00Z",
                    }
                    self.db.get_table_data("profiles").append(profile_row)

                    class MockRpcResponse:
                        def __init__(self, data):
                            self.data = data

                    return MockRpcResponse({
                        "company": company_row,
                        "profile": profile_row,
                    })

                raise NotImplementedError(f"RPC function '{self.fn_name}' not implemented in test harness")

        return MockRpcBuilder(self, function_name, params)

    # --------------------------------------------------------------------------
    # PostgreSQL Row Level Security (RLS) Simulation Engine
    # Evaluates the exact SQL RLS policies declared in 001_initial_schema.sql
    # --------------------------------------------------------------------------
    def evaluate_rls_select(self, table_name: str, auth_user_id: str) -> List[Dict[str, Any]]:
        """
        Simulates database-level SELECT query execution with active RLS for `auth_user_id`.
        Uses public.get_auth_user_company_id() anti-recursion helper simulation.
        """
        # Resolve user company and role (simulating get_auth_user_company_id() and get_auth_user_role())
        user_profile = next((p for p in self.get_table_data("profiles") if p.get("id") == auth_user_id and p.get("is_active")), None)
        user_company_id = user_profile.get("company_id") if user_profile else None
        user_role = user_profile.get("role") if user_profile else None

        rows = self.get_table_data(table_name)
        allowed_rows = []

        for row in rows:
            if table_name == "companies":
                # Policy: companies_select_tenant (id = get_auth_user_company_id())
                if user_company_id and row.get("id") == user_company_id:
                    allowed_rows.append(row)

            elif table_name == "departments":
                # Policy: departments_select_tenant (company_id = get_auth_user_company_id())
                if user_company_id and row.get("company_id") == user_company_id:
                    allowed_rows.append(row)

            elif table_name == "profiles":
                # Policy: profiles_select_tenant (id = auth.uid() OR company_id = get_auth_user_company_id())
                if row.get("id") == auth_user_id:
                    allowed_rows.append(row)
                elif user_company_id and row.get("company_id") == user_company_id:
                    allowed_rows.append(row)

        return allowed_rows

    def evaluate_rls_update(self, table_name: str, auth_user_id: str, row_id: str, update_fields: Dict[str, Any]) -> bool:
        """
        Simulates database-level UPDATE query execution with active RLS for `auth_user_id`.
        Applies hardened Migration 002 RLS policies with WITH CHECK constraints.
        Returns True if update succeeds, raises PermissionError/ValueError if blocked by RLS.
        """
        user_profile = next((p for p in self.get_table_data("profiles") if p.get("id") == auth_user_id and p.get("is_active")), None)
        user_company_id = user_profile.get("company_id") if user_profile else None
        user_role = user_profile.get("role") if user_profile else None

        rows = self.get_table_data(table_name)
        target_row = next((r for r in rows if r.get("id") == row_id), None)
        if not target_row:
            return False

        if table_name == "profiles":
            # Policy 1: profiles_update_self
            if row_id == auth_user_id:
                # WITH CHECK: id = auth.uid() AND company_id = get_auth_user_company_id() AND role = get_auth_user_role()
                new_company = update_fields.get("company_id", target_row.get("company_id"))
                new_role = update_fields.get("role", target_row.get("role"))
                if new_company != user_company_id or new_role != user_role:
                    raise PermissionError("RLS WITH CHECK violation: self-update cannot alter company_id or role")
                target_row.update(update_fields)
                return True

            # Policy 2: profiles_update_admin
            if user_role in ("owner", "admin") and target_row.get("company_id") == user_company_id:
                target_row.update(update_fields)
                return True

            raise PermissionError("RLS USING violation: user cannot update profiles outside their authorized administrative scope")

        return False


def generate_token(
    user_id: str,
    email: str = "user@example.com",
    expired: bool = False,
    secret: Optional[str] = None,
    algorithm: str = "HS256",
) -> str:
    """Generates signed test JWT tokens."""
    current_time = int(time.time())
    exp_time = (current_time - 3600) if expired else (current_time + 3600)

    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": current_time,
        "exp": exp_time,
    }
    jwt_secret = secret or TestingConfig.JWT_SECRET
    return jwt.encode(payload, jwt_secret, algorithm=algorithm)


@pytest.fixture
def mock_db():
    db = MockDatabase()
    # Seed initial tenant entities
    # Company A
    db.table("companies").insert({
        "id": "company-a-uuid",
        "name": "Acme Corporation",
        "slug": "acme-corp",
        "subscription_tier": "starter",
    }).execute()

    # Company B
    db.table("companies").insert({
        "id": "company-b-uuid",
        "name": "Beta Dynamics",
        "slug": "beta-dyn",
        "subscription_tier": "starter",
    }).execute()

    # Company A Departments
    db.table("departments").insert({
        "id": "dept-a-eng-uuid",
        "company_id": "company-a-uuid",
        "name": "Engineering",
    }).execute()

    # Company B Departments
    db.table("departments").insert({
        "id": "dept-b-sales-uuid",
        "company_id": "company-b-uuid",
        "name": "Sales",
    }).execute()

    # User A Owner (Alice)
    db.table("profiles").insert({
        "id": "user-a-owner-uuid",
        "company_id": "company-a-uuid",
        "department_id": "dept-a-eng-uuid",
        "email": "alice@acme.com",
        "full_name": "Alice Owner",
        "role": "owner",
        "is_active": True,
    }).execute()

    # User A Employee (Bob)
    db.table("profiles").insert({
        "id": "user-a-emp-uuid",
        "company_id": "company-a-uuid",
        "department_id": "dept-a-eng-uuid",
        "email": "bob@acme.com",
        "full_name": "Bob Employee",
        "role": "employee",
        "is_active": True,
    }).execute()

    # User B Owner (Charlie)
    db.table("profiles").insert({
        "id": "user-b-owner-uuid",
        "company_id": "company-b-uuid",
        "department_id": "dept-b-sales-uuid",
        "email": "charlie@beta.com",
        "full_name": "Charlie Beta",
        "role": "owner",
        "is_active": True,
    }).execute()

    # Hook mock db into client providers
    set_supabase_clients(client=db, admin_client=db)
    return db


@pytest.fixture
def app(mock_db):
    app = create_app(TestingConfig)
    return app


@pytest.fixture
def client(app):
    return app.test_client()
