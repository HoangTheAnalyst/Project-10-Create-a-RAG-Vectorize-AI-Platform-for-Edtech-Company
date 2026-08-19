# Project Structure
The project is organized into several directories, each serving a specific purpose in the overall architecture of the RAG (Retrieval-Augmented Generation) platform:
+ rag_platform: Frontend & Backend application deployment and orchestration.
+ rag_dbt: dbt (data build tool) analytics engineering and data mart definitions.
+ vector_creation: Transform files to chunks & vector embeddings, then load them into Snowflake for RAG retrieval.

# 📂 Project Directory Structure

```text
├── .github/                          # CI/CD Automation
│   └── workflows/
│       └── run_dbt_daily.yml         # Automated daily dbt execution pipeline
│
├── rag_platform/                     # Application Deployment & Orchestration
│   ├── backend/
│   │   ├── app/
│   │   │   ├── services/             # RAG retrieval logic & Snowflake connectors
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # Backend configuration & environment loading
│   │   │   ├── main.py               # FastAPI entrypoint & API routers
│   │   │   └── models.py             # Pydantic schemas & response models
│   │   ├── .env.example              # Template for backend API keys & credentials
│   │   ├── dockerfile                # FastAPI container build recipe
│   │   └── requirements.txt          # Python dependencies
│   │
│   ├── frontend/
│   │   ├── public/                   # Static assets & branding icons
│   │   ├── src/
│   │   │   ├── app/                  # Next.js 14 App Router
│   │   │   │   ├── (chat)/           # AI Study Tutor chat interface
│   │   │   │   ├── dashboard/        # Telemetry & Performance Analytics page
│   │   │   │   ├── exam/             # Quiz & Practice Examination room
│   │   │   │   ├── globals.css
│   │   │   │   └── layout.tsx
│   │   │   └── components/           # Modular UI components
│   │   │       ├── KpiCard.tsx       # Metric cards with threshold alert logic
│   │   │       ├── QuestionCard.tsx  # Interactive question components
│   │   │       └── Sidebar.tsx       # Responsive navigation drawer
│   │   ├── .env.local                # Frontend local environment variables
│   │   ├── dockerfile                # Multi-stage standalone Next.js build
│   │   ├── package.json              # Node dependencies & build scripts
│   │   ├── postcss.config.js
│   │   ├── tailwind.config.js
│   │   ├── .next.config.mjs          # Next.js build configuration & standalone output settings
│   │   └── tsconfig.json
│   │
│   └── docker-compose.yml            # Multi-service container orchestration
│
├── rag_dbt/                          # dbt Analytics Engineering & Data Marts
│   ├── macros/
│   │   └── generate_schema_name.sql  # Dynamic custom schema routing
│   ├── models/
│   │   ├── staging_documents/        # Silver Layer: Cleaned raw document chunks
│   │   │   ├── schema.yml
│   │   │   ├── source.yml
│   │   │   └── stg_chunks.sql
│   │   ├── staging_log/              # Silver Layer: Cleaned telemetry query logs
│   │   │   ├── schema.yml
│   │   │   ├── source.yml
│   │   │   └── stg_log.sql
│   │   ├── marts_documents/          # Gold Layer: Document dimensions & facts
│   │   │   ├── schema.yml
│   │   │   ├── dim_lesson.sql
│   │   │   └── fct_chunks.sql
│   │   └── marts_log/                # Gold Layer: Audit metrics & performance facts
│   │       ├── schema.yml
│   │       ├── fct_answer.sql
│   │       └── fct_log.sql
│   └── tests/                        # Data Quality & Observability Singular Tests
│       ├── assert_chunk_is_not_found.sql
│       ├── assert_chunk_vector_is_valid_array.sql
│       └── assert_no_refusal_violations.sql
│
├── vector_creation/                  # Sequential ETL & Embedding Generation
│   ├── documents/                    # Multi-stage document storage
│   │   └── {docx, md, chunking, embedded}_documents/
│   │       └── {Exercise, Lecture}/
│   │           └── {Geography, History, Literature}/
│   ├── src/                          # 6-Step sequential pipeline scripts
│   │   ├── step_1_docx_to_md_lecture.py
│   │   ├── step_2_docx_to_md_exercise.py
│   │   ├── step_3_chunking_md_lecture.py
│   │   ├── step_4_chunking_md_exercise.py
│   │   ├── step_5_embedded_documents.py
│   │   └── step_6_insert_data_to_snowflake.py
│   ├── .env.example                  # Template for vector ETL credentials
│   ├── requirements.txt
│   └── run_pipeline.py               # Master pipeline executor script
│
├── docs/                             # Architecture diagrams & technical specifications
├── images/                           # Screenshots & UI preview assets for README
└── .gitignore                        # Root gitignore