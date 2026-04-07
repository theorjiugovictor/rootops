-- RootOps — Database Initialization
-- This script runs automatically when the PostgreSQL container starts
-- for the first time (via docker-entrypoint-initdb.d).

-- Enable the pgvector extension for semantic embedding storage
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable the uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── HNSW Indexes for Approximate Nearest Neighbor Search ────────
-- Uses halfvec (float16) cosine distance for 50% storage reduction.
-- HNSW gives O(log n) search vs O(n) brute-force sequential scan.
--
-- Parameters:
--   m = 16          → connections per node (higher = better recall, more RAM)
--   ef_construction = 64  → build-time quality (higher = slower build, better index)
--
-- These indexes are created IF NOT EXISTS so they're safe to re-run.
-- They will only activate once the tables are created by SQLAlchemy/Alembic.

-- Code chunks: the primary search target for RAG queries
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'code_chunks') THEN
        CREATE INDEX IF NOT EXISTS idx_code_chunks_embedding_hnsw
            ON code_chunks
            USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64);
    END IF;
END $$;

-- Log entries: cross-correlated with code during queries + auto-heal
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'log_entries') THEN
        CREATE INDEX IF NOT EXISTS idx_log_entries_embedding_hnsw
            ON log_entries
            USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64);
    END IF;
END $$;

-- Dev profiles: style fingerprint similarity (smaller table, still benefits)
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'dev_profiles') THEN
        CREATE INDEX IF NOT EXISTS idx_dev_profiles_embedding_hnsw
            ON dev_profiles
            USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64);
    END IF;
END $$;
