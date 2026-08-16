{{ config(
    materialized='table',
    schema='marts_log'
) }}

SELECT
    MD5(query_id) AS query_sk,
    session_id,
    user_query,
    conversation_id,
    conversation_name,
    selected_subject,
    selected_lesson,
    ai_response,
    created_at
FROM {{ ref('stg_log') }}