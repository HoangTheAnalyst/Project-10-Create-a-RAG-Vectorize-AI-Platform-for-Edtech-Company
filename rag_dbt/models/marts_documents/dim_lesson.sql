{{ config(
    materialized='table',
    schema='marts'
) }}

--Create dimension table for lessons, deduplicating to the latest ingestion date and generating surrogate key (lesson_sk)
WITH raw_lesson AS (
    SELECT
        ROW_NUMBER() OVER (
            PARTITION BY lesson_name
            ORDER BY ingested_at DESC
        ) as rn,
        MD5(CONCAT_WS('||', subject, lesson_name)) AS lesson_sk,
        subject,
        lesson_name
    FROM {{ ref('stg_chunks') }}
)

SELECT
    lesson_sk,
    subject,
    lesson_name
FROM raw_lesson
WHERE rn = 1