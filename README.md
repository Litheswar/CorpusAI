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
│ Phase 0: System Architecture & Requirements Blueprint  ◀ [CURRENT]     │
│ Phase 1: Database Setup, Supabase Auth & Multi-Tenant Core             │
│ Phase 2: Document Ingestion, Parsing, Chunking & Storage Pipeline      │
│ Phase 3: Embedding Pipeline, pgvector Indexing & Vector Search         │
│ Phase 4: Provider-Agnostic LLM Service & Grounded RAG Pipeline         │
│ Phase 5: REST API Finalization, Conversations & Citation Endpoints     │
│ Phase 6: Frontend Development (React + Vite + Tailwind CSS)            │
│ Phase 7: Advanced Knowledge Engine (Versioning, Conflicts, Temporal)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Phase 0 Documentation Blueprint

All foundational blueprints and technical specifications have been authored and reviewed under the `docs/` directory:

- 📋 [**Requirements Specification (`docs/requirements.md`)**](docs/requirements.md): Functional and non-functional requirements, user personas, roles, and boundaries.
- 🏛️ [**System Architecture (`docs/phase-0-architecture.md`)**](docs/phase-0-architecture.md): Component breakdown, defense-in-depth model, directory structure, Architectural Decision Records (ADRs), and answers to all 20 architectural review questions.
- 🗄️ [**Database Design (`docs/database-design.md`)**](docs/database-design.md): Entity-relationship diagrams, complete schema specifications for all tables, pgvector HNSW indexing, and Row Level Security (RLS) policies.
- 🧠 [**RAG & AI Architecture (`docs/rag-architecture.md`)**](docs/rag-architecture.md): Document lifecycle state machine, parsing, chunking, chunk metadata schema, permission-aware vector search, provider-agnostic LLM interface, and citation mechanics.
- 🌐 [**API Design (`docs/api-design.md`)**](docs/api-design.md): RESTful endpoint contracts for auth, companies, users, departments, documents, conversations, and chat completions.
- 🛡️ [**Security & Threat Model (`docs/security-design.md`)**](docs/security-design.md): JWT validation, defense-in-depth enforcement, untrusted content handling, indirect prompt injection defense, and audit logging.

---

## 6. Current Phase Status: Phase 0 Completed

Phase 0 is strictly a design, architecture, and requirements phase. No production code or migrations were created in this phase. The project is fully specified and ready to proceed to **Phase 1: Database Setup, Supabase Auth & Multi-Tenant Core**.
