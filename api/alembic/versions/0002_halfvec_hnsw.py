"""halfvec quantization and HNSW indexes

Convert embedding columns from vector(384) to halfvec(384) for 50% storage
reduction, and add HNSW indexes for O(log n) approximate nearest neighbor
search instead of brute-force sequential scans.

Revision ID: 0002_halfvec_hnsw
Revises:
Create Date: 2026-04-03
"""

from alembic import op

# revision identifiers
revision = "0002_halfvec_hnsw"
down_revision = None
branch_labels = None
depends_on = None

# Tables that have embedding columns
_TABLES = ["code_chunks", "log_entries", "dev_profiles"]
_DIM = 384


def upgrade() -> None:
    # ── 1. Convert vector(384) → halfvec(384) ───────────────────
    for table in _TABLES:
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN embedding TYPE halfvec({_DIM}) "
            f"USING embedding::halfvec({_DIM})"
        )

    # ── 2. Create HNSW indexes ──────────────────────────────────
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
    # ── Drop HNSW indexes ────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS idx_code_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_log_entries_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_dev_profiles_embedding_hnsw")

    # ── Revert halfvec(384) → vector(384) ────────────────────────
    for table in _TABLES:
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN embedding TYPE vector({_DIM}) "
            f"USING embedding::vector({_DIM})"
        )
