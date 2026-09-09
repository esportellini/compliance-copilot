from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import Decision, RiskLevel


class CopilotQueryRequest(BaseModel):
    question: str = Field(min_length=3)
    product_type: str | None = None
    product_id: int | None = None
    product_name_hint: str | None = None
    amount: float | None = Field(default=None, ge=0)
    objective: str | None = None


class SourceOut(BaseModel):
    document_id: int | None = None
    chunk_id: int | None = None
    document_name: str
    excerpt: str
    score: float
    page_number: int | None = None
    section_title: str | None = None
    document_version: str | None = None

    model_config = {"from_attributes": True}


class RuleMatchReference(BaseModel):
    rule_id: int
    rule_key: str
    version: int
    name: str
    priority: int
    decision: str
    condition: dict


class CopilotAnswerOut(BaseModel):
    query_id: int | None = None
    decision: Decision
    answer: str
    justification: str
    sources: list[SourceOut] = []
    confidence: float
    risk_level: RiskLevel
    next_action: str | None = None
    requires_human_review: bool
    matched_rules: list[str] = []
    rule_provenance: list[RuleMatchReference] = []
    out_of_scope: bool = False


class CopilotHistoryItem(BaseModel):
    id: int
    question: str
    product_type: str | None = None
    amount: float | None = None
    decision: str
    risk_level: str
    confidence: float
    requires_human_review: bool
    created_at: datetime


class CopilotHistoryDetail(BaseModel):
    id: int
    question: str
    product_type: str | None
    product_id: int | None
    product_label: str | None
    product_identifier: str | None
    amount: float | None
    objective: str | None
    created_at: datetime
    answer: CopilotAnswerOut
