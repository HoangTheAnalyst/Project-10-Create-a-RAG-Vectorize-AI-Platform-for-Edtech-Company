# 🚀 Deployment Guide: RAG AI Platform & Data Warehouse Pipeline

This document provides complete instructions for setting up, executing, and deploying the RAG AI Platform across local development, containerized web services, and automated CI/CD environments.

---

## ⚠️ Security Notice: Snowflake Access Control & Role Permissions

To adhere to security best practices and the Principle of Least Privilege (PoLP), configure two distinct levels of database access:

1. **Pipeline & Modeling Modules (`vector_creation` & `rag_dbt`):**
   * **Required Role:** `ACCOUNTADMIN` or a dedicated data engineering role with full `CREATE TABLE`, `CREATE SCHEMA`, and `WRITE/INSERT` privileges on the `RAG_AI_PLATFORM` database (`RAW`, `STAGING`, `MARTS`, `STAGING_LOG`, `MARTS_LOG` schemas).
   * **Used in:** `vector_creation/.env` and `~/.dbt/profiles.yml`.

2. **Application Runtime Service (`rag_platform/backend`):**
   * **Required Role:** A restricted application service role with minimal operational access:
     * `SELECT` permission on Gold Marts (`MARTS.FCT_CHUNKS`, `MARTS.DIM_LESSON`, `MARTS_LOG.FCT_LOG`).
     * `INSERT` permission exclusively on `RAW.QUERY_LOGS` for telemetry ingestion.
   * **Used in:** `rag_platform/backend/.env`.

> **💡 User Creation Tip:** You can provision dedicated users and configure fine-grained role-based access control (RBAC) directly in Snowflake. For exact DDL statements and administrative queries, refer to the [important_sql.md](important_sql.md) file.
---

## 📋 Prerequisites

Ensure the following environments and tools are installed:
* **Python 3.10+** and **Node.js 18+** / `npm`
* **Docker & Docker Compose** (for containerized execution)
* **Snowflake Account** with target database `RAG_AI_PLATFORM` provisioned
* **API Keys**:
  * `COHERE_API_KEY`: For vector embedding inference
  * `GROQ_API_KEY`: For LLM response synthesis

---

## Option 1: Full Local Deployment (End-to-End Pipeline)

Follow this sequence to ingest document data, run data warehouse transformations, and start the application.

### Stage 1: Document Processing & Vector Ingestion (`vector_creation`)

1. **Set up the virtual environment:**
   ```bash
   cd vector_creation
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure `.env` (Admin / Write Role):**
   Create a `.env` file from `.env.example` using an account with `ACCOUNTADMIN` or full write privileges:
   ```ini
   SNOWFLAKE_USER=YOUR_USERNAME
   SNOWFLAKE_PASSWORD=YOUR_PASSWORD
   SNOWFLAKE_ACCOUNT=YOUR_ACCOUNT_IDENTIFIER
   SNOWFLAKE_ROLE=ACCOUNTADMIN
   SNOWFLAKE_WAREHOUSE=COMPUTE_WH
   SNOWFLAKE_DATABASE=RAG_AI_PLATFORM
   SNOWFLAKE_SCHEMA=RAW
   ```
3. **Putting Source Documents**: Place your source `docx` documents in the `vector_creation/documents/docx_documents/{Exercise, Lecture}` directory. 
4. **Run the Ingestion Pipeline:**
   ```bash
   python vector_creation/run_pipeline.py
   deactivate
   cd ..
   ```

---

### Stage 2: Data Transformation & Testing (`rag_dbt`)

1. **Configure dbt Connection (`~/.dbt/profiles.yml`):**
   Set up your connection profile using an `ACCOUNTADMIN` or transformation-authorized role:
   ```yaml
   rag_dbt:
     target: dev
     outputs:
       dev:
         type: snowflake
         threads: 16
         account: YOUR_ACCOUNT_IDENTIFIER
         user: YOUR_USERNAME
         password: YOUR_PASSWORD
         role: ACCOUNTADMIN
         database: RAG_AI_PLATFORM
         warehouse: SNOWFLAKE_LEARNING_WH
         schema: RAW
   ```

2. **Execute Transformations & Data Quality Tests:**
   ```bash
   cd rag_dbt
   
   # Verify Snowflake connection
   dbt debug

   # Run Staging and Gold Marts models
   dbt run

   # Run singular and generic data tests
   dbt test
   
   cd ..
   ```

---

### Stage 3: Application Services (`rag_platform`)

#### 1. FastAPI Backend
```bash
cd rag_platform/backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

Create `rag_platform/backend/.env` using credentials with restricted permissions (`SELECT` on Marts, `INSERT` on `RAW.QUERY_LOGS`):
```ini
SNOWFLAKE_USER=YOUR_RESTRICTED_APP_USER
SNOWFLAKE_PASSWORD=YOUR_PASSWORD
SNOWFLAKE_ACCOUNT=YOUR_ACCOUNT_IDENTIFIER
SNOWFLAKE_ROLE=APP_SERVICE_ROLE
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=RAG_AI_PLATFORM
SNOWFLAKE_SCHEMA=MARTS
COHERE_API_KEY=YOUR_COHERE_API_KEY
GROQ_API_KEY=YOUR_GROQ_API_KEY
```

Start the API service:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*API docs available at `http://localhost:8000/docs`.*

---

#### 2. Next.js Frontend
Open a separate terminal window:
```bash
cd rag_platform/frontend
npm install
```

Create `rag_platform/frontend/.env.local`:
```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Launch the development server:
```bash
npm run dev
```
*Access UI at `http://localhost:3000`.*

---

## Option 2: Containerized Web Platform (`docker-compose`)

Run the complete web stack (`backend` and `frontend`) inside isolated Docker containers.

1. **Navigate to the platform directory:**
   ```bash
   cd rag_platform
   ```

2. **Verify Environment Configurations:**
   * `backend/.env`: Valid credentials (restricted app role) and API keys.
   * `frontend/.env.local`: Target API URL pointing to the backend service (`http://backend:8000` or `http://localhost:8000`).

3. **Build and Start Containers:**
   ```bash
   docker-compose up --build -d
   ```

4. **Access Web Interfaces:**
   * **Frontend UI (Chat, Exam Room, Telemetry Dashboard):** `http://localhost:3000`
   * **FastAPI Swagger Documentation:** `http://localhost:8000/docs`

5. **Stop Services:**
   ```bash
   docker-compose down
   ```

---

## (Optional) Automated dbt Pipeline Execution (GitHub Actions)

The `.github/workflows/run_dbt_daily.yml` workflow automates staging-to-marts transformations and executes test suites on a scheduled daily cadence.

### 1. Configure GitHub Repository Secrets
Navigate to **Settings > Secrets and variables > Actions** in your GitHub repository and define the following secrets:
* `SNOWFLAKE_ACCOUNT`: Your Snowflake account locator/identifier.
* `SNOWFLAKE_USER`: Your Snowflake username.
* `SNOWFLAKE_PASSWORD`: Your Snowflake password.
* `SNOWFLAKE_ROLE`: Role with write/execute permissions on the target schemas (e.g., `ACCOUNTADMIN`).
* `SNOWFLAKE_DATABASE`: Target database name (`RAG_AI_PLATFORM`).
* `SNOWFLAKE_WAREHOUSE`: Compute warehouse name (`SNOWFLAKE_LEARNING_WH` or `COMPUTE_WH`).
* `SNOWFLAKE_SCHEMA`: Default schema name (`RAW`).

### 2. Trigger the Workflow
* **Scheduled Execution:** Triggers automatically every day at 19:15 UTC (02:15 AM ICT) via GitHub Actions cron.
* **Manual Execution:** Navigate to the **Actions** tab in GitHub, select **Daily dbt Pipeline Execution** from the left sidebar, and click **Run workflow**.