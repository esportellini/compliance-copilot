from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.enums import Decision, RiskLevel


class RuleCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    product_type: str | None = None
    amount_gt: float | None = None
    amount_gte: float | None = None

    @field_validator("status", "product_type", mode="before")
    @classmethod
    def validate_text_values(cls, value: Any):
        if value is not None and not isinstance(value, str):
            raise ValueError("condition value must be a string")
        return value

    @field_validator("amount_gt", "amount_gte", mode="before")
    @classmethod
    def validate_amount_values(cls, value: Any):
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError("amount condition must be numeric")
        return value


class RuleBase(BaseModel):
    name: str
    description: str | None = None
    product_type: str | None = None
    condition: RuleCondition = Field(default_factory=RuleCondition)
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
    condition: RuleCondition | None = None
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
