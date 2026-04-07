"""Multi-repo schema: repositories + service_dependencies tables,
repo_id FK on code_chunks, commits, log_entries, ingestion_state,
codebase_summary.

Existing rows are migrated to a default "legacy" repository so no
data is lost. Re-ingest repos after this migration to populate repo_id
on all new chunks/commits.

Revision ID: 0004_multi_repo
Revises: 0003_embedding_768
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "0004_multi_repo"
down_revision = "0003_embedding_768"
branch_labels = None
depends_on = None

# Fixed UUID for the legacy single-repo migration placeholder
_LEGACY_REPO_ID = "00000000-0000-0000-0000-000000000010"


def upgrade() -> None:
    # ── 1. Create repositories table ────────────────────────────────
    op.create_table(
        "repositories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("local_path", sa.String(1024), nullable=True),
        sa.Column("team", sa.String(255), nullable=True),
        sa.Column("tags", JSON, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("commit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_repositories_name", "repositories", ["name"])
    op.create_index("ix_repositories_team", "repositories", ["team"])

    # ── 2. Insert legacy placeholder so existing rows can FK to it ──
    op.execute(f"""
        INSERT INTO repositories (id, name, description, created_at)
        VALUES (
            '{_LEGACY_REPO_ID}',
            'legacy',
            'Auto-created placeholder for data ingested before multi-repo support.',
            now()
        )
    """)

    # ── 3. Add repo_id columns (nullable — existing rows get legacy ID) ─
    for table in ("code_chunks", "commits", "log_entries"):
        op.add_column(table, sa.Column("repo_id", UUID(as_uuid=True), nullable=True))
        op.create_index(f"ix_{table}_repo_id", table, ["repo_id"])
        op.execute(f"UPDATE {table} SET repo_id = '{_LEGACY_REPO_ID}'")
        op.create_foreign_key(
            f"fk_{table}_repo_id", table,
            "repositories", ["repo_id"], ["id"],
            ondelete="CASCADE",
        )

    # ── 4. Migrate ingestion_state ────────────────────────────────────
    # Old schema: single row with id PK (singleton UUID)
    # New schema: repo_id PK (FK to repositories)
    op.add_column("ingestion_state", sa.Column("repo_id", UUID(as_uuid=True), nullable=True))
    op.execute(f"UPDATE ingestion_state SET repo_id = '{_LEGACY_REPO_ID}'")
    # Drop old singleton PK, replace with repo_id PK
    op.drop_constraint("ingestion_state_pkey", "ingestion_state", type_="primary")
    op.execute("ALTER TABLE ingestion_state DROP COLUMN IF EXISTS id")
    op.execute("ALTER TABLE ingestion_state ALTER COLUMN repo_id SET NOT NULL")
    op.create_primary_key("pk_ingestion_state", "ingestion_state", ["repo_id"])
    op.create_foreign_key(
        "fk_ingestion_state_repo_id", "ingestion_state",
        "repositories", ["repo_id"], ["id"],
        ondelete="CASCADE",
    )

    # ── 5. Migrate codebase_summary ───────────────────────────────────
    # Old schema: id (string PK, singleton UUID string)
    # New schema: repo_id (UUID PK, FK to repositories)
    op.add_column("codebase_summary", sa.Column("repo_id", UUID(as_uuid=True), nullable=True))
    op.execute(f"UPDATE codebase_summary SET repo_id = '{_LEGACY_REPO_ID}'")
    op.drop_constraint("codebase_summary_pkey", "codebase_summary", type_="primary")
    op.execute("ALTER TABLE codebase_summary DROP COLUMN IF EXISTS id")
    op.execute("ALTER TABLE codebase_summary ALTER COLUMN repo_id SET NOT NULL")
    op.create_primary_key("pk_codebase_summary", "codebase_summary", ["repo_id"])
    op.create_foreign_key(
        "fk_codebase_summary_repo_id", "codebase_summary",
        "repositories", ["repo_id"], ["id"],
        ondelete="CASCADE",
    )

    # ── 6. Create service_dependencies table ─────────────────────────
    op.create_table(
        "service_dependencies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_repo_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source_repo_name", sa.String(255), nullable=False),
        sa.Column("target_repo_name", sa.String(255), nullable=False),
        sa.Column("target_repo_id", UUID(as_uuid=True), nullable=True),
        sa.Column("dependency_type", sa.String(32), nullable=False),
        sa.Column("source_file", sa.String(1024), nullable=False),
        sa.Column("source_pattern", sa.Text, nullable=False),
        sa.Column("call_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_service_dep_source", "service_dependencies", ["source_repo_id"])
    op.create_index("ix_service_dep_target", "service_dependencies", ["target_repo_id"])
    op.create_unique_constraint(
        "uq_dep_source_target_type_file",
        "service_dependencies",
        ["source_repo_id", "target_repo_name", "dependency_type", "source_file"],
    )
    op.create_foreign_key(
        "fk_service_dep_source", "service_dependencies",
        "repositories", ["source_repo_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_table("service_dependencies")

    for table in ("code_chunks", "commits", "log_entries"):
        op.drop_constraint(f"fk_{table}_repo_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_repo_id", table)
        op.drop_column(table, "repo_id")

    # Restore ingestion_state to singleton pattern
    op.drop_constraint("fk_ingestion_state_repo_id", "ingestion_state", type_="foreignkey")
    op.drop_constraint("pk_ingestion_state", "ingestion_state", type_="primary")
    op.add_column(
        "ingestion_state",
        sa.Column("id", UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("'00000000-0000-0000-0000-000000000001'::uuid")),
    )
    op.create_primary_key("ingestion_state_pkey", "ingestion_state", ["id"])
    op.drop_column("ingestion_state", "repo_id")

    # Restore codebase_summary
    op.drop_constraint("fk_codebase_summary_repo_id", "codebase_summary", type_="foreignkey")
    op.drop_constraint("pk_codebase_summary", "codebase_summary", type_="primary")
    op.add_column(
        "codebase_summary",
        sa.Column("id", sa.String(36), nullable=False,
                  server_default="'00000000-0000-0000-0000-000000000002'"),
    )
    op.create_primary_key("codebase_summary_pkey", "codebase_summary", ["id"])
    op.drop_column("codebase_summary", "repo_id")

    op.drop_table("repositories")
