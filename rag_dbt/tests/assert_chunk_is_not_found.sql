{{config(
    warn_if='>= 10'
) }}

SELECT
    query_id,
    session_id,
    conversation_id,
    conversation_name,
    client_ip,
    user_query,
    ai_response,
    created_at
FROM {{ source('raw_log_source', 'query_logs') }}
WHERE chunks_retrieved = 0