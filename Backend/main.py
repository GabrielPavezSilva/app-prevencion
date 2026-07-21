"""
FastAPI Backend - Sistema de Prevención de Riesgos (Gestión de EPP)
PostgreSQL + SQLAlchemy ORM
"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.v1.api import api_router
from app.db.session import Base
from app.db.session_mysql import engine_mysql
from app.core.logging_config import logger
from app.core.config import settings
# Importar todos los modelos para que Base.metadata los registre antes de create_all
from app.models import inventario  # noqa: F401

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas que no existan (idempotente — no toca tablas ya creadas)
    Base.metadata.create_all(bind=engine_mysql)
    logger.info("Tablas verificadas/creadas.")
    yield
    logger.info("Servidor apagándose.")


_is_prod = settings.ENVIRONMENT == "production"

app = FastAPI(
    title="Prevención EPP API",
    description="Backend de gestión de EPP — stock, entregas y trazabilidad",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — localhost para desarrollo local; dominio de producción vía CORS_ORIGINS
_cors_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
]
# Orígenes adicionales vía variable de entorno (separados por coma)
_extra = os.environ.get("CORS_ORIGINS", "")
if _extra:
    _cors_origins.extend([o.strip() for o in _extra.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.get("/")
def root():
    return {
        "mensaje": "Prevención EPP API — stock, entregas y trazabilidad",
        "docs": "/docs",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")