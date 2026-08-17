{{ config(
    materialized='table',
    schema='marts_log'
) }}

/*
==================================================================================================
CONFIDENTIAL / RESTRICTED ACCESS MART: Raw Interaction Telemetry
==================================================================================================
- Purpose: Preserves genuine student queries (`user_query`) and raw AI responses (`ai_response`) 
  for deep-dive pedagogical analysis, LLM response quality evaluation, and sensitive internal audits.
- Access Governance: Highly restricted model. Unlike `fct_log`—which anonymizes identifiers via 
  MD5 hashing and completely omits raw textual interactions for general business reporting—this 
  table retains actual student conversations and must be protected under strict RBAC policies.
==================================================================================================
*/

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