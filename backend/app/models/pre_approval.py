from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PreApprovalRequest(Base, TimestampMixin):
    __tablename__ = "pre_approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_query_id: Mapped[int | None] = mapped_column(
        ForeignKey("copilot_queries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("financial_products.id"), nullable=True
    )
    product_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operation_type: Mapped[str] = mapped_column(String(48))
    estimated_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    intended_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    copilot_initial_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    copilot_initial_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    compliance_opinion: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    requester = relationship("User", back_populates="pre_approvals")
    source_query = relationship("CopilotQuery")
    comments = relationship(
        "PreApprovalComment", back_populates="request", cascade="all, delete-orphan"
    )

    @property
    def sla_status(self) -> str:
        if self.status not in {"PENDING", "IN_REVIEW"}:
            return "COMPLETED"
        if self.due_at is None:
            return "ON_TIME"
        due = self.due_at if self.due_at.tzinfo else self.due_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if due <= now:
            return "OVERDUE"
        return "DUE_SOON" if (due - now) <= timedelta(hours=12) else "ON_TIME"


class PreApprovalComment(Base, TimestampMixin):
    __tablename__ = "pre_approval_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("pre_approval_requests.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author_name: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)

    request = relationship("PreApprovalRequest", back_populates="comments")
