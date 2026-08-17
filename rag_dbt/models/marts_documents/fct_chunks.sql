{{ config(
    materialized='incremental',
    schema='marts',
    incremental_strategy='merge',
    unique_key='chunk_sk',
    on_schema_change='sync_all_columns'
) }}

-- Incrementally ingest document chunks and vectors, generating surrogate keys (chunk_sk, lesson_sk)
WITH stg_chunks AS (
    SELECT
        chunk_id,
        subject,
        lesson_name,
        content_type,
        section_title,
        chunk_type,
        content,
        chunk_vector,
        ingested_at
    FROM {{ ref('stg_chunks') }}
    
    {% if is_incremental() %}
        WHERE ingested_at > (SELECT MAX(ingested_at) FROM {{ this }})
    {% endif %}
),

created_sk AS (
    SELECT
        MD5(chunk_id) AS chunk_sk,
        content_type,
        subject,
        MD5(CONCAT_WS('||', subject, lesson_name)) AS lesson_sk,
        section_title,
        content,
        chunk_vector,
        chunk_type,
        ingested_at
    FROM stg_chunks
)

SELECT
    chunk_sk,
    content_type,
    subject,
    lesson_sk,
    section_title,
    chunk_type,
    content,
    chunk_vector,
    ingested_at
FROM created_sk