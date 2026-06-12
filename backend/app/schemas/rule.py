from pydantic import BaseModel

from app.schemas.enums import Decision, RiskLevel


class RuleBase(BaseModel):
    name: str
    description: str | None = None
    product_type: str | None = None
    condition: dict = {}
    decision: Decision
    risk: RiskLevel = RiskLevel.MEDIUM
    priority: int = 100
    is_active: bool = True


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    product_type: str | None = None
    condition: dict | None = None
    decision: Decision | None = None
    risk: RiskLevel | None = None
    priority: int | None = None
    is_active: bool | None = None


class RuleOut(RuleBase):
    id: int

    model_config = {"from_attributes": True}


class RuleEvaluateRequest(BaseModel):
    product_type: str | None = None
    product_id: int | None = None
    amount: float | None = None
