{{config(
    materialized='view',
    schema='staging'
)}}

WITH raw_chunk AS (
    SELECT
        chunk_id,
        file_name,
        subject,
        lesson_name,
        content_type,
        section_title,
        content,
        raw_metadata,
        chunk_vector,
        ingested_at
    FROM {{ source('raw_source', 'raw_chunks') }}
),

clean_raw_chunk AS (
    SELECT
        TRIM(chunk_id) AS chunk_id,
        TRIM(subject) AS subject,
        TRIM(lesson_name) AS lesson_name,
        TRIM(content_type) AS content_type,
        TRIM(section_title) AS section_title,
        REGEXP_REPLACE(content, '#+\\s*', ' ') AS content,
        CAST(chunk_vector AS ARRAY) AS chunk_vector,
        CAST(ingested_at AS TIMESTAMP_NTZ) AS ingested_at
    FROM raw_chunk
    WHERE chunk_id IS NOT NULL
    AND lesson_name != section_title
    AND chunk_vector IS NOT NULL

)

SELECT * FROM clean_raw_chunk
