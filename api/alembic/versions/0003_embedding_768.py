"""Upgrade embedding columns from halfvec(384) to halfvec(768)

Switching from all-MiniLM-L6-v2 (384-dim) to
jinaai/jina-embeddings-v2-base-code (768-dim).

IMPORTANT: All existing embeddings are incompatible with the new model.
After running this migration, re-ingest all repositories and logs.

Revision ID: 0003_embedding_768
Revises: 0002_halfvec_hnsw
Create Date: 2026-04-03
"""

from alembic import op

revision = "0003_embedding_768"
down_revision = "0002_halfvec_hnsw"
branch_labels = None
depends_on = None

_TABLES = ["code_chunks", "log_entries", "dev_profiles"]
_OLD_DIM = 384
_NEW_DIM = 768


def upgrade() -> None:
    # ── 1. Drop old HNSW indexes (dimension-specific, must be rebuilt) ──
    op.execute("DROP INDEX IF EXISTS idx_code_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_log_entries_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_dev_profiles_embedding_hnsw")

    # ── 2. Clear existing embeddings — they're incompatible with new model ──
    # Nulling them out rather than deleting rows so code_chunks/commits remain.
    # Re-ingest to populate new embeddings.
    for table in _TABLES:
        op.execute(f"UPDATE {table} SET embedding = NULL")

    # ── 3. Resize halfvec columns to new dimension ───────────────────────
    for table in _TABLES:
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN embedding TYPE halfvec({_NEW_DIM}) "
            f"USING NULL::halfvec({_NEW_DIM})"
        )

    # ── 4. Rebuild HNSW indexes at new dimension ─────────────────────────
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_code_chunks_embedding_hnsw "
        "ON code_chunks "
        "USING hnsw (embedding halfvec_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_log_entries_embedding_hnsw "
        "ON log_entries "
        "USING hnsw (embedding halfvec_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_dev_profiles_embedding_hnsw "
        "ON dev_profiles "
        "USING hnsw (embedding halfvec_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_code_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_log_entries_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_dev_profiles_embedding_hnsw")

    for table in _TABLES:
        op.execute(f"UPDATE {table} SET embedding = NULL")

    for table in _TABLES:
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN embedding TYPE halfvec({_OLD_DIM}) "
            f"USING NULL::halfvec({_OLD_DIM})"
        )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_code_chunks_embedding_hnsw "
        "ON code_chunks USING hnsw (embedding halfvec_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_log_entries_embedding_hnsw "
        "ON log_entries USING hnsw (embedding halfvec_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_dev_profiles_embedding_hnsw "
        "ON dev_profiles USING hnsw (embedding halfvec_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
