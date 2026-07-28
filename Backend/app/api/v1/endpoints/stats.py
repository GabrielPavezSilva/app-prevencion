"""
Endpoint del dashboard EPP — /api/stats (Fase 5).

Reemplaza a `GET /stats/inventario`, que agregaba sobre `lecturas_rfid` /
`secciones` / `temporadas` (dominio lavandería, tablas eliminadas en Fase 1).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_module
from app.db.deps import get_mysql_db
from app.schemas.stats import DashboardResponse
from app.services.reportes_service import ReportesService

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    desde: Optional[str] = Query(None, description="Fecha local YYYY-MM-DD; default: día 1 del mes en curso"),
    hasta: Optional[str] = Query(None, description="Fecha local YYYY-MM-DD; default: hoy"),
    empresa_id: Optional[int] = None,
    area_id: Optional[int] = None,
    meses: int = Query(12, ge=1, le=36, description="Ventana de la serie mensual"),
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(require_module("dashboard")),
):
    """
    Métricas del panel de control: KPI del periodo, serie mensual, distribución
    por motivo/área/producto y alertas de stock.
    """
    return ReportesService(db).dashboard(desde, hasta, empresa_id, area_id, meses)
