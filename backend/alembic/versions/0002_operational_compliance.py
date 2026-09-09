"""Operational compliance: version provenance, SLA, and notifications.

Revision ID: 0002_operational_compliance
Revises: 0001_initial
Create Date: 2026-09-09

This is a forward-only migration from the public v1.0.0 schema. The published
0001 migration is intentionally left unchanged.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_operational_compliance"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("compliance_rules", sa.Column("rule_key", sa.String(120), nullable=True))
    op.add_column("compliance_rules", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("compliance_rules", sa.Column("status", sa.String(16), nullable=True))
    op.add_column("compliance_rules", sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True))
    op.add_column("compliance_rules", sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True))
    op.add_column("compliance_rules", sa.Column("created_by", sa.Integer(), nullable=True))
    op.execute("UPDATE compliance_rules SET rule_key = 'legacy-' || id, status = CASE WHEN is_active THEN 'ACTIVE' ELSE 'ARCHIVED' END, effective_from = created_at")
    op.alter_column("compliance_rules", "rule_key", nullable=False)
    op.alter_column("compliance_rules", "status", nullable=False)
    op.alter_column("compliance_rules", "effective_from", nullable=False)
    op.create_foreign_key("fk_compliance_rules_created_by", "compliance_rules", "users", ["created_by"], ["id"])
    op.create_unique_constraint("uq_rule_key_version", "compliance_rules", ["rule_key", "version"])
    op.create_index("ix_compliance_rules_rule_key", "compliance_rules", ["rule_key"])
    op.create_index("ix_compliance_rules_status", "compliance_rules", ["status"])
    op.create_index("ix_compliance_rules_effective_from", "compliance_rules", ["effective_from"])
    op.create_index(
        "uq_active_rule_key", "compliance_rules", ["rule_key"], unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.add_column("copilot_answers", sa.Column("rule_provenance", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column("source_references", sa.Column("document_version", sa.String(32), nullable=True))
    op.add_column("pre_approval_requests", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_pre_approval_requests_due_at", "pre_approval_requests", ["due_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("entity", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_index("ix_pre_approval_requests_due_at", table_name="pre_approval_requests")
    op.drop_column("pre_approval_requests", "due_at")
    op.drop_column("source_references", "document_version")
    op.drop_column("copilot_answers", "rule_provenance")
    op.drop_index("ix_compliance_rules_effective_from", table_name="compliance_rules")
    op.drop_index("uq_active_rule_key", table_name="compliance_rules")
    op.drop_index("ix_compliance_rules_status", table_name="compliance_rules")
    op.drop_index("ix_compliance_rules_rule_key", table_name="compliance_rules")
    op.drop_constraint("uq_rule_key_version", "compliance_rules", type_="unique")
    op.drop_constraint("fk_compliance_rules_created_by", "compliance_rules", type_="foreignkey")
    for column in ["created_by", "effective_to", "effective_from", "status", "version", "rule_key"]:
        op.drop_column("compliance_rules", column)
