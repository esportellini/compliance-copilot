"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role = postgresql.ENUM(
    "ADMIN", "COMPLIANCE", "EMPLOYEE", "AUDITOR", name="user_role", create_type=False
)
decision = postgresql.ENUM(
    "ALLOWED",
    "REPORT_REQUIRED",
    "PRE_APPROVAL_REQUIRED",
    "RESTRICTED",
    "INCONCLUSIVE",
    name="decision",
    create_type=False,
)
risk_level = postgresql.ENUM("LOW", "MEDIUM", "HIGH", name="risk_level", create_type=False)
product_status = postgresql.ENUM(
    "ALLOWED", "MONITORED", "RESTRICTED", "BLOCKED", name="product_status", create_type=False
)
document_status = postgresql.ENUM(
    "DRAFT", "ACTIVE", "ARCHIVED", name="document_status", create_type=False
)
pre_approval_status = postgresql.ENUM(
    "PENDING",
    "IN_REVIEW",
    "APPROVED",
    "REJECTED",
    "APPROVED_WITH_CONDITIONS",
    "CANCELLED",
    name="pre_approval_status",
    create_type=False,
)

ALL_ENUMS = (
    user_role,
    decision,
    risk_level,
    product_status,
    document_status,
    pre_approval_status,
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in ALL_ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("department", sa.String(120)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "policy_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reference_code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("version", sa.String(32), server_default="1.0", nullable=False),
        sa.Column("status", document_status, server_default="DRAFT", nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("effective_date", sa.Date()),
        sa.Column("storage_path", sa.String(512)),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        *_timestamps(),
        sa.UniqueConstraint("reference_code", name="uq_policy_reference_code"),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section_title", sa.String(255)),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer()),
        *_timestamps(),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunk_position"),
    )

    op.create_table(
        "financial_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("asset_class", sa.String(64), nullable=False),
        sa.Column("issuer", sa.String(255)),
        sa.Column("isin", sa.String(12)),
        sa.Column("currency", sa.String(3), server_default="BRL", nullable=False),
        sa.Column("status", product_status, server_default="ALLOWED", nullable=False),
        sa.Column("risk_level", risk_level, server_default="MEDIUM", nullable=False),
        sa.Column("notes", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint("symbol", name="uq_product_symbol"),
        sa.UniqueConstraint("isin", name="uq_product_isin"),
    )
    op.create_index("ix_products_symbol", "financial_products", ["symbol"])

    op.create_table(
        "compliance_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("decision", decision, nullable=False),
        sa.Column("risk_level", risk_level, server_default="MEDIUM", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("conditions", postgresql.JSONB()),
        sa.Column("source_document_id", sa.Integer(), sa.ForeignKey("policy_documents.id", ondelete="SET NULL")),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_rule_code"),
    )

    op.create_table(
        "copilot_queries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("financial_products.id", ondelete="SET NULL")),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("context", postgresql.JSONB()),
        *_timestamps(),
    )
    op.create_index("ix_copilot_queries_user_id", "copilot_queries", ["user_id"])

    op.create_table(
        "copilot_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_id", sa.Integer(), sa.ForeignKey("copilot_queries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", decision, nullable=False),
        sa.Column("risk_level", risk_level),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("matched_rule_id", sa.Integer(), sa.ForeignKey("compliance_rules.id", ondelete="SET NULL")),
        sa.Column("model_name", sa.String(120)),
        sa.Column("latency_ms", sa.Integer()),
        *_timestamps(),
        sa.UniqueConstraint("query_id", name="uq_answer_query"),
    )

    op.create_table(
        "source_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("answer_id", sa.Integer(), sa.ForeignKey("copilot_answers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("policy_documents.id", ondelete="SET NULL")),
        sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id", ondelete="SET NULL")),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("compliance_rules.id", ondelete="SET NULL")),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("excerpt", sa.Text()),
        sa.Column("relevance_score", sa.Float()),
        *_timestamps(),
    )

    op.create_table(
        "pre_approval_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("financial_products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", pre_approval_status, server_default="PENDING", nullable=False),
        sa.Column("side", sa.String(8)),
        sa.Column("quantity", sa.Numeric(18, 4)),
        sa.Column("estimated_amount", sa.Numeric(18, 2)),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("decision_notes", sa.Text()),
        sa.Column("risk_level", risk_level),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_pre_approval_status", "pre_approval_requests", ["status"])

    op.create_table(
        "pre_approval_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("pre_approval_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("body", sa.Text(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(80)),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("risk_level", risk_level),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("payload", postgresql.JSONB()),
        *_timestamps(),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("value", postgresql.JSONB()),
        sa.Column("description", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint("key", name="uq_setting_key"),
    )

    op.create_table(
        "training_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(120)),
        sa.Column("required_roles", postgresql.ARRAY(user_role)),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("due_in_days", sa.Integer()),
        sa.Column("content_url", sa.String(512)),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_training_code"),
    )

    op.create_table(
        "user_training_acknowledgements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("training_item_id", sa.Integer(), sa.ForeignKey("training_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("score", sa.Float()),
        *_timestamps(),
        sa.UniqueConstraint("user_id", "training_item_id", name="uq_user_training"),
    )

    op.create_table(
        "restricted_list_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("financial_products.id", ondelete="CASCADE")),
        sa.Column("symbol", sa.String(32)),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("restricted_from", sa.Date(), nullable=False),
        sa.Column("restricted_until", sa.Date()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("added_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        *_timestamps(),
    )
    op.create_index("ix_restricted_symbol", "restricted_list_items", ["symbol"])


def downgrade() -> None:
    op.drop_table("restricted_list_items")
    op.drop_table("user_training_acknowledgements")
    op.drop_table("training_items")
    op.drop_table("system_settings")
    op.drop_table("audit_logs")
    op.drop_table("pre_approval_comments")
    op.drop_table("pre_approval_requests")
    op.drop_table("source_references")
    op.drop_table("copilot_answers")
    op.drop_table("copilot_queries")
    op.drop_table("compliance_rules")
    op.drop_table("financial_products")
    op.drop_table("document_chunks")
    op.drop_table("policy_documents")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_type in reversed(ALL_ENUMS):
        enum_type.drop(bind, checkfirst=True)
