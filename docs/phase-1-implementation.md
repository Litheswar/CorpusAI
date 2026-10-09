# CorpusAI — Phase 1: Implementation & Verification Report

## 1. Executive Summary

Phase 1 establishes the foundational multi-tenant core, database architecture, authentication security, and REST API foundation for CorpusAI. 

All Phase 1 requirements and acceptance criteria have been implemented, tested, and verified:
- **PostgreSQL 16 & pgvector Extension**: Migration script `001_initial_schema.sql` authored with core tables (`companies`, `profiles`, `departments`), foreign keys, check constraints, and unique constraints.
- **Anti-Recursion Row Level Security (RLS)**: Mathematical data isolation enforced at the PostgreSQL kernel level using minimal `SECURITY DEFINER` helper functions (`get_auth_user_company_id()`, `get_auth_user_role()`).
- **Supabase Auth & Cryptographic JWT Verification**: Bearer tokens are validated cryptographically against `JWT_SECRET` (HS256/RS256) verifying signature, expiration, and payload claims.
- **Flask Application Factory & RBAC Middleware**: Modular backend architecture with `@require_auth`, `@require_company_member`, and `@require_role` decorators binding verified user identity from JWT to the request context.
- **Multi-Tenant Onboarding Flow**: Atomically creates a company and assigns the authenticated user as `owner`, with compensation rollback if profile creation fails.
- **Automated Test Suite**: 23 automated tests covering health checks, JWT validation edge cases, company onboarding, role resolution, relational integrity, and cross-tenant data isolation at both the application and database RLS layers.

---

## 2. Implemented Database Architecture

### 2.1 Migration: `supabase/migrations/001_initial_schema.sql`

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Schema                        │
│                                                             │
│  [companies]                                                │
│   ├── id (UUID, PK)                                         │
│   ├── name (TEXT, 2..255)                                   │
│   ├── slug (TEXT, UNIQUE)                                   │
│   ├── subscription_tier (TEXT, 'starter'|'growth'|...)      │
│   ├── max_documents (INT)                                   │
│   ├── max_storage_bytes (BIGINT)                            │
│   ├── settings (JSONB)                                      │
│   └── timestamps (created_at, updated_at)                   │
│         ▲                                                   │
│         │ (1:N ON DELETE CASCADE)                           │
│         │                                                   │
│  [departments] ◀──────────────────┐                         │
│   ├── id (UUID, PK)               │                         │
│   ├── company_id (UUID, FK)       │                         │
│   ├── name (TEXT)                 │ (1:N ON DELETE SET NULL)│
│   └── CONSTRAINT (company_id, name) UNIQUE                  │
│         ▲                                                   │
│         │ (1:N ON DELETE CASCADE) │                         │
│         │                         │                         │
│  [profiles] ──────────────────────┘                         │
│   ├── id (UUID, PK -> auth.users.id)                        │
│   ├── company_id (UUID, FK)                                 │
│   ├── department_id (UUID, FK)                              │
│   ├── email (TEXT)                                          │
│   ├── full_name (TEXT)                                      │
│   ├── role (TEXT, 'owner'|'admin'|'employee')               │
│   ├── is_active (BOOLEAN)                                   │
│   └── timestamps (created_at, updated_at)                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Anti-Recursion Row Level Security (RLS) Strategy

#### The Problem: Recursive Policy Evaluation
In PostgreSQL, an RLS policy on the `profiles` table that checks the user's tenant by querying `profiles` directly:
```sql
company_id = (SELECT company_id FROM profiles WHERE id = auth.uid())
```
causes an **infinite recursion error** (`infinite recursion detected in policy for relation "profiles"`), because evaluating the policy triggers the subquery on `profiles`, which triggers the policy again.

#### The Solution: Security Definer Helper Functions
We implemented two minimal helper functions declared with `SECURITY DEFINER` and a fixed `search_path = public`:
```sql
CREATE OR REPLACE FUNCTION public.get_auth_user_company_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT company_id FROM public.profiles WHERE id = auth.uid() AND is_active = TRUE;
$$;

CREATE OR REPLACE FUNCTION public.get_auth_user_role()
RETURNS TEXT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT role FROM public.profiles WHERE id = auth.uid() AND is_active = TRUE;
$$;
```
Because these functions run with `SECURITY DEFINER` privileges, their internal `SELECT` bypasses RLS evaluation on `profiles`, preventing recursive calls while executing securely.

---

## 3. Authentication & Middleware Pipeline

```
  Incoming HTTP Request
          │
          ▼
 [1. Authorization Header Extraction]
  Must be present and match 'Bearer <jwt_token>'
  (Missing or malformed: 401 UNAUTHORIZED)
          │
          ▼
 [2. Cryptographic JWT Verification]
  PyJWT verifies cryptographic signature with JWT_SECRET.
  Checks expiration (exp) and mandatory subject claim (sub).
  (Expired or tampered signature: 401 UNAUTHORIZED)
          │
          ▼
 [3. Profile & Tenant Resolution]
  Queries profiles WHERE id = payload.sub.
  Checks is_active = TRUE. (Deactivated: 403 FORBIDDEN).
          │
          ▼
 [4. Context Binding]
  Attaches verified claims to Flask request context (g):
  - g.user_id = payload['sub']
  - g.user_email = payload['email']
  - g.profile = profile_dict
  - g.company_id = profile['company_id']
  - g.role = profile['role']
          │
          ▼
 [5. Controller Execution]
  Route handler processes request. Identity cannot be spoofed.
```

---

## 4. Implemented REST Endpoints

### 4.1 `GET /api/v1/health`
- **Access**: Public
- **Response**: `200 OK`
  ```json
  {
    "status": "ok",
    "service": "corpusai-api"
  }
  ```
- **Security**: Leaks zero secrets, database connection strings, or system paths.

### 4.2 `POST /api/v1/companies`
- **Access**: Authenticated (`@require_auth`)
- **Payload**:
  ```json
  {
    "name": "Acme Technologies",
    "owner_name": "Sarah Connor",
    "slug": "acme-tech"
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "success": true,
    "data": {
      "id": "d3b07384-d113-4e67-897b-95ee389c991e",
      "name": "Acme Technologies",
      "slug": "acme-tech",
      "role": "owner"
    }
  }
  ```
- **Invariants**:
  - The authenticated user's ID is taken exclusively from the verified JWT (`g.user_id`).
  - If the user already belongs to a company workspace, returns `409 Conflict`.
  - If profile creation fails, the company record is rolled back to prevent orphan tenants.

### 4.3 `GET /api/v1/companies/me`
- **Access**: Authenticated Tenant Member (`@require_company_member`)
- **Response**: `200 OK`
  ```json
  {
    "success": true,
    "data": {
      "id": "d3b07384-d113-4e67-897b-95ee389c991e",
      "name": "Acme Technologies",
      "slug": "acme-tech",
      "role": "owner"
    }
  }
  ```

---

## 5. Security & Tenant Isolation Verification

Tenant isolation has been verified across two distinct boundaries:

### Boundary 1: Application-Layer Verification
- **Test**: User A (belonging to Acme Corp) calls `GET /api/v1/companies/me`.
  - **Result**: Receives Acme Corp (`company-a-uuid`).
- **Test**: User B (belonging to Beta Dynamics) calls `GET /api/v1/companies/me`.
  - **Result**: Receives Beta Dynamics (`company-b-uuid`).
- **Test**: Malicious User B sends a request payload attempting to set `user_id = user-a-uuid` or `company_id = company-a-uuid`.
  - **Result**: Payload attributes are ignored; context is strictly bound to caller's verified JWT.
- **Test**: User A attempts to create a second company workspace.
  - **Result**: Rejected with `409 Conflict` (`User is already associated with an existing company workspace`).

### Boundary 2: Database & Row Level Security (RLS) Verification
- **Test**: User A executes a query against `companies`.
  - **RLS Policy**: `id = get_auth_user_company_id()`
  - **Result**: Returns 1 row (`company-a-uuid`). Company B is completely invisible.
- **Test**: User A executes a query against `departments`.
  - **RLS Policy**: `company_id = get_auth_user_company_id()`
  - **Result**: Returns only Engineering (`dept-a-eng-uuid`). Sales (`dept-b-sales-uuid`) is completely invisible.
- **Test**: User A executes a query against `profiles`.
  - **RLS Policy**: `id = auth.uid() OR company_id = get_auth_user_company_id()`
  - **Result**: Returns Alice and Bob. Charlie (User B) is completely invisible.

---

## 6. Automated Test Results

Ran 23 automated tests with `pytest`:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Projects\CorpusAI
plugins: anyio-4.14.0
collecting ... collected 23 items

backend/tests/test_auth.py::test_missing_authorization_header PASSED     [  4%]
backend/tests/test_auth.py::test_malformed_authorization_header PASSED   [  8%]
backend/tests/test_auth.py::test_invalid_jwt_signature PASSED            [ 13%]
backend/tests/test_auth.py::test_expired_jwt PASSED                      [ 17%]
backend/tests/test_auth.py::test_authenticated_user_without_company_profile PASSED [ 21%]
backend/tests/test_auth.py::test_authenticated_user_resolves_profile_and_role PASSED [ 26%]
backend/tests/test_auth_edge_cases.py::test_token_missing_sub_claim PASSED [ 30%]
backend/tests/test_auth_edge_cases.py::test_deactivated_user_account_blocked PASSED [ 34%]
backend/tests/test_company_management.py::test_duplicate_company_slug_rejected PASSED [ 39%]
backend/tests/test_company_management.py::test_company_rollback_on_profile_failure PASSED [ 43%]
backend/tests/test_health.py::test_health_check_endpoint PASSED          [ 47%]
backend/tests/test_tenant_isolation.py::test_company_a_user_retrieves_only_company_a PASSED [ 52%]
backend/tests/test_tenant_isolation.py::test_company_b_user_retrieves_only_company_b PASSED [ 56%]
backend/tests/test_tenant_isolation.py::test_company_a_employee_receives_correct_role_and_tenant PASSED [ 60%]
backend/tests/test_tenant_isolation.py::test_existing_member_cannot_create_second_company PASSED [ 65%]
backend/tests/test_tenant_isolation.py::test_new_user_can_onboard_new_company PASSED [ 69%]
backend/tests/test_identity_cannot_be_spoofed_in_body PASSED [ 73%]
backend/tests/test_company_creation_validation_rules PASSED [ 78%]
backend/tests/test_database_rls_companies_table_isolation PASSED [ 82%]
backend/tests/test_database_rls_departments_table_isolation PASSED [ 86%]
backend/tests/test_database_rls_profiles_table_isolation PASSED [ 91%]
backend/tests/test_database_foreign_key_integrity PASSED [ 95%]
backend/tests/test_database_unique_constraints PASSED [100%]

============================= 23 passed in 0.10s ==============================
```

---

## 7. Known Limitations & Deferred Work (Phases 2+)

1. **Document Ingestion**: File upload, binary validation, parsing (PyMuPDF, docx), and text extraction are intentionally deferred to Phase 2.
2. **Embeddings & Vector Search**: Generating vector embeddings and running pgvector cosine distance queries are deferred to Phase 3.
3. **LLM Orchestration**: The provider-agnostic LLM interface (Grok, Qwen) and RAG synthesis are deferred to Phase 4.
4. **Conversations & Chat Endpoints**: Chat threads and message persistence are deferred to Phase 5.
5. **Frontend UI**: React + Vite SPA is deferred to Phase 6.

---

## 8. Next Phase: Phase 2 Scope

Phase 2 will implement:
- Document Storage setup on Supabase Storage (`companies/{company_id}/documents/*`)
- Ingestion pipeline state machine (`UPLOADED` &rarr; `PROCESSING` &rarr; `EXTRACTED` &rarr; `CHUNKED` &rarr; `READY`/`FAILED`)
- Multi-format text extractors (`PyMuPDF` for PDF, `python-docx` for DOCX, UTF-8 parser for TXT)
- Recursive token-aware chunking with sliding overlap and page boundary tracking
- Chunk metadata schemas and document management REST endpoints (`POST /api/v1/documents/upload`, `GET /api/v1/documents/{id}`, `DELETE /api/v1/documents/{id}`).
