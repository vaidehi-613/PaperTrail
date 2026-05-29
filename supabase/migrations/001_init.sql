-- Enable pgvector (must be done in Supabase Dashboard → Extensions first)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS papers (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename   TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id    UUID    NOT NULL REFERENCES papers (id) ON DELETE CASCADE,
    content     TEXT    NOT NULL,
    embedding   VECTOR(1536),        -- text-embedding-3-small dimensions
    section     TEXT,
    page        INTEGER,
    is_table    BOOLEAN NOT NULL DEFAULT FALSE,
    is_figure   BOOLEAN NOT NULL DEFAULT FALSE,
    chunk_index INTEGER NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Approximate nearest-neighbour index; tune lists= once rows > 1 million
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
