{{config(
    warn_if='>= 1'
) }}

SELECT
    session_id,
    conversation_id,
    client_ip,
    user_query,
    ai_response,
    created_at
FROM  {{ source('raw_log_source', 'query_logs') }}
WHERE 
    (ai_response ILIKE '%Xin lỗi, thầy không thể trả lời câu hỏi này.%'
    OR user_query ILIKE '%Xin lỗi, thầy không thể trả lời câu hỏi này.%')
    AND created_at >= DATEADD(day, -3, CURRENT_TIMESTAMP())