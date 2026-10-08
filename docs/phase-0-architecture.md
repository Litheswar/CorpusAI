# CorpusAI — Phase 0: System Architecture Blueprint

## 1. High-Level System Architecture

CorpusAI is designed as a modular, horizontally scalable, multi-tenant enterprise knowledge retrieval and synthesis platform. The architecture cleanly decouples the presentation layer, the stateless application backend, the unified database and vector storage infrastructure, and external AI foundation model providers.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                CLIENT / PRESENTATION LAYER                             │
│                           React 19 + Vite + Tailwind CSS SPA                           │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTPS / WSS / REST
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 API & APPLICATION LAYER                                │
│                              Stateless Python / Flask Tier                             │
│                                                                                        │
│   ┌───────────────────────────┐    ┌──────────────────────────┐    ┌───────────────┐   │
│   │   Auth & RBAC Middleware  │───▶│   Document Orchestrator  │───▶│   RAG Engine  │   │
│   └───────────────────────────┘    └──────────────────────────┘    └───────┬───────┘   │
└─────────────────────┬───────────────────────────┬──────────────────────────┼───────────┘
                      │                           │                          │
        JWT / Session │             Object Stream │                          │ Context
        Validation    │             Upload/Read   │                          ▼
                      ▼                           ▼                  ┌───────────────┐
┌───────────────────────────────────────────────────────────┐        │  LLM Service  │
│                SUPABASE BACKEND PLATFORM                  │        │  (Provider-   │
│                                                           │        │   Agnostic)   │
│  ┌───────────────────────┐    ┌────────────────────────┐  │        └───────┬───────┘
│  │     Supabase Auth     │    │    Supabase Storage    │  │                │
│  │   (GoTrue / JWT /     │    │  (S3-compatible bucket │  │         Direct │ Vendor
│  │    User Identities)   │    │   Tenant Path Scoped)  │  │         API    │ Payload
│  └───────────────────────┘    └────────────────────────┘  │                ▼
│                                                           │        ┌───────────────┐
│  ┌─────────────────────────────────────────────────────┐  │        │ LLM Providers │
│  │            PostgreSQL 16 Database Engine            │  │        │  Grok / Qwen  │
│  │                                                     │  │        └───────────────┘
│  │   - Relational Core (Companies, Users, Perms)       │  │
│  │   - Row Level Security (RLS) Active Isolation       │  │
│  │   - pgvector Extension (Embeddings & HNSW Index)    │  │
│  │   - ACID Chunk Metadata & Citations Store           │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown & Responsibilities

### 2.1 Backend: Python / Flask Application Tier
- **Framework Choice**: Python 3.11+ with Flask.
- **Role**: Serves the REST API, enforces business logic, coordinates document extraction/chunking pipelines, executes permission-aware vector queries, orchestrates conversation state, and constructs grounded prompts for the LLM.
- **Design Pattern**: Layered architectural pattern (Routes &rarr; Services &rarr; Repositories &rarr; Adapters).
- **Stateless Execution**: The Flask application holds no local session state in memory. All user sessions are authenticated via stateless JWTs, allowing horizontal scaling behind standard load balancers (e.g., NGINX, AWS ALB).

### 2.2 Database & Infrastructure: Supabase Platform
- **Supabase Auth**: Issues cryptographic JWTs, handles password hashing, OAuth integrations, user lifecycle management, and claims propagation.
- **Supabase Storage**: S3-compatible private object store housing raw uploaded documents (PDFs, DOCX, TXT) structured within private tenant buckets.
- **PostgreSQL Database**: The authoritative single source of truth for company workspaces, profiles, roles, departments, documents, chunk text, conversations, and audit trails.
- **PostgreSQL Row Level Security (RLS)**: Enforces cryptographic and query-level isolation at the engine level, guaranteeing zero cross-tenant contamination.
- **pgvector**: Native PostgreSQL extension enabling vector similarity operations (`cosine`, `L2`, `inner product`) co-located with relational tenant and permission metadata.

### 2.3 AI & Vector Search: Unified `pgvector` Architecture
- Embeddings generated for document chunks are stored directly in PostgreSQL within the `document_chunks` table as `vector(1536)` or `vector(1024)` columns.
- Vector search combines vector distance operators (`<=>` for cosine distance) with relational `WHERE` clauses (enforcing `company_id` and document permission constraints) in a single atomic SQL transaction.

### 2.4 LLM Abstraction Layer
- An abstract interface (`BaseLLMProvider`) defines contract methods for chat completion and structured generation.
- Concrete adapters (`GrokProvider`, `QwenProvider`, etc.) encapsulate vendor-specific SDKs, API formats, streaming protocols, and error mappings.

---

## 3. Multi-Tenant Architecture & Defense-in-Depth Model

Tenant isolation is the core architectural invariant of CorpusAI. Relying solely on application-level filtering (e.g., adding `WHERE company_id = ?` manually in Flask code) introduces the risk of human oversight and authorization bypass vulnerabilities (IDOR).

CorpusAI adopts a **multi-layered Defense-in-Depth Model**:

```
                       [Incoming Client Request]
                                   │
                                   ▼
 [Layer 1: JWT Signature & Expiry Validation]
  Verify cryptographic signature using Supabase Auth public key.
  Extract user identity (sub) and authenticated role.
                                   │
                                   ▼
 [Layer 2: User Identity & Profile Resolution]
  Map user UUID to internal profile record.
  Resolve active `company_id` and assigned roles (`Owner`, `Admin`, `Employee`).
                                   │
                                   ▼
 [Layer 3: Application-Level Authorization Guard]
  Flask middleware / decorators inspect route permissions.
  Reject mismatched cross-company resource IDs (IDOR prevention) before processing.
                                   │
                                   ▼
 [Layer 4: SQL Query Parameter Scoping]
  All queries explicitly inject `company_id` filters into repository methods.
                                   │
                                   ▼
 [Layer 5: PostgreSQL Row Level Security (RLS)]
  The database engine enforces RLS policies on tables using database session context
  (`request.jwt.claim.sub` or `app.current_company_id`).
  Even if application code fails to filter, PostgreSQL drops unauthorized rows.
                                   │
                                   ▼
 [Layer 6: Storage Object Path Constraints]
  Supabase Storage security policies reject access to object keys outside
  `companies/{company_id}/*`.
                                   │
                                   ▼
                      [Authorized Data Only]
```

### Defense-in-Depth Verification Matrix

| Vulnerability Scenario | Layer 1 (Auth) | Layer 2/3 (App Guard) | Layer 4/5 (DB & RLS) | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| Spoofed / Expired Token | Fails signature check | Blocked (401 Unauthorized) | Never reached | Access Denied |
| User A requests Document from Company B by ID | Valid token for Company A | Route decorator checks document tenant &rarr; Mismatch detected | RLS policy denies row access even if route check were omitted | Blocked (403/404) |
| SQL Injection in Search Filter | Escaped by parameterized query | Validated against schema | RLS restricts result set to current tenant | Zero data leak |
| Rogue / Buggy Search Query without `WHERE` clause | Passes | Passes | RLS automatically injects tenant filter at execution plan level | Only current tenant chunks returned |

---

## 4. Proposed Project Directory Structure

```text
CorpusAI/
│
├── docs/                                # Technical Blueprints & Architectural Specs
│   ├── phase-0-architecture.md          # Comprehensive technical architecture
│   ├── requirements.md                  # SRS & functional/non-functional requirements
│   ├── database-design.md               # PostgreSQL schema, indexing & RLS policies
│   ├── rag-architecture.md              # Ingestion, chunking, retrieval & LLM pipeline
│   ├── api-design.md                    # REST API OpenAPI-style endpoint contracts
│   └── security-design.md               # Threat modeling, RLS, auth & isolation rules
│
├── backend/                             # Core Python/Flask REST Application
│   ├── app/
│   │   ├── __init__.py                  # Application factory (create_app)
│   │   ├── config.py                    # Environment-driven configuration settings
│   │   │
│   │   ├── routes/                      # API HTTP Transport Layer (Controllers)
│   │   │   ├── __init__.py
│   │   │   ├── auth_routes.py           # /api/auth (Login, signup, tokens, profile)
│   │   │   ├── company_routes.py        # /api/companies (Settings, workspace config)
│   │   │   ├── user_routes.py           # /api/users (Invitations, roles, directory)
│   │   │   ├── department_routes.py     # /api/departments (Org hierarchy)
│   │   │   ├── document_routes.py       # /api/documents (Uploads, status, metadata)
│   │   │   ├── chat_routes.py           # /api/chat (Questions, streaming RAG queries)
│   │   │   └── conversation_routes.py   # /api/conversations (Threads, message logs)
│   │   │
│   │   ├── middleware/                  # Request Interceptors & Security Filters
│   │   │   ├── __init__.py
│   │   │   ├── auth_middleware.py       # JWT verification & claims decoding
│   │   │   ├── tenant_middleware.py     # Tenant context binding & validation
│   │   │   └── error_handler.py         # Standardized JSON error response handler
│   │   │
│   │   ├── models/                      # Domain Entities & Data Transfer Objects
│   │   │   ├── __init__.py
│   │   │   ├── company.py
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── chunk.py
│   │   │   └── conversation.py
│   │   │
│   │   ├── services/                    # Core Business & AI Logic Orchestration
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py          # Identity mapping & role validation
│   │   │   ├── document_service.py      # Lifecycle orchestration & storage logic
│   │   │   ├── parser_service.py        # Text extraction (PDF, DOCX, TXT)
│   │   │   ├── chunking_service.py      # Recursive token chunking & metadata tagging
│   │   │   ├── embedding_service.py     # Vector generation client
│   │   │   ├── rag_service.py           # Permission-aware retrieval & context builder
│   │   │   └── llm/                     # Provider-Agnostic LLM Engine
│   │   │       ├── __init__.py
│   │   │       ├── base_provider.py     # Abstract Base Class (BaseLLMProvider)
│   │   │       ├── grok_provider.py     # xAI Grok API implementation adapter
│   │   │       ├── qwen_provider.py     # Alibaba Qwen API implementation adapter
│   │   │       └── llm_factory.py       # Provider instantiator & fallback router
│   │   │
│   │   ├── repositories/                # Data Access Layer (PostgreSQL / Supabase)
│   │   │   ├── __init__.py
│   │   │   ├── company_repository.py
│   │   │   ├── user_repository.py
│   │   │   ├── document_repository.py
│   │   │   ├── chunk_repository.py      # pgvector similarity queries & filters
│   │   │   └── conversation_repository.py
│   │   │
│   │   └── utils/                       # Shared Utilities & Helpers
│   │       ├── __init__.py
│   │       ├── logger.py                # Structured JSON logging
│   │       ├── validators.py            # Input validation routines
│   │       └── text_cleaner.py          # Document normalization utilities
│   │
│   ├── tests/                           # Test Suite
│   │   ├── conftest.py                  # Pytest fixtures & mock clients
│   │   ├── unit/                        # Unit tests (parsers, chunkers, providers)
│   │   └── integration/                 # Integration tests (RLS, API endpoints)
│   │
│   ├── requirements.txt                 # Backend Python package dependencies
│   ├── .env.example                     # Template environment variables
│   └── run.py                           # Application WSGI development entry point
│
├── frontend/                            # React 19 + Vite Frontend (Phase 6)
│   ├── (Reserved for Phase 6)
│
├── scripts/                             # DevOps, DB Migrations & Benchmark Scripts
│   ├── migrations/                      # PostgreSQL DDL and pgvector migration scripts
│   └── seed_demo_data.py                # Synthetic tenant and benchmark document seed
│
├── .gitignore                           # Git ignore rules for Python, Node, and IDEs
└── README.md                            # High-level project documentation
```

### Responsibility of Major Directories
- `docs/`: Master architectural blueprints, security threat models, and interface contracts.
- `backend/app/routes/`: Thin HTTP controllers responsible for request validation, status codes, and JSON serialization. Contains no direct database or AI logic.
- `backend/app/services/`: Pure business logic and workflow orchestration (e.g., executing the multi-step document ingestion state machine).
- `backend/app/services/llm/`: Isolated LLM interface allowing zero-impact model provider swaps.
- `backend/app/repositories/`: All SQL and database operations, enforcing parameterization and pgvector integration.
- `backend/app/middleware/`: Security perimeter handling JWT authentication, company context binding, and global exception mapping.

---

## 5. Architectural Decision Records (ADRs)

### ADR-01: Backend Framework Selection — Python / Flask
- **Context**: The core workload of CorpusAI is document ingestion, PDF parsing, text tokenization, vector generation, and LLM streaming.
- **Decision**: Select Python with Flask over Node.js/Express, Go, or FastAPI.
- **Rationale**:
  1. The AI/ML and NLP ecosystem (PyMuPDF, python-docx, tiktoken, vector embedding SDKs) is natively mature in Python.
  2. Flask offers a minimalist, unopinionated architecture allowing strict control over application middleware, repository patterns, and dependency injection.
  3. Flask avoids unnecessary abstraction overhead while remaining straightforward to secure and maintain.
- **Tradeoffs**: Synchronous by default; long-running document ingestion tasks must be dispatched through asynchronous background worker patterns (or task queues like Celery/Redis in future phases).

### ADR-02: Backend Platform & Database Selection — Supabase (PostgreSQL)
- **Context**: A multi-tenant enterprise SaaS requires user authentication, file storage, relational entity storage, access control, and vector similarity search.
- **Decision**: Adopt Supabase as the unified backend infrastructure platform.
- **Rationale**:
  1. Supabase bundles managed PostgreSQL 16, enterprise-grade Supabase Auth (GoTrue), S3-compatible Supabase Storage, and native `pgvector` in a single cohesive service.
  2. Unifies operational maintenance: one single database instance manages user profiles, document files, permissions, and vector embeddings.
  3. PostgreSQL Row Level Security (RLS) offers kernel-level data isolation directly within the database engine.
- **Tradeoffs**: Tightly couples database tier to PostgreSQL standards (which is highly desirable for ACID compliance and SQL standardization).

### ADR-03: Vector Search Engine — Native `pgvector`
- **Context**: The RAG pipeline requires semantic vector similarity search over high-dimensional text embeddings.
- **Decision**: Use PostgreSQL with the `pgvector` extension instead of standalone vector databases.
- **Rationale**:
  1. **Atomic Joins**: Allows filtering by vector similarity while simultaneously joining against relational tenant boundaries (`company_id`), user department memberships, and document permission tables in a single SQL query plan.
  2. **ACID Transactions**: When a document is deleted, its metadata, chunks, and vector embeddings are deleted atomically in one transaction. No ghost vectors or desynchronization issues.
  3. **Row Level Security**: Native PostgreSQL RLS policies seamlessly filter vector search results automatically.
- **Tradeoffs**: At massive web scale (100M+ vectors), dedicated distributed vector engines can offer higher brute-force QPS; however, for enterprise multi-tenant knowledge bases (hundreds of thousands of chunks per tenant), `pgvector` with HNSW indexing provides sub-50ms latency with vastly superior operational simplicity.

### ADR-04: Why Not FAISS for Production?
- **Context**: Facebook AI Similarity Search (FAISS) is an industry-standard library for efficient vector similarity search.
- **Decision**: Reject FAISS as the primary production vector store for CorpusAI (while retaining it for optional standalone learning experiments).
- **Rationale**:
  1. FAISS is an in-memory index library, not a database. It does not provide durable on-disk persistence, concurrency control, or multi-user write transactions out of the box.
  2. FAISS cannot natively perform relational joins against PostgreSQL permission tables or user roles.
  3. Building multi-tenant isolation in FAISS requires either maintaining an in-memory index per tenant (high memory footprint, complex cold-start lifecycle) or managing metadata filtering in custom application memory (prone to leakage and bugs).

### ADR-05: Why Not Chroma?
- **Context**: Chroma is a popular open-source embedding database for AI applications.
- **Decision**: Do not introduce Chroma into the production architecture.
- **Rationale**:
  1. Adding Chroma introduces a second database server to operate, secure, backup, and monitor alongside PostgreSQL.
  2. Creates a "Dual Source of Truth" problem: document metadata exists in PostgreSQL, while chunks and vectors exist in Chroma. If an update or deletion succeeds in one system and fails in the other, data becomes desynchronized.
  3. Multi-tenancy and granular RBAC must be managed and synchronized across two disconnected security boundaries.
  4. Supabase PostgreSQL with `pgvector` already fulfills all vector storage requirements natively.

### ADR-06: Provider-Agnostic LLM Abstraction Layer
- **Context**: The LLM landscape evolves rapidly. Enterprise clients may require different foundation models (e.g., xAI Grok, Alibaba Qwen, DeepSeek, OpenAI) based on regional data governance, cost, or reasoning accuracy.
- **Decision**: Implement an abstract base interface `BaseLLMProvider` with modular provider adapters.
- **Rationale**:
  1. Decouples prompt construction, citation synthesis, and conversation management from any specific vendor's SDK or wire protocol.
  2. Enables dynamic runtime provider switching or tenant-specific model configurations (e.g., Company A uses Grok; Company B uses Qwen).
  3. Simplifies testing by allowing seamless substitution of a `MockLLMProvider` in automated CI/CD pipelines.

---

## 6. Answers to the 20 Architectural Review Questions

### 1. How does a user authenticate?
The user submits credentials to Supabase Auth (`/auth/v1/token` or via the Supabase client SDK). Supabase validates credentials and issues an RS256-signed JWT containing the user's UUID (`sub`), email, and token metadata. The frontend client attaches this JWT as a Bearer token in the HTTP `Authorization` header on all API requests to the Flask backend. The Flask `AuthMiddleware` verifies the cryptographic signature using Supabase's public keys.

### 2. How does a user become associated with a company?
During initial tenant creation, the user creates a company record; the system inserts a record into `companies` and links the user's Supabase UUID to a new record in `profiles` with `company_id` and `role = 'owner'`. For invited employees, a Company Owner or Admin generates an invitation record containing the target email and `company_id`. When the employee completes signup via the invitation link, their profile record is created and tied to that `company_id`.

### 3. How does multi-tenancy work?
Multi-tenancy is implemented through a shared-database, shared-schema model with **mandatory tenant discriminator columns** (`company_id`) on all domain tables (`profiles`, `departments`, `documents`, `document_chunks`, `conversations`, `messages`, `document_permissions`). Isolation is guaranteed via double enforcement: Flask application middleware and PostgreSQL Row Level Security (RLS).

### 4. How is Company A isolated from Company B?
1. **Network & Auth**: Every request resolves the caller's verified `company_id` from their authenticated profile.
2. **Application Boundary**: Every repository method scopes SQL statements with `WHERE company_id = :current_company_id`.
3. **Database RLS**: PostgreSQL RLS policies evaluate `company_id = current_setting('app.current_company_id')`. Queries attempting to read or write rows with another company's ID return empty sets or throw access violation errors.
4. **Storage Isolation**: File storage paths are partitioned by company (`companies/{company_id}/*`), with Supabase Storage access policies blocking cross-path reads.

### 5. How are documents stored?
Raw binary files (PDF, DOCX, TXT) are uploaded to a private Supabase Storage bucket under the path `companies/{company_id}/documents/{document_id}/{filename}`. Document metadata, file size, MIME type, storage path, status, and processing timestamps are stored in the PostgreSQL `documents` table.

### 6. How are documents processed?
Processing follows a deterministic finite state machine managed by `DocumentService`:
`UPLOADED` &rarr; `PROCESSING` &rarr; `EXTRACTED` (text extracted via PyMuPDF/python-docx preserving page boundaries) &rarr; `CHUNKED` (text split into recursive token windows with overlap) &rarr; `EMBEDDED` (embeddings computed via embedding model) &rarr; `INDEXED` (vectors committed to `document_chunks` with HNSW indexing) &rarr; `READY`. Failures at any stage transition the document to `FAILED` with an error message logged.

### 7. How are chunks stored?
Chunks are stored as individual rows in the `document_chunks` table in PostgreSQL. Each row contains `chunk_id`, `document_id`, `company_id`, `content` (clean text snippet), `page_number`, `chunk_index`, `metadata` (JSONB), and `embedding` (`vector` type).

### 8. Where are embeddings stored?
Embeddings are stored natively within PostgreSQL in the `document_chunks.embedding` column using the `pgvector` extension. They are indexed using HNSW (Hierarchical Navigable Small World) indexes with cosine distance metrics.

### 9. How does vector retrieval work?
When a user asks a question, the question text is transformed into a dense vector using the embedding service. The backend executes a similarity search query using the pgvector cosine distance operator `<=>`, computing the distance between the query vector and chunk vectors in `document_chunks`. The query sorts by distance ascending and returns the Top-$K$ (e.g., $K=5$) most relevant chunks above a similarity threshold.

### 10. How does permission-aware retrieval work?
The vector search SQL query executes with strict multi-clause relational filtering *prior* to or *during* the vector scan:
```sql
WHERE company_id = :company_id
  AND (
    visibility = 'company' 
    OR (visibility = 'department' AND department_id = :user_department_id)
    OR document_id IN (SELECT document_id FROM document_permissions WHERE user_id = :user_id)
  )
ORDER BY embedding <=> :query_vector LIMIT :k;
```
RLS additionally enforces this at the database level. Unauthorized chunks are never selected, eliminating the risk of data leakage.

### 11. How does the LLM receive context?
The RAG service compiles a prompt comprising:
1. **System Prompt**: Enforcing strict grounding, anti-hallucination rules, and citation format requirements.
2. **Retrieved Context**: A formatted block containing the retrieved chunk texts, tagged with sequential source numbers, document titles, and page numbers:
   `[Source 1: Employee_Handbook.pdf, Page 12] Casual leave allowance is 12 days...`
3. **Conversation History**: Recent conversational turns (last $N$ messages) for conversational continuity.
4. **User Question**: The user's prompt.

### 12. How are citations generated?
Retrieved chunks retain explicit source references (`document_title`, `document_id`, `page_number`, `chunk_index`). The LLM prompt instructs the model to cite its factual assertions using bracketed tags matching the sources (e.g., `[Source 1]`). The backend parses these citations from the LLM output and pairs them with verifiable source metadata objects returned in the API response payload.

### 13. What happens when the answer isn't found?
If the vector similarity score of all retrieved chunks falls below a relevance confidence threshold (or if zero chunks match permission filters), or if the LLM analyzes the context and finds no relevant information, the system returns a standard fallback response:
*"I could not find sufficient information in your authorized company documents to answer this question. Please consult your administrator or verify that the relevant document has been uploaded."*
The LLM is strictly prohibited from guessing or utilizing external general knowledge to fabricate corporate policies.

### 14. How are conversations stored?
Conversations are stored in the PostgreSQL `conversations` table (`conversation_id`, `company_id`, `user_id`, `title`, timestamps). Individual messages are stored in the `messages` table (`message_id`, `conversation_id`, `sender_type` ['user', 'assistant'], `content`, `citations` [JSONB], timestamps). Each conversation is tied to both the user and company.

### 15. How can document versions be supported later?
The database schema includes `documents.version` (integer) and `document_chunks.document_version` (integer), plus a `superseded_by` foreign key. Future extensions will allow tagging documents as active or superseded, enabling queries to filter by active version (`WHERE is_current = true`) or query historical versions for audit comparisons.

### 16. How can conflicting knowledge be detected later?
Because chunks carry rich metadata (document version, publication date, source authority level), future RAG pipelines can implement a Multi-Source Conflict Detection stage: when Top-$K$ retrieval fetches chunks from different documents with opposing factual claims, an intermediate evaluator prompt detects contradictory claims and highlights the discrepancy to the user (e.g., *"Document A states X, whereas Document B states Y"*).

### 17. What APIs will the backend expose?
The backend exposes RESTful endpoints partitioned into resource modules:
- `/api/auth`: Signup, login, refresh, profile retrieval.
- `/api/companies`: Tenant profile, workspace settings.
- `/api/users`: Member invitations, role management.
- `/api/departments`: Department CRUD operations.
- `/api/documents`: Upload, processing status polling, deletion, metadata updates.
- `/api/chat`: Non-streaming and streaming question answering.
- `/api/conversations`: Thread history, message listings.

### 18. What security boundaries exist?
1. **Network Perimeter**: HTTPS / TLS 1.3 encryption in transit.
2. **Auth Boundary**: Cryptographically verified RS256 JWTs issued by Supabase Auth.
3. **Application RBAC**: Role-based access control and tenant verification in Flask middleware.
4. **Database Perimeter**: PostgreSQL RLS policies at the engine level.
5. **Storage Perimeter**: S3-compatible bucket-level path policies.
6. **Prompt Injection Boundary**: Ingested document content treated as untrusted data wrapped in isolated system prompt delimiters.

### 19. Why are we using pgvector instead of FAISS/Chroma for production?
- **Unified Engine**: Eliminates dual-database maintenance; vectors and business entities live in one ACID-compliant PostgreSQL instance.
- **Transactional Consistency**: Cascading deletes immediately remove text chunks and embeddings without leaving orphan vectors.
- **Relational Filtering**: Joins vector similarity searches with complex tenant and RBAC permission tables in a single query plan.
- **Engine-Level RLS**: PostgreSQL Row Level Security enforces tenant isolation automatically during vector queries.

### 20. What exactly will be implemented in Phase 1?
Phase 1 focuses exclusively on the foundation:
1. Setting up the PostgreSQL database schema and migrations on Supabase.
2. Enabling the `pgvector` extension and creating initial core tables.
3. Configuring Row Level Security (RLS) policies for tenant isolation.
4. Initializing the Flask application structure, configuration management, and database connection pooling.
5. Implementing Supabase Auth integration and JWT validation middleware.
6. Implementing the tenant provisioning and user invitation workflows.
*(No document ingestion, chunking, or LLM querying is implemented until Phases 2, 3, and 4).*
