"""Compliance Copilot — FastAPI application entry point.

Security measures applied at app level:
  - CORS restricted to configured origins
  - Global exception handler (never exposes stack traces in production)
  - Health endpoint with disclaimer
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description=(
        "Plataforma de compliance para gestores de ativos e family offices. "
        "As respostas apoiam a análise de compliance, mas não substituem "
        "a revisão humana quando exigida pela política interna."
    ),
    version="1.0.0",
    # hide docs in production
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s %s — %r", request.method, request.url, exc)
    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Erro interno do servidor. Tente novamente em instantes."},
        )
    raise exc


app.include_router(api_router, prefix="/api")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "disclaimer": (
            "As respostas do Compliance Copilot apoiam a análise de compliance, "
            "mas não substituem revisão humana quando exigida pela política interna."
        ),
    }
