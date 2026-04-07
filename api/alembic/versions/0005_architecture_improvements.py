"""Architecture improvements: LogConcepts, GraphEdges, EntityRegistry,
trust-ladder fields on pending_fixes, embedding model versioning.

Revision ID: 0005_architecture_improvements
Revises: 0004_multi_repo
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision = "0005_architecture_improvements"
down_revision = "0004_multi_repo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. log_concepts table ────────────────────────────────────
    op.create_table(
        "log_concepts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("service_name", sa.String(256), nullable=False),
        sa.Column("template", sa.Text, nullable=False),
        sa.Column("drain_cluster_id", sa.String(64), nullable=True),
        sa.Column("severity", sa.String(32), nullable=True),
        sa.Column("total_occurrences", sa.Integer, nullable=False, server_default="1"),
        sa.Column("temporal_histogram", JSON, nullable=True),
        sa.Column("daily_counts", JSON, nullable=True),
        sa.Column("trend", sa.String(32), nullable=False, server_default="'unknown'"),
        sa.Column("correlations", JSON, nullable=True),
        sa.Column("embedding", sa.Text, nullable=True),   # stored as text; pgvector cast at query time
        sa.Column("embedding_model_version", sa.String(32), nullable=False, server_default="'v1'"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_log_concepts_service", "log_concepts", ["service_name"])
    op.create_index("ix_log_concepts_severity", "log_concepts", ["severity"])

    # Use pgvector halfvec for the embedding column
    op.execute("ALTER TABLE log_concepts ALTER COLUMN embedding TYPE halfvec(768) USING NULL")

    # ── 2. graph_edges table ─────────────────────────────────────
    op.create_table(
        "graph_edges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_entity", sa.String(512), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("target_entity", sa.String(512), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=False),
        sa.Column("edge_type", sa.String(64), nullable=False),
        sa.Column("promotion_level", sa.String(32), nullable=False, server_default="'observed'"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("evidence", JSON, nullable=True),
        sa.Column("incident_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.String(256), nullable=True),
    )
    op.create_index("ix_graph_edges_source", "graph_edges", ["source_entity"])
    op.create_index("ix_graph_edges_target", "graph_edges", ["target_entity"])
    op.create_index("ix_graph_edges_type", "graph_edges", ["edge_type"])
    op.create_unique_constraint(
        "uq_graph_edge_source_target_type",
        "graph_edges",
        ["source_entity", "target_entity", "edge_type"],
    )

    # ── 3. entity_registry table ─────────────────────────────────
    op.create_table(
        "entity_registry",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_name", sa.String(512), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("aliases", JSON, nullable=True),
        sa.Column("repos", JSON, nullable=True),
        sa.Column("deprecated", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("metadata_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_entity_registry_name", "entity_registry", ["canonical_name"], unique=True)
    op.create_index("ix_entity_registry_type", "entity_registry", ["entity_type"])

    # ── 4. Trust-ladder fields on pending_fixes ───────────────────
    op.add_column("pending_fixes", sa.Column("confidence_score", sa.Float, nullable=True))
    op.add_column("pending_fixes", sa.Column("blast_radius", sa.Integer, nullable=True))
    op.add_column("pending_fixes", sa.Column("blast_radius_level", sa.String(16), nullable=True))
    op.add_column("pending_fixes", sa.Column("requires_approval", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("pending_fixes", sa.Column("auto_apply_eligible", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("pending_fixes", sa.Column("rollback_plan", sa.Text, nullable=True))

    # ── 5. Embedding model versioning on code_chunks + log_entries ─
    op.add_column(
        "code_chunks",
        sa.Column("embedding_model_version", sa.String(32), nullable=False, server_default="'v1'"),
    )
    op.add_column(
        "log_entries",
        sa.Column("embedding_model_version", sa.String(32), nullable=False, server_default="'v1'"),
    )
    op.create_index("ix_code_chunks_emb_version", "code_chunks", ["embedding_model_version"])
    op.create_index("ix_log_entries_emb_version", "log_entries", ["embedding_model_version"])


def downgrade() -> None:
    op.drop_index("ix_log_entries_emb_version", "log_entries")
    op.drop_index("ix_code_chunks_emb_version", "code_chunks")
    op.drop_column("log_entries", "embedding_model_version")
    op.drop_column("code_chunks", "embedding_model_version")

    op.drop_column("pending_fixes", "rollback_plan")
    op.drop_column("pending_fixes", "auto_apply_eligible")
    op.drop_column("pending_fixes", "requires_approval")
    op.drop_column("pending_fixes", "blast_radius_level")
    op.drop_column("pending_fixes", "blast_radius")
    op.drop_column("pending_fixes", "confidence_score")

    op.drop_table("entity_registry")
    op.drop_table("graph_edges")
    op.drop_table("log_concepts")
