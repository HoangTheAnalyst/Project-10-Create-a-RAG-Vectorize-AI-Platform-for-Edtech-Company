{{ config(
    materialized='incremental',
    schema='marts_log',
    incremental_strategy='append',
    on_schema_change='fail'
) }}

WITH stg_log AS (
    SELECT
        query_id,
        client_ip,
        user_query,
        selected_subject,
        selected_lesson,
        similarity_threshold,
        chunks_retrieved,
        top_similarity_score,
        ai_response,
        latency_seconds,
        created_at
    FROM {{ ref('stg_log') }}

    {% if is_incremental() %}
    WHERE created_at > (SELECT MAX(created_at) FROM {{ this }})
    {% endif %}
),

add_metric AS (
    SELECT
        MD5(query_id) AS query_sk,
        MD5(client_ip) AS hashed_client_ip,

        MD5(CONCAT_WS('||', selected_subject, selected_lesson)) AS lesson_sk,
        selected_subject,
        selected_lesson,

        similarity_threshold,
        chunks_retrieved,
        top_similarity_score,
        latency_seconds,

        LENGTH(user_query) AS user_query_length,
        LENGTH(ai_response) AS ai_response_length,
        top_similarity_score - similarity_threshold AS similarity_score_diff,

        IFF(chunks_retrieved = 0,TRUE,FALSE) AS no_chunks_retrieved,
        IFF(latency_seconds > 5,TRUE,FALSE) AS high_latency,
        created_at
    FROM stg_log
        
)

SELECT * FROM add_metric

