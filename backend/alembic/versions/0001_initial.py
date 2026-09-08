"""Initial schema matching the current SQLAlchemy models.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-11

This project has not published a migration chain and has no real user database
that depends on the previous draft schema. Replacing the initial migration is
therefore safe here. Rewriting an initial migration is not appropriate for a
released system; published schemas require forward-only compatibility
migrations instead.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("department", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_anonymized", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "financial_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("product_type", sa.String(48), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=True),
        sa.Column("issuer", sa.String(255), nullable=True),
        sa.Column("manager", sa.String(255), nullable=True),
        sa.Column("administrator", sa.String(255), nullable=True),
        sa.Column("risk", sa.String(16), nullable=True),
        sa.Column("liquidity", sa.String(64), nullable=True),
        sa.Column("target_audience", sa.String(120), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_financial_products_name", "financial_products", ["name"])
    op.create_index("ix_financial_products_product_type", "financial_products", ["product_type"])
    op.create_index("ix_financial_products_status", "financial_products", ["status"])
    op.create_index(
        "uq_financial_products_identifier_normalized",
        "financial_products",
        [sa.text("upper(trim(identifier))")],
        unique=True,
    )

    op.create_table(
        "policy_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_policy_documents_name", "policy_documents", ["name"])
    op.create_index("ix_policy_documents_doc_type", "policy_documents", ["doc_type"])
    op.create_index("ix_policy_documents_status", "policy_documents", ["status"])

    op.create_table(
        "compliance_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("product_type", sa.String(48), nullable=True),
        sa.Column("condition", postgresql.JSONB(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("risk", sa.String(16), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_compliance_rules_name", "compliance_rules", ["name"])
    op.create_index("ix_compliance_rules_product_type", "compliance_rules", ["product_type"])
    op.create_index("ix_compliance_rules_is_active", "compliance_rules", ["is_active"])

    op.create_table(
        "restricted_list_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_restricted_list_items_identifier", "restricted_list_items", ["identifier"])
    op.create_index("ix_restricted_list_items_active", "restricted_list_items", ["active"])
    op.create_index(
        "uq_restricted_list_identifier_normalized",
        "restricted_list_items",
        [sa.text("upper(trim(identifier))")],
        unique=True,
    )

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_system_settings_key", "system_settings", ["key"], unique=True)

    op.create_table(
        "training_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_label", sa.String(255), nullable=True),
        sa.Column("entity", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_severity", "audit_logs", ["severity"])

    op.create_table(
        "copilot_queries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("product_type", sa.String(48), nullable=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("financial_products.id"), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_copilot_queries_user_id", "copilot_queries", ["user_id"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_title", sa.String(255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    op.create_table(
        "pre_approval_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_query_id", sa.Integer(), sa.ForeignKey("copilot_queries.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("financial_products.id"), nullable=True),
        sa.Column("product_label", sa.String(255), nullable=True),
        sa.Column("operation_type", sa.String(48), nullable=False),
        sa.Column("estimated_amount", sa.Float(), nullable=True),
        sa.Column("intended_date", sa.Date(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("copilot_initial_response", sa.Text(), nullable=True),
        sa.Column("copilot_initial_decision", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("compliance_opinion", sa.Text(), nullable=True),
        sa.Column("reviewer", sa.String(255), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_started_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_pre_approval_requests_requester_id", "pre_approval_requests", ["requester_id"])
    op.create_index("ix_pre_approval_requests_source_query_id", "pre_approval_requests", ["source_query_id"])
    op.create_index("ix_pre_approval_requests_status", "pre_approval_requests", ["status"])

    op.create_table(
        "user_training_acknowledgements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("training_item_id", sa.Integer(), sa.ForeignKey("training_items.id"), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_user_training_acknowledgements_user_id", "user_training_acknowledgements", ["user_id"])
    op.create_index("ix_user_training_acknowledgements_training_item_id", "user_training_acknowledgements", ["training_item_id"])

    op.create_table(
        "copilot_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_id", sa.Integer(), sa.ForeignKey("copilot_queries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("matched_rules", postgresql.JSONB(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_copilot_answers_query_id", "copilot_answers", ["query_id"])
    op.create_index("ix_copilot_answers_decision", "copilot_answers", ["decision"])

    op.create_table(
        "pre_approval_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("pre_approval_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("author_name", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_pre_approval_comments_request_id", "pre_approval_comments", ["request_id"])

    op.create_table(
        "source_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("answer_id", sa.Integer(), sa.ForeignKey("copilot_answers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("policy_documents.id"), nullable=True),
        sa.Column("chunk_id", sa.Integer(), nullable=True),
        sa.Column("document_name", sa.String(255), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_title", sa.String(255), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_source_references_answer_id", "source_references", ["answer_id"])


def downgrade() -> None:
    op.drop_table("source_references")
    op.drop_table("pre_approval_comments")
    op.drop_table("copilot_answers")
    op.drop_table("user_training_acknowledgements")
    op.drop_table("pre_approval_requests")
    op.drop_table("document_chunks")
    op.drop_table("copilot_queries")
    op.drop_table("audit_logs")
    op.drop_table("training_items")
    op.drop_table("system_settings")
    op.drop_table("restricted_list_items")
    op.drop_table("compliance_rules")
    op.drop_table("policy_documents")
    op.drop_table("financial_products")
    op.drop_table("users")
