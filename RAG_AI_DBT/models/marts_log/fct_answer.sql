{{ config(
    materialized='table',
    schema='marts_log'
) }}

SELECT
    MD5(query_id) AS query_sk,
    user_query,
    selected_subject,
    selected_lesson,
    ai_response,
    created_at
FROM {{ ref('stg_log') }}