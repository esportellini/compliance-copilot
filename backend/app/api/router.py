from fastapi import APIRouter

from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.copilot import router as copilot_router
from app.api.routes.documents import router as documents_router
from app.api.routes.misc import dashboard_router, users_router
from app.api.routes.pre_approvals import router as pre_approvals_router
from app.api.routes.privacy import router as privacy_router
from app.api.routes.products import router as products_router
from app.api.routes.reports import router as reports_router
from app.api.routes.rules import router as rules_router
from app.api.routes.settings import router as settings_router
from app.api.routes.training import router as training_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(copilot_router)
api_router.include_router(products_router)
api_router.include_router(rules_router)
api_router.include_router(documents_router)
api_router.include_router(pre_approvals_router)
api_router.include_router(audit_router)
api_router.include_router(reports_router)
api_router.include_router(training_router)
api_router.include_router(settings_router)
api_router.include_router(privacy_router)
api_router.include_router(users_router)
api_router.include_router(dashboard_router)