# 🏛️ Architecture Decision Records (ADRs) & Technical Trade-offs

This document outlines the foundational architecture decisions, technology selections, and engineering trade-offs made during the design and implementation of the RAG AI Platform & Telemetry Observability ecosystem.

---

## 1. Embedding Strategy: Managed Cloud API Calls vs. Self-Hosted Models

* **Context:** Hosting open-source multilingual embedding models (such as `BAAI/bge-m3`) locally requires between 500 MB and 2 GB of memory on boot, excluding runtime dependencies.
* **Decision:** Utilize managed external API calls for vector embeddings instead of maintaining a self-hosted inference service.
* **Rationale & Trade-offs:**
  * The free/demo deployment tier operates under severe resource constraints (512 MB RAM, 0.1 vCPU), making in-memory model loading technically infeasible.
  * While daily rate limits are imposed on external API calls, the curated volume of demo educational documents makes this a practical trade-off, achieving zero-cost infrastructure hosting.

---

## 2. Ingestion Storage: Direct Append to Snowflake vs. Dedicated OLTP Database

* **Context:** The application captures interaction telemetry and session logs to power operational analytics and data auditing.
* **Decision:** Bypass dedicated transactional databases (e.g., PostgreSQL/MySQL) and append telemetry directly into Snowflake's `RAW.QUERY_LOGS` table.
* **Rationale & Trade-offs:**
  * Accelerates time-to-market for the initial product release.
  * The platform runs a focused single-model workload without complex transactional domain entities (e.g., billing subscriptions, user reviews). Entities such as `users`, `sessions`, and `conversations` are safely flattened into individual audit rows without risk of relational fragmentation or unbounded row expansion.

---

## 3. Dimensional Modeling: Omission of a Dedicated `dim_date` Table

* **Context:** Traditional enterprise data warehouses implement a dedicated date dimension (`dim_date`) for multi-tier fiscal, quarterly, and calendar period slicing.
* **Decision:** Omit `dim_date` from the initial dimensional schema.
* **Rationale & Trade-offs:**
  * Document knowledge marts (`marts_documents`) require no temporal slicing.
  * Telemetry marts (`marts_log`) only require day-level operational trend aggregations, which are handled efficiently using `DATE_TRUNC('day', created_at)`. Adding a dedicated date dimension would introduce unnecessary pipeline overhead without delivering tangible analytical value at this stage.

---

## 4. Document Lifecycle: Deduplication vs. SCD Type 2 History Tracking

* **Context:** Evaluating whether document revisions should be versioned using Slowly Changing Dimension Type 2 (SCD Type 2).
* **Decision:** Implement latest-state deduplication partitioned by `ingested_at` across `marts.dim_lesson` and `marts.fct_chunks`.
* **Rationale & Trade-offs:**
  * Historical textbook versions provide minimal pedagogical or analytical value for active study sessions.
  * **Hallucination Prevention:** RAG retrieval pipelines must ground responses exclusively in current, validated curriculum standards. Retaining obsolete chunks increases the risk of retrieving outdated information, superseded test questions, or sensitive content that was intentionally removed.

---

## 5. Web Stack: Next.js (Frontend) + FastAPI (Backend) vs. Low-Code Frameworks

* **Context:** Choosing between rapid UI scaffolding tools (e.g., Streamlit, Gradio) and a decoupled full-stack architecture.
* **Decision:** Construct the user interface with Next.js (App Router, Tailwind CSS) backed by a FastAPI service layer.
* **Rationale & Trade-offs:**
  * While low-code frameworks offer fast prototyping, their rigid layouts fail to deliver the polished, responsive experience required to engage students and educational centers effectively.
  * Next.js paired with FastAPI delivers modern interface control, modular component reusability, clear separation of concerns, and clean container orchestration via Docker Compose.

---

## 6. Privacy & Governance: Embedding Telemetry Dashboards via PII Anonymization

* **Context:** Exposing query metrics and student learning telemetry in a shared dashboard could introduce data privacy concerns.
* **Decision:** Embed the analytics dashboard directly into the unified web platform while enforcing strict one-way hashing on all identifiers.
* **Rationale & Trade-offs:**
  * **Data Privacy:** Sensitive client identifiers (IP addresses, Session IDs, Conversation IDs) are anonymized via MD5 hashing (`hashed_client_ip`, `session_sk`) before exposure in the analytical Gold Marts.
  * **Unified Experience:** Stakeholders can evaluate the end-to-end loop directly: submitting queries in the chat room and observing immediate telemetry updates on the dashboard without configuring external BI tools.

---

## 7. Data Architecture: Medallion Architecture (dbt + Snowflake) vs. Raw Table Views

* **Context:** Deciding whether to query raw ingestion tables directly for dashboard metrics to simplify data pipelines.
* **Decision:** Enforce structured Medallion transitions (`RAW` $\rightarrow$ `STAGING` $\rightarrow$ `MARTS`) managed through dbt transformations and data tests.
* **Rationale & Trade-offs:**
  * Raw records can contain structural variations, unparsed vector arrays, and malformed strings.
  * The Gold Mart layer precomputes key performance indicators (such as `similarity_score_diff`, `no_chunks_retrieved`, and `high_latency` flags), applies surrogate keys, and enforces schema constraints, ensuring deterministic query execution and reliable dashboard reporting.

---

## 8. Retrieval Hyperparameters: Threshold 0.55, Top-8 Chunks, 1024-dim, Temperature 0.2–0.3

* **Context:** Balancing semantic context coverage against response precision and pedagogical accuracy.
* **Decision:** Standardize runtime defaults to: `Threshold = 0.55`, `Limit = 8 chunks`, `Vector Dimension = 1024`, `Temperature = 0.2–0.3`.
* **Rationale & Trade-offs:**
  * **Grounding Anchor:** A 0.55 similarity threshold filters out irrelevant context. When relevant chunks are found, a lower temperature ($0.2–0.3$) forces the model to anchor its answers strictly in the retrieved material, mitigating hallucinations.
  * **Semantic Resolution:** A 1024-dimensional vector space provides sufficient expressiveness to differentiate specialized subject terminology across Geography, History, and Literature.

---

## 9. Content Processing: DOCX to Markdown Normalization Prior to Chunking

* **Context:** Curriculum source materials originate as `.docx` files containing complex layout formatting, arbitrary line breaks, and inconsistent heading hierarchies.
* **Decision:** Standardize source files into clean Markdown before semantic chunking and embedding generation.
* **Rationale & Trade-offs:**
  * Markdown delivers clean, structured syntax that allows chunking algorithms to preserve semantic boundaries (headings, sections, and question stems).
  * Dividing the ingestion pipeline into discrete, sequential scripts ensures fault isolation, simplifies debugging, and enables validation at each stage prior to vectorization.

---

## 10. Future Capabilities & System Roadmap

The architecture provides modular extension points to accommodate future platform enhancements:
* **Remediation Feedback Engine:** Automated pedagogical diagnostics explaining *why* a selected multiple-choice answer was incorrect, linking directly to the relevant theory chunk.
* **Student Mastery Matrix:** Granular competency tracking dashboards monitoring individual learning progression over time.
* **LaTeX Formula Rendering:** Native parsing and rendering for complex mathematical and scientific notation.
* **Dedicated OLTP Database:** Decoupling transactional app state from Snowflake as active concurrent user volume scales.

## 11. Telemetry Cadence: Daily Batch Reporting vs. Real-Time Streaming Dashboards

* **Context:** Evaluating whether to implement real-time streaming pipelines (e.g., message brokers, continuous micro-batching) for live telemetry updates versus scheduled daily batch processing.
* **Decision:** Execute telemetry transformations and reporting on a scheduled daily batch cadence via automated CI/CD (`run_dbt_daily.yml`).
* **Rationale & Trade-offs:**
  * **Target Audience & Intent:** The dashboard is fundamentally designed as an executive operational report rather than an infrastructure alert system. Leadership and C-level stakeholders require stabilized, day-over-day aggregated metrics (e.g., daily query volumes, SLA breach rates, retrieval accuracy trends) to make informed strategic decisions, not noisy second-by-second fluctuations.
  * **Cost & Resource Optimization:** Streaming pipelines and continuous warehouse uptime generate unnecessary cloud compute costs on Snowflake. Daily off-peak batch execution achieves zero idle compute overhead while satisfying all business and operational requirements.