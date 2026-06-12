from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    event_type: str
    user_id: int | None
    actor_label: str | None
    entity: str | None
    entity_id: int | None
    severity: str
    message: str
    meta: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingItemOut(BaseModel):
    id: int
    title: str
    body: str
    category: str | None
    order_index: int
    required: bool
    acknowledged: bool = False

    model_config = {"from_attributes": True}


class TrainingAcknowledge(BaseModel):
    training_item_id: int


class SettingOut(BaseModel):
    key: str
    value: str
    description: str | None

    model_config = {"from_attributes": True}
