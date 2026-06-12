from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.permissions import Role
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.audit import log_event

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user = (
        db.query(User)
        .filter(User.email == payload["sub"], User.is_active == True)  # noqa: E712
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return user


def require_roles(*roles: Role):
    def checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if Role(current_user.role) not in roles:
            log_event(
                db, "UNAUTHORIZED_ACCESS",
                f"Acesso negado: {current_user.email} (role={current_user.role})",
                user_id=current_user.id, actor_label=current_user.email,
                severity="WARNING",
            )
            db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
        return current_user

    return checker


require_compliance = require_roles(Role.ADMIN, Role.COMPLIANCE)
require_admin = require_roles(Role.ADMIN)
require_global_view = require_roles(Role.ADMIN, Role.COMPLIANCE, Role.AUDITOR)
