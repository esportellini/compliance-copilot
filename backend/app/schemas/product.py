from datetime import datetime

from pydantic import BaseModel

from app.schemas.enums import ProductStatus


# tipos aceitos pelo frontend — o motor de regras usa subconjunto destes
PRODUCT_TYPES = [
    "STOCK",
    "FII",
    "ETF",
    "OPEN_FUND",
    "CLOSED_FUND",
    "FIDC",
    "FIXED_INCOME",
    "COE",
    "DERIVATIVE",
    "CRYPTO",
    "IPO",
    "OTHER",
]

PRODUCT_TYPE_LABELS: dict[str, str] = {
    "STOCK": "Ação",
    "FII": "FII",
    "ETF": "ETF",
    "OPEN_FUND": "Fundo aberto",
    "CLOSED_FUND": "Fundo fechado",
    "FIDC": "FIDC",
    "FIXED_INCOME": "Renda fixa",
    "COE": "COE",
    "DERIVATIVE": "Derivativo",
    "CRYPTO": "Criptoativo",
    "IPO": "IPO / Oferta pública",
    "OTHER": "Outro",
}


class ProductBase(BaseModel):
    name: str
    product_type: str
    identifier: str | None = None
    issuer: str | None = None
    manager: str | None = None
    administrator: str | None = None
    risk: str | None = None
    liquidity: str | None = None
    target_audience: str | None = None
    status: ProductStatus = ProductStatus.ALLOWED
    notes: str | None = None
    tags: list[str] = []


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    product_type: str | None = None
    identifier: str | None = None
    issuer: str | None = None
    manager: str | None = None
    administrator: str | None = None
    risk: str | None = None
    liquidity: str | None = None
    target_audience: str | None = None
    status: ProductStatus | None = None
    notes: str | None = None
    tags: list[str] | None = None


class ProductOut(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
