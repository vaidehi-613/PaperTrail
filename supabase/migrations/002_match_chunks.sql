-- Vector similarity search RPC used by the retriever.
-- Run this in the Supabase SQL Editor after 001_init.sql.
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding  VECTOR(1536),
    filter_paper_id  UUID,
    match_count      INT DEFAULT 5
)
RETURNS TABLE (
    id          UUID,
    content     TEXT,
    section     TEXT,
    page        INTEGER,
    is_table    BOOLEAN,
    is_figure   BOOLEAN,
    similarity  FLOAT
)
LANGUAGE SQL STABLE AS $$
    SELECT  id,
            content,
            section,
            page,
            is_table,
            is_figure,
            1 - (embedding <=> query_embedding) AS similarity
    FROM    chunks
    WHERE   chunks.paper_id = filter_paper_id
    ORDER   BY embedding <=> query_embedding
    LIMIT   match_count;
$$;
