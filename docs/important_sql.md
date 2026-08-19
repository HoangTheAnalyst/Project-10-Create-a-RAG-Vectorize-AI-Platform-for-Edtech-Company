# 📌 Important SQL Queries - RAG & Telemetry Platform (Snowflake)

This document contains the foundational SQL statements used across the platform for data ingestion, vector retrieval, telemetry observability, and student examination services (excluding internal dbt models which reside in `rag_dbt`).

---

## 1. Document Chunk Ingestion (ETL Pipeline)

* **Purpose:** Creates the raw document chunk repository and executes batch ingestion of embedded JSON chunks with vector representations and metadata payloads[cite: 3].
* **Target Schema/Table:** `RAW.RAW_CHUNKS`[cite: 3].
* **Vector Specifications:** Raw embedding stored as `ARRAY` and parsed via `PARSE_JSON` into array format[cite: 3].

### 📝 Table Schema (DDL)
```sql
CREATE TABLE IF NOT EXISTS RAW.RAW_CHUNKS (
    chunk_id VARCHAR(255),
    file_name VARCHAR(255),
    subject VARCHAR(100),
    lesson_name VARCHAR(255),
    content_type VARCHAR(50),
    section_title VARCHAR(255),
    chunk_type VARCHAR(50),
    content VARCHAR,
    chunk_vector ARRAY,
    raw_metadata VARIANT,
    ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

### 📝 Parameterized Batch Insert Query
```sql
INSERT INTO RAW.RAW_CHUNKS (
    chunk_id,
    file_name,
    subject,
    lesson_name,
    content_type,
    section_title,
    chunk_type,
    content,
    chunk_vector,
    raw_metadata
)
SELECT 
    column1, 
    column2, 
    column3, 
    column4, 
    column5, 
    column6, 
    column7, 
    column8, 
    PARSE_JSON(column9), 
    PARSE_JSON(column10)
FROM VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
```

---

## 2. Vector Cosine Similarity Search with Metadata Filtering

* **Purpose:** Performs semantic cosine similarity search using Snowflake's native vector engine, joined with dimension tables for subject and lesson pre-filtering.
* **Source Tables:** `MARTS.FCT_CHUNKS` (Facts) + `MARTS.DIM_LESSON` (Dimensions).
* **Technical Specifications:**
  * Dimension: `1024` floats.
  * Function: `VECTOR_COSINE_SIMILARITY(f.chunk_vector::VECTOR(FLOAT, 1024), PARSE_JSON(%s)::VECTOR(FLOAT, 1024))`.
  * Cutoff: Returns chunks matching `similarity_score >= min_similarity`, ordered descending, limited to Top 8.

### 📝 Parameterized Query (Application Layer)
```sql
WITH scored_chunks AS (
    SELECT 
        f.subject,
        d.lesson_name,
        f.section_title,
        f.content,
        f.chunk_type,
        VECTOR_COSINE_SIMILARITY(
            f.chunk_vector::VECTOR(FLOAT, 1024),
            PARSE_JSON(%s)::VECTOR(FLOAT, 1024)
        ) AS similarity_score
    FROM MARTS.FCT_CHUNKS f
    JOIN MARTS.DIM_LESSON d 
      ON f.lesson_sk = d.lesson_sk
    WHERE 1=1
      -- Dynamic metadata pre-filters:
      -- AND f.subject = %s
      -- AND d.lesson_name = %s
)
SELECT 
    subject, 
    lesson_name, 
    section_title, 
    content, 
    chunk_type, 
    similarity_score
FROM scored_chunks
WHERE similarity_score >= %s
ORDER BY similarity_score DESC
LIMIT 8;
```

---

## 3. Query Interaction Telemetry Log Ingestion

* **Purpose:** Ingests execution metadata per user interaction turn (session ID, query text, top similarity score, latency, and response) for real-time observability.
* **Target Table:** `RAW.QUERY_LOGS` (Bronze layer upstream for dbt telemetry pipeline).

### 📝 Parameterized Insert Query
```sql
INSERT INTO RAW.QUERY_LOGS (
    session_id, 
    conversation_id, 
    conversation_name, 
    client_ip, 
    user_query, 
    selected_subject, 
    selected_lesson, 
    similarity_threshold, 
    chunks_retrieved, 
    top_similarity_score, 
    ai_response, 
    latency_seconds
) 
VALUES (
    %s,  -- session_id (VARCHAR/TEXT)
    %s,  -- conversation_id (VARCHAR/TEXT)
    %s,  -- conversation_name (VARCHAR/TEXT)
    %s,  -- client_ip (VARCHAR)
    %s,  -- user_query (TEXT)
    %s,  -- selected_subject (VARCHAR)
    %s,  -- selected_lesson (VARCHAR)
    %s,  -- similarity_threshold (FLOAT)
    %s,  -- chunks_retrieved (INTEGER)
    %s,  -- top_similarity_score (FLOAT)
    %s,  -- ai_response (TEXT)
    %s   -- latency_seconds (FLOAT)
);
```

---

## 4. Analytical Telemetry Extraction for Dashboard

* **Purpose:** Extracts audit logs, latency flags, and cosine match differences from the dbt Gold Mart to compute real-time KPI metrics and time-series charts[cite: 1].
* **Source Table:** `MARTS_LOG.FCT_LOG`[cite: 1].

### 📝 Analytical Extraction Query
```sql
SELECT 
    query_sk, 
    hashed_client_ip, 
    session_sk, 
    conversation_sk, 
    lesson_sk,
    selected_subject, 
    selected_lesson, 
    similarity_threshold, 
    chunks_retrieved, 
    top_similarity_score, 
    latency_seconds, 
    user_query_length, 
    ai_response_length, 
    similarity_score_diff, 
    no_chunks_retrieved, 
    high_latency, 
    created_at, 
    DATE_TRUNC('day', created_at) AS log_date
FROM MARTS_LOG.FCT_LOG
ORDER BY created_at DESC;
```

---

## 5. Randomized Question & Answer Retrieval for Examination Room

* **Purpose:** Retrieves multiple-choice question chunks and performs an exact section-level self-join to attach the corresponding explanation/answer chunk[cite: 2].
* **Source Tables:** `MARTS.FCT_CHUNKS` (Question chunks `q`) self-joined with `MARTS.FCT_CHUNKS` (Answer chunks `a`) via `lesson_sk` and `section_title`[cite: 2].

### 📝 Parameterized Query
```sql
SELECT 
    q.section_title, 
    q.content AS question_content, 
    COALESCE(a.content, 'No detailed explanation available.') AS answer_content
FROM MARTS.FCT_CHUNKS q
JOIN MARTS.DIM_LESSON d 
  ON q.lesson_sk = d.lesson_sk
LEFT JOIN MARTS.FCT_CHUNKS a 
  ON q.lesson_sk = a.lesson_sk 
 AND q.section_title = a.section_title
 AND LOWER(a.chunk_type) IN ('answer', 'answers')
WHERE q.subject = %s 
  AND d.lesson_name = %s
  AND LOWER(q.chunk_type) IN ('question', 'questions')
ORDER BY RANDOM()
LIMIT %s;
```

---

## 6. Metadata Hierarchy Filter Extraction

* **Purpose:** Populates dropdown filter selectors on the UI by pulling unique subject-lesson parent-child relationships.
* **Source Table:** `MARTS.DIM_LESSON`.

### 📝 Filter Query
```sql
SELECT DISTINCT 
    subject, 
    lesson_name 
FROM MARTS.DIM_LESSON 
ORDER BY subject, lesson_name;
```