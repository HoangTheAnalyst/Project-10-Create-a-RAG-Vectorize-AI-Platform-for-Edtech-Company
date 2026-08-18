
SELECT
    chunk_id,
    chunk_vector,
    ARRAY_SIZE(chunk_vector) AS actual_dimensions
FROM {{source('raw_source', 'raw_chunks') }}
WHERE 
    chunk_vector IS NULL
    OR NOT IS_ARRAY(chunk_vector)
    OR ARRAY_SIZE(chunk_vector) != 384