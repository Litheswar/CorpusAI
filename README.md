# CorpusAI — Enterprise Multi-Tenant AI Knowledge Platform

CorpusAI is a production-oriented, multi-tenant AI SaaS platform that transforms fragmented corporate documentation (PDFs, DOCX, TXT, policies, SOPs, engineering playbooks) into an intelligent, permission-aware conversational knowledge assistant.

---

## 1. Project Overview & Core Goals

Enterprises lose thousands of hours manually searching through dense handbooks and conflicting policy documents. CorpusAI solves this by providing:

1. **Multi-Tenant Workspaces**: Complete isolation between organizations (`company_id`). Data belonging to Company A is never visible, searchable, or accessible to Company B.
2. **Permission-Aware RAG**: Retrieval-Augmented Generation that enforces organizational departments and document visibility *before* vectors are retrieved.
3. **Strict Grounding & Verifiable Citations**: Conversational answers synthesized directly from authorized documents with explicit document name and page number citations.
4. **Provider-Agnostic LLM Engine**: Decoupled foundation model layer capable of switching between Grok, Qwen, and other frontier models without modifying business logic.
5. **PostgreSQL & pgvector Consolidation**: Single-engine ACID persistence uniting relational company data, document metadata, and high-dimensional vector embeddings.

---

## 2. High-Level Architecture

```text
                    CorpusAI
                       │
             ┌─────────┴─────────┐
             │                   │
        Multi-Tenant          AI/RAG
             │                   │
       Supabase Auth          Documents
             │                   │
          Company             Chunking
             │                   │
        Permissions          Embeddings
             │                   │
            RLS              pgvector
             │                   │
             └─────────┬─────────┘
                       │
                    Flask
                       │
                       ▼
                  LLM Provider
                 Grok / Qwen
                       │
                       ▼
                 Grounded Answer
                       │
                       ▼
                    React
```

---

## 3. Technology Stack

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend API** | Python 3.11+, Flask | Rich AI/NLP ecosystem, minimalist REST architecture, clean separation of concerns. |
| **Database & Auth** | Supabase (PostgreSQL 16) | Unified enterprise auth, relational storage, and storage buckets in one cohesive platform. |
| **Data Isolation** | PostgreSQL Row Level Security (RLS) | Kernel-level tenant isolation guaranteeing zero cross-company data leakage. |
| **Vector Engine** | `pgvector` with HNSW Indexing | Native vector similarity search co-located with relational tenant and permission metadata. |
| **File Storage** | Supabase Storage (S3-compatible) | Secure, tenant-partitioned private object storage for raw documents. |
| **LLM Orchestration** | Provider-Agnostic Layer (`BaseLLMProvider`) | Dynamic adapter architecture supporting xAI Grok, Alibaba Qwen, and custom models. |
| **Frontend (Phase 6)** | React 19, Vite, Tailwind CSS | High-performance, responsive single-page application with modern UI/UX design. |

---

## 4. Engineering Roadmap & Phases

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        DEVELOPMENT ROADMAP                             │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 0: System Architecture & Requirements Blueprint  ✔ [COMPLETED]   │
│ Phase 1: Database Setup, Supabase Auth & Multi-Tenant Core ✔ [COMPLETED]│
│ Phase 2: Document Ingestion, Parsing, Chunking & Storage Pipeline      │
│ Phase 3: Embedding Pipeline, pgvector Indexing & Vector Search         │
│ Phase 4: Provider-Agnostic LLM Service & Grounded RAG Pipeline         │
│ Phase 5: REST API Finalization, Conversations & Citation Endpoints     │
│ Phase 6: Frontend Development (React + Vite + Tailwind CSS)            │
│ Phase 7: Advanced Knowledge Engine (Versioning, Conflicts, Temporal)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Local Development & Setup

### 5.1 Prerequisites
- Python 3.11+
- Git
- (Optional) Supabase CLI or active Supabase cloud project

### 5.2 Python Virtual Environment Setup

```bash
# Clone the repository
git clone https://github.com/Litheswar/CorpusAI.git
cd CorpusAI

# Create virtual environment
python -m venv .venv

# Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate on Linux/macOS
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 5.3 Environment Configuration

Create a `.env` file in the `backend/` directory from `.env.example`:

```bash
cp backend/.env.example backend/.env
```

Populate `backend/.env` with your Supabase credentials:

```ini
FLASK_ENV=development
PORT=5000
HOST=127.0.0.1
DEBUG=True

SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-public-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-secret-key
JWT_SECRET=your-supabase-jwt-secret
```

> **Security Note**: Never commit `backend/.env`. The service-role key is a privileged secret that grants administrative database access and must never be exposed to clients.

### 5.4 Database Setup & Migrations

Apply the Phase 1 schema migration to your Supabase PostgreSQL instance:

```bash
# Via Supabase CLI:
supabase db push

# Or via psql / Supabase SQL Editor:
# Run the contents of supabase/migrations/001_initial_schema.sql
```

The migration automatically enables the `vector` and `uuid-ossp` extensions, creates `companies`, `departments`, and `profiles` tables, adds anti-recursion `SECURITY DEFINER` functions, and enables Row Level Security (RLS) policies.

### 5.5 Running the Flask API Server

```bash
python backend/run.py
```

The server starts at `http://127.0.0.1:5000`.

### 5.6 Running Automated Tests

Run the full automated test suite with pytest:

```bash
python -m pytest backend/tests/ -v
```

All 23 unit, integration, and security tests run in-memory and execute in under 0.2 seconds.

---

## 6. API Quickstart Examples

### Health Check
```bash
curl -X GET http://127.0.0.1:5000/api/v1/health
```
Response:
```json
{
  "service": "corpusai-api",
  "status": "ok"
}
```

### Onboard Company (Requires Supabase JWT)
```bash
curl -X POST http://127.0.0.1:5000/api/v1/companies \
  -H "Authorization: Bearer <SUPABASE_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Technologies",
    "owner_name": "Sarah Connor",
    "slug": "acme-tech"
  }'
```
Response:
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

### Get My Company Workspace
```bash
curl -X GET http://127.0.0.1:5000/api/v1/companies/me \
  -H "Authorization: Bearer <SUPABASE_JWT>"
```

---

## 7. Documentation Index

- 📋 [**Requirements Specification (`docs/requirements.md`)**](docs/requirements.md)
- 🏛️ [**Phase 0 Architecture Blueprint (`docs/phase-0-architecture.md`)**](docs/phase-0-architecture.md)
- 🗄️ [**Database Design Specification (`docs/database-design.md`)**](docs/database-design.md)
- 🧠 [**RAG & AI Architecture (`docs/rag-architecture.md`)**](docs/rag-architecture.md)
- 🌐 [**REST API Design (`docs/api-design.md`)**](docs/api-design.md)
- 🛡️ [**Security & Threat Modeling (`docs/security-design.md`)**](docs/security-design.md)
- 🚀 [**Phase 1 Implementation Report (`docs/phase-1-implementation.md`)**](docs/phase-1-implementation.md)
