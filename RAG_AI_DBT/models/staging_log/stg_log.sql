{{ config(
    materialized='view',
    schema='staging_log'
) }}

WITH source_data AS (
    SELECT * 
    FROM {{ source('raw_log_source', 'query_logs') }}
),

renamed AS (
    SELECT
        CAST(query_id AS VARCHAR) AS query_id,
        CAST(session_id AS VARCHAR) AS session_id,
        CAST(conversation_id AS VARCHAR) AS conversation_id,
        CAST(conversation_name AS VARCHAR) AS conversation_name,
        CAST(client_ip AS VARCHAR) AS client_ip,
        CAST(user_query AS VARCHAR) AS user_query,
        CAST(selected_subject AS VARCHAR) AS selected_subject,
        CAST(selected_lesson AS VARCHAR) AS selected_lesson,
        CAST(similarity_threshold AS FLOAT) AS similarity_threshold,
        CAST(chunks_retrieved AS INT) AS chunks_retrieved,
        CAST(top_similarity_score AS FLOAT) AS top_similarity_score,
        CAST(ai_response AS VARCHAR) AS ai_response,
        CAST(latency_seconds AS FLOAT) AS latency_seconds,
        CAST(created_at AS TIMESTAMP_NTZ) AS created_at
    FROM source_data
)

SELECT * FROM renamed