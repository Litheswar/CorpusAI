# CorpusAI — System Requirements Specification (SRS)

## 1. Executive Summary & Problem Statement

Modern enterprises amass terabytes of institutional knowledge across fragmented formats: PDF handbooks, DOCX specifications, TXT incident logs, HR policies, engineering playbooks, SOPs, and financial guides. 

Employees spend an estimated 20–30% of their work week manually searching for information, asking colleagues, or relying on outdated documents. 

**CorpusAI** is an enterprise-grade, multi-tenant AI Knowledge Platform and Retrieval-Augmented Generation (RAG) SaaS designed to solve this problem. CorpusAI enables organizations to securely upload internal documents, automatically parse and index institutional knowledge, and query it via conversational AI with verifiable citations and strict tenant and permission isolation.

---

## 2. Stakeholders, User Personas, & Roles

CorpusAI operates on a multi-tier role hierarchy spanning the platform level and company/tenant level.

### 2.1 Platform Level

| Role | Scope | Key Capabilities |
| :--- | :--- | :--- |
| **Platform Admin** | Global Platform | Manages tenant provisioning, monitors global system health, reviews infrastructure telemetry, oversees billing and provider quotas, and operates outside tenant boundaries without accessing tenant-private data. |

### 2.2 Company Level (Tenant)

| Role | Scope | Key Capabilities |
| :--- | :--- | :--- |
| **Company Owner** | Single Company | Root tenant user. Can create and configure company workspaces, manage subscription tiers, invite and remove users, assign roles, define departments, upload/delete any company document, configure granular document visibility, and audit access logs. |
| **Company Admin** | Single Company | Tenant operational manager. Can manage employees, assign department memberships, manage and categorize documents, view knowledge usage telemetry, and configure department-level knowledge collections. Cannot delete the workspace or demote the Company Owner. |
| **Employee** | Single Company | Standard tenant user. Can access authorized company and department knowledge, converse with the AI assistant, review grounded answers with precise page-level citations, and manage personal chat history. Cannot view unauthorized documents or administrative panels. |

### 2.3 Future Extensibility Roles
The role system is designed as an enum/relation pattern to accommodate future roles without database schema migrations:
- **Department Manager**: Delegated admin for a specific department (e.g., Engineering Lead managing only Engineering docs).
- **External Auditor / Guest**: Read-only access to a strictly bounded subset of compliance documents with time-limited sessions.
- **Service Account / API Client**: Programmatic machine-to-machine access for CI/CD document sync or webhook ingestion.

---

## 3. Functional Requirements

### 3.1 Tenant & Workspace Management
- **FR-1.1**: The system shall support multi-tenancy where all data (documents, chunks, embeddings, conversations, users) is strictly bound to a `company_id`.
- **FR-1.2**: A tenant signup flow shall create a new company workspace, provision the creator's profile, and automatically grant the `Company Owner` role.
- **FR-1.3**: Company Owners and Admins shall be able to invite team members via email with role and department pre-assignment.
- **FR-1.4**: Users shall belong to one primary tenant workspace at a time (extensible to multi-workspace switching in future versions).

### 3.2 Document Ingestion & Management
- **FR-2.1**: The system shall support ingestion of PDF, DOCX, and TXT files up to 50MB per document.
- **FR-2.2**: Documents shall be stored in tenant-isolated Supabase Storage buckets under structured paths (`companies/{company_id}/documents/{document_id}/{filename}`).
- **FR-2.3**: Documents shall transition through a deterministic lifecycle state machine:
  `UPLOADED` &rarr; `PROCESSING` &rarr; `EXTRACTED` &rarr; `CHUNKED` &rarr; `EMBEDDED` &rarr; `INDEXED` &rarr; `READY` (or `FAILED`).
- **FR-2.4**: Ingestion failures at any step shall record error codes and user-safe failure reasons without leaving orphaned chunks or corrupt states.
- **FR-2.5**: Admins and Owners shall be able to archive or delete documents. Deletion shall trigger cascading deletion of text chunks, vectors, and raw storage objects.

### 3.3 Chunking & Embedding Pipeline
- **FR-3.1**: Text extraction must preserve document structural markers (pages, headings, tables).
- **FR-3.2**: Extracted text shall be cleaned (whitespace normalization, artifact removal) and chunked using recursive token-aware chunking with sliding overlaps.
- **FR-3.3**: Each chunk shall preserve rich metadata: `company_id`, `document_id`, `page_number`, `chunk_index`, `department_id`, and `version`.
- **FR-3.4**: Text chunks shall be converted into dense vector embeddings via a unified embedding model and persisted into PostgreSQL with `pgvector`.

### 3.4 Permission-Aware RAG & Search
- **FR-4.1**: Semantic vector search shall execute strictly within the user's tenant boundary (`company_id`).
- **FR-4.2**: Retrieval shall enforce document-level and department-level visibility filters *before or during* the similarity search query. Under no circumstances may unauthorized chunks be retrieved into memory.
- **FR-4.3**: Top-$K$ relevant chunks shall be retrieved with cosine distance or inner product thresholds.
- **FR-4.4**: Context assembly shall structure retrieved chunks with document titles and page numbers for the LLM.

### 3.5 Conversational Chat & LLM Response Generation
- **FR-5.1**: Users shall interact with an AI assistant through persistent conversation threads.
- **FR-5.2**: The assistant shall generate strictly grounded answers synthesized from retrieved context chunks.
- **FR-5.3**: The assistant must explicitly state when the retrieved context does not contain sufficient information to answer the question, refusing to hallucinate.
- **FR-5.4**: The system must provide verifiable citations detailing the document title, page number, and chunk reference for every factual claim.
- **FR-5.5**: The LLM layer must use a provider-independent abstraction layer capable of switching between Grok, Qwen, or other models without changing RAG business logic.

---

## 4. Non-Functional Requirements

### 4.1 Security & Data Isolation
- **NFR-1.1**: **Zero Cross-Tenant Leakage**: Under zero circumstances may Company A inspect, search, or infer data belonging to Company B.
- **NFR-1.2**: **Defense-in-Depth**: Isolation must be enforced at both the Flask application layer and the PostgreSQL database layer (Row Level Security / RLS).
- **NFR-1.3**: **Least Privilege**: Storage and database access shall use fine-grained authenticated tokens and service roles restricted to trusted backend services.
- **NFR-1.4**: **Untrusted Content Sanitization**: Ingested documents and user questions are treated as untrusted inputs to mitigate indirect prompt injection attacks.

### 4.2 Performance & Scalability
- **NFR-2.1**: **Query Latency**: End-to-end question answering (retrieval + LLM first token) target: $\le 1.8$ seconds; completion target: $\le 4.0$ seconds.
- **NFR-2.2**: **Vector Search Latency**: Cosine similarity query on indexed collections of 500k chunks target: $\le 50$ ms using pgvector HNSW/IVFFlat indexes.
- **NFR-2.3**: **Document Processing Throughput**: A standard 50-page PDF handbook should be processed, chunked, embedded, and indexed within 30 seconds.

### 4.3 Reliability & Availability
- **NFR-3.1**: 99.9% uptime target for the core query API.
- **NFR-3.2**: Stateless Flask application tier to allow horizontal auto-scaling behind a reverse proxy / load balancer.
- **NFR-3.3**: Circuit breakers and retry logic with exponential backoff on all external LLM provider calls.

### 4.4 Maintainability & Extensibility
- **NFR-4.1**: Clean architectural separation: Routes &rarr; Services &rarr; Repositories &rarr; Database.
- **NFR-4.2**: Decoupled LLM provider interface allowing plug-and-play addition of new model vendors.
- **NFR-4.3**: Future-proof schemas supporting document versioning, conflict detection, and temporal queries.

---

## 5. Scope & Phase Boundaries

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PHASE ROADMAP OVERVIEW                          │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 0: System Architecture & Requirements Blueprint (CURRENT)       │
│ Phase 1: Database Setup, Supabase Auth & Multi-Tenant Core             │
│ Phase 2: Document Ingestion, Parsing, Chunking & Storage Pipeline      │
│ Phase 3: Embedding Pipeline, pgvector Indexing & Vector Search         │
│ Phase 4: Provider-Agnostic LLM Service & Grounded RAG Pipeline         │
│ Phase 5: REST API Finalization, Conversations & Citation Endpoints     │
│ Phase 6: Frontend Development (React + Vite + Tailwind CSS)            │
│ Phase 7: Advanced Knowledge Engine (Versioning, Conflicts, Temporal)   │
└────────────────────────────────────────────────────────────────────────┘
```

*Strict Rule: Phase 0 delivers only the technical architecture, design specifications, data models, and API blueprints. No production implementation code is created in Phase 0.*
