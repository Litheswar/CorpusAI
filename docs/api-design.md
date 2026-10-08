# CorpusAI — REST API Design Specification

## 1. Global API Standards

- **Base URL**: `/api/v1`
- **Transport**: HTTPS with TLS 1.3
- **Format**: All requests and responses use `application/json` (except multi-part file uploads and Server-Sent Events).
- **Authentication**: Stateless Bearer JWT issued by Supabase Auth passed via `Authorization: Bearer <jwt_token>`.
- **Standard Success Response**:
  ```json
  {
    "success": true,
    "data": { ... },
    "meta": { "timestamp": "2026-10-08T15:00:00Z" }
  }
  ```
- **Standard Error Response**:
  ```json
  {
    "success": false,
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "The requested document was not found or access is denied.",
      "details": {}
    }
  }
  ```

---

## 2. Authentication & Account Management (`/api/v1/auth`)

### 2.1 Register New Tenant & Owner (`POST /api/v1/auth/register-company`)
- **Purpose**: Creates a new company tenant workspace, provisions the owner profile, and returns initial session tokens.
- **Authentication**: Authenticated Supabase user (JWT valid) or Supabase signup hook.
- **Authorization**: Public for new account creation.
- **Request Body**:
  ```json
  {
    "company_name": "Acme Technologies",
    "company_slug": "acme-tech",
    "full_name": "Sarah Connor",
    "email": "sarah@acme.com"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "success": true,
    "data": {
      "company": {
        "id": "d3b07384-d113-4e67-897b-95ee389c991e",
        "name": "Acme Technologies",
        "slug": "acme-tech"
      },
      "user": {
        "id": "4a7c2b18-3e91-4d7a-8b6f-2e1c3a4d5e6f",
        "email": "sarah@acme.com",
        "full_name": "Sarah Connor",
        "role": "owner"
      }
    }
  }
  ```
- **Errors**: `400 Bad Request` (invalid input), `409 Conflict` (slug or email already registered).

### 2.2 Get Current User Profile (`GET /api/v1/auth/me`)
- **Purpose**: Retrieves the active user profile, company details, assigned department, and role permissions.
- **Authentication**: Required (`Bearer JWT`).
- **Authorization**: Any valid tenant member.
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "data": {
      "id": "4a7c2b18-3e91-4d7a-8b6f-2e1c3a4d5e6f",
      "email": "sarah@acme.com",
      "full_name": "Sarah Connor",
      "role": "owner",
      "company": {
        "id": "d3b07384-d113-4e67-897b-95ee389c991e",
        "name": "Acme Technologies",
        "slug": "acme-tech"
      },
      "department": null
    }
  }
  ```
- **Errors**: `401 Unauthorized` (expired or invalid token).

---

## 3. Company Workspace Management (`/api/v1/companies`)

### 3.1 Get Company Workspace Settings (`GET /api/v1/companies/current`)
- **Purpose**: Returns current company settings, usage statistics, and subscription quotas.
- **Authentication**: Required.
- **Authorization**: `owner` or `admin`.
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "data": {
      "id": "d3b07384-d113-4e67-897b-95ee389c991e",
      "name": "Acme Technologies",
      "slug": "acme-tech",
      "subscription_tier": "starter",
      "document_count": 24,
      "max_documents": 100,
      "storage_used_bytes": 104857600,
      "max_storage_bytes": 5368709120,
      "settings": {
        "default_llm_provider": "grok"
      }
    }
  }
  ```
- **Errors**: `401 Unauthorized`, `403 Forbidden`.

### 3.2 Update Company Settings (`PATCH /api/v1/companies/current`)
- **Purpose**: Modifies workspace display name and tenant configuration.
- **Authentication**: Required.
- **Authorization**: `owner` only.
- **Request Body**:
  ```json
  {
    "name": "Acme Technologies Global",
    "settings": {
      "default_llm_provider": "qwen"
    }
  }
  ```
- **Response** (`200 OK`): Updated company record.
- **Errors**: `400 Bad Request`, `403 Forbidden`.

---

## 4. User & Membership Management (`/api/v1/users`)

### 4.1 List Company Users (`GET /api/v1/users`)
- **Purpose**: Lists all active employees and administrators in the current tenant.
- **Authentication**: Required.
- **Authorization**: `owner`, `admin`, or `employee` (limited directory view).
- **Query Parameters**: `?page=1&limit=20&department_id=<uuid>`
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "data": {
      "users": [
        {
          "id": "4a7c2b18-3e91-4d7a-8b6f-2e1c3a4d5e6f",
          "email": "john@acme.com",
          "full_name": "John Doe",
          "role": "employee",
          "department_id": "9b1c2d3e-4f5a-6b7c-8d9e-0f1a2b3c4d5e",
          "department_name": "Engineering",
          "is_active": true
        }
      ],
      "pagination": { "page": 1, "limit": 20, "total": 1 }
    }
  }
  ```

### 4.2 Invite Employee (`POST /api/v1/users/invite`)
- **Purpose**: Invites a new team member to join the tenant workspace with pre-assigned role and department.
- **Authentication**: Required.
- **Authorization**: `owner` or `admin`.
- **Request Body**:
  ```json
  {
    "email": "jane@acme.com",
    "full_name": "Jane Smith",
    "role": "employee",
    "department_id": "9b1c2d3e-4f5a-6b7c-8d9e-0f1a2b3c4d5e"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "success": true,
    "data": {
      "invitation_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
      "email": "jane@acme.com",
      "status": "pending"
    }
  }
  ```
- **Errors**: `400 Bad Request`, `403 Forbidden`, `409 Conflict` (user already member).

---

## 5. Department Management (`/api/v1/departments`)

### 5.1 List Departments (`GET /api/v1/departments`)
- **Purpose**: Lists all departments in the company.
- **Authentication**: Required.
- **Authorization**: All authenticated tenant members.
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "data": [
      {
        "id": "9b1c2d3e-4f5a-6b7c-8d9e-0f1a2b3c4d5e",
        "name": "Engineering",
        "description": "Software and infrastructure teams"
      }
    ]
  }
  ```

### 5.2 Create Department (`POST /api/v1/departments`)
- **Purpose**: Creates an organizational department.
- **Authentication**: Required.
- **Authorization**: `owner` or `admin`.
- **Request Body**:
  ```json
  {
    "name": "Human Resources",
    "description": "Talent, culture, and employee policies"
  }
  ```
- **Response** (`201 Created`): Created department object.
- **Errors**: `400 Bad Request`, `409 Conflict` (duplicate department name).

---

## 6. Document Ingestion & Management (`/api/v1/documents`)

### 6.1 Upload Document (`POST /api/v1/documents/upload`)
- **Purpose**: Ingests a new document (PDF, DOCX, TXT) into Supabase Storage and triggers ingestion lifecycle.
- **Authentication**: Required.
- **Authorization**: `owner`, `admin`, or authorized `employee`.
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: Binary file stream (max 50MB)
  - `department_id`: Optional UUID
  - `visibility`: `"company"` | `"department"` | `"restricted"` (default `"company"`)
  - `authority_level`: `"policy"` | `"announcement"` | `"sop"` | `"informal"` (default `"sop"`)
- **Response** (`202 Accepted`):
  ```json
  {
    "success": true,
    "data": {
      "document_id": "1e2f3a4b-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
      "filename": "Employee_Handbook_2026.pdf",
      "status": "PROCESSING",
      "file_size": 2048500,
      "mime_type": "application/pdf"
    }
  }
  ```
- **Errors**: `400 Bad Request` (unsupported file format), `413 Payload Too Large` (>50MB), `403 Forbidden`.

### 6.2 Get Document Status & Metadata (`GET /api/v1/documents/{document_id}`)
- **Purpose**: Polls ingestion status or inspects document details.
- **Authentication**: Required.
- **Authorization**: Tenant member with document read permission.
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "data": {
      "id": "1e2f3a4b-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
      "filename": "Employee_Handbook_2026.pdf",
      "status": "READY",
      "total_pages": 48,
      "total_chunks": 112,
      "visibility": "company",
      "authority_level": "policy",
      "version": 1,
      "is_current": true,
      "created_at": "2026-10-08T14:30:00Z"
    }
  }
  ```
- **Errors**: `404 Not Found` (does not exist or unauthorized).

### 6.3 List Documents (`GET /api/v1/documents`)
- **Purpose**: Returns paginated list of authorized documents.
- **Authentication**: Required.
- **Authorization**: Filtered automatically to caller's permissions.
- **Query Parameters**: `?page=1&limit=20&department_id=<uuid>&status=READY`
- **Response** (`200 OK`): Array of document metadata objects with pagination.

### 6.4 Delete Document (`DELETE /api/v1/documents/{document_id}`)
- **Purpose**: Deletes a document, raw storage file, chunks, and vector embeddings atomically.
- **Authentication**: Required.
- **Authorization**: `owner`, `admin`, or original uploader.
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "data": {
      "id": "1e2f3a4b-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
      "deleted": true
    }
  }
  ```
- **Errors**: `403 Forbidden`, `404 Not Found`.

---

## 7. Conversational Chat & Grounded RAG (`/api/v1/chat`)

### 7.1 Ask Question / RAG Query (`POST /api/v1/chat/completions`)
- **Purpose**: Executes permission-aware semantic search over company documents, synthesizes a grounded answer, and returns citations. Supports streaming or JSON mode.
- **Authentication**: Required.
- **Authorization**: Any tenant member.
- **Request Body**:
  ```json
  {
    "conversation_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
    "question": "What is the policy for carrying over unused vacation days?",
    "stream": false,
    "filters": {
      "department_id": null
    }
  }
  ```
- **Response** (`200 OK` - Non-Streaming):
  ```json
  {
    "success": true,
    "data": {
      "message_id": "5c6d7e8f-9a0b-1c2d-3e4f-5a6b7c8d9e0f",
      "conversation_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
      "answer": "Under the company policy, employees accrue 12 days of annual leave per calendar year. Unused leave cannot be carried over to the subsequent calendar year and lapses automatically on December 31st [Source 1].",
      "citations": [
        {
          "source_index": 1,
          "document_id": "1e2f3a4b-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
          "document_title": "Employee_Handbook_2026.pdf",
          "page_number": 12,
          "chunk_id": "8f3b21a0-4c2e-4b6e-9821-419b4937a0c1",
          "relevance_score": 0.89
        }
      ],
      "model": "grok-beta",
      "token_usage": {
        "prompt_tokens": 620,
        "completion_tokens": 58,
        "total_tokens": 678
      }
    }
  }
  ```
- **Streaming Response** (`200 OK`, `stream: true`):
  - Returns Server-Sent Events (`text/event-stream`).
  - Events stream tokens progressively (`data: {"token": "Under"}`, `data: {"token": " the"}`) followed by a terminal citation event (`event: citations`, `data: [...]`).
- **Errors**: `400 Bad Request`, `401 Unauthorized`, `503 Service Unavailable` (LLM provider timeout).

---

## 8. Conversation Threads (`/api/v1/conversations`)

### 8.1 List User Conversations (`GET /api/v1/conversations`)
- **Purpose**: Lists past conversation threads created by the authenticated user in the current company.
- **Authentication**: Required.
- **Authorization**: User only (`user_id = auth.uid()`).
- **Response** (`200 OK`): Array of conversation summary objects sorted by `updated_at DESC`.

### 8.2 Get Conversation Messages (`GET /api/v1/conversations/{conversation_id}/messages`)
- **Purpose**: Returns the full chronological message history with citations for a conversation thread.
- **Authentication**: Required.
- **Authorization**: Thread owner only.
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "data": {
      "conversation_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
      "title": "Vacation Policy Inquiries",
      "messages": [
        {
          "id": "1a2b3c4d-...",
          "sender_type": "user",
          "content": "What is the policy for carrying over unused vacation days?",
          "created_at": "2026-10-08T14:35:00Z"
        },
        {
          "id": "5c6d7e8f-...",
          "sender_type": "assistant",
          "content": "Under the company policy...",
          "citations": [ ... ],
          "created_at": "2026-10-08T14:35:03Z"
        }
      ]
    }
  }
  ```
- **Errors**: `404 Not Found` (thread belongs to another user or tenant).

### 8.3 Delete Conversation (`DELETE /api/v1/conversations/{conversation_id}`)
- **Purpose**: Deletes a conversation thread and its associated message history.
- **Authentication**: Required.
- **Authorization**: Thread owner only.
- **Response** (`200 OK`): `{ "success": true, "data": { "deleted": true } }`.
