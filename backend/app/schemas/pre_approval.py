from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.enums import PreApprovalStatus


class PreApprovalCreate(BaseModel):
    product_id: int | None = None
    product_label: str | None = None
    operation_type: str
    estimated_amount: float | None = None
    intended_date: date | None = None
    justification: str | None = None


class PreApprovalStatusUpdate(BaseModel):
    status: PreApprovalStatus
    compliance_opinion: str | None = None


class CommentCreate(BaseModel):
    body: str


class CommentOut(BaseModel):
    id: int
    author_name: str
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PreApprovalOut(BaseModel):
    id: int
    requester_id: int
    product_id: int | None
    product_label: str | None
    operation_type: str
    estimated_amount: float | None
    intended_date: date | None
    justification: str | None
    copilot_initial_response: str | None
    status: PreApprovalStatus
    compliance_opinion: str | None
    reviewer: str | None
    decided_at: datetime | None
    created_at: datetime
    comments: list[CommentOut] = []

    model_config = {"from_attributes": True}
