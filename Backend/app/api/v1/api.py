"""
API Router - Agrupa todos los endpoints
"""
from fastapi import APIRouter
from app.api.v1.endpoints import personal, auth, stats, templates, reportes, inventario, superadmin, epp

api_router = APIRouter()

# Include all endpoint routers with their prefixes
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
api_router.include_router(personal.router, prefix="/personal", tags=["Personal"])
api_router.include_router(stats.router, prefix="/stats", tags=["Estadísticas"])
api_router.include_router(templates.router, prefix="/templates", tags=["Templates"])
api_router.include_router(reportes.router, prefix="/reportes", tags=["Reportes"])
api_router.include_router(inventario.router, prefix="/inventario", tags=["Inventario"])
api_router.include_router(epp.router, prefix="/epp", tags=["EPP"])
api_router.include_router(superadmin.router, prefix="/superadmin", tags=["Superadmin"])
