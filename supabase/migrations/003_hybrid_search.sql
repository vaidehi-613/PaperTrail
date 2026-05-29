-- Run in Supabase SQL Editor after 001_init.sql and 002_match_chunks.sql.

-- 1. Generated tsvector column — auto-updated whenever content changes
ALTER TABLE chunks
    ADD COLUMN IF NOT EXISTS content_tsv TSVECTOR
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

-- 2. GIN index for fast full-text lookup
CREATE INDEX IF NOT EXISTS chunks_fts_idx
    ON chunks USING GIN (content_tsv);

-- 3. Hybrid RPC: vector ANN + BM25 fused with Reciprocal Rank Fusion
CREATE OR REPLACE FUNCTION match_chunks_hybrid(
    query_embedding  VECTOR(1536),
    query_text       TEXT,
    filter_paper_id  UUID,
    match_count      INT DEFAULT 5,
    rrf_k            INT DEFAULT 60
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
WITH vector_ranked AS (
    SELECT id,
           ROW_NUMBER() OVER (ORDER BY embedding <=> query_embedding) AS rank
    FROM   chunks
    WHERE  paper_id = filter_paper_id
    ORDER  BY embedding <=> query_embedding
    LIMIT  match_count * 4
),
bm25_ranked AS (
    SELECT id,
           ROW_NUMBER() OVER (
               ORDER BY ts_rank_cd(content_tsv,
                        plainto_tsquery('english', query_text)) DESC
           ) AS rank
    FROM   chunks
    WHERE  paper_id = filter_paper_id
      AND  content_tsv @@ plainto_tsquery('english', query_text)
    LIMIT  match_count * 4
),
rrf AS (
    SELECT COALESCE(v.id, b.id)                              AS id,
           COALESCE(1.0 / (rrf_k + v.rank), 0.0)
           + COALESCE(1.0 / (rrf_k + b.rank), 0.0)          AS score
    FROM   vector_ranked v
    FULL OUTER JOIN bm25_ranked b ON v.id = b.id
)
SELECT c.id, c.content, c.section, c.page,
       c.is_table, c.is_figure, r.score
FROM   rrf r
JOIN   chunks c ON c.id = r.id
ORDER  BY r.score DESC
LIMIT  match_count;
$$;
