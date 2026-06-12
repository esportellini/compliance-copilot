from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str  # str simples — validação de formato não é necessária no login
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    department: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = "EMPLOYEE"
    department: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    department: str | None = None
    is_active: bool | None = None
