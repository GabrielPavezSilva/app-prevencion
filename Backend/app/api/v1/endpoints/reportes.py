"""
Endpoints de reportabilidad EPP — /api/reportes (Fase 5).

Reescrito de cero: el router anterior consultaba tablas del dominio lavandería
(eliminadas en Fase 1) y **no tenía ninguna dependencia de auth** — su
`POST /importar/{template_id}` era escritura masiva sin token. Ese importador
además quedó obsoleto en Fase 3, lo reemplazó /api/importaciones.

Cada reporte expone dos rutas gemelas que llaman al mismo método de service:
JSON para la tabla en pantalla y `.xlsx` para la descarga. Se usan rutas
separadas y no `?formato=` porque `response_model` y `StreamingResponse` no
conviven bien en una misma ruta.
"""
from datetime import date
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.security import require_module
from app.db.deps import get_mysql_db
from app.schemas.reportes import EppVigenteRow, StockRow, TrazabilidadRow
from app.services.reportes_service import ReportesService

router = APIRouter()

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _descarga(buffer, nombre: str) -> StreamingResponse:
    archivo = f"{nombre}_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        buffer,
        media_type=_XLSX,
        headers={
            # filename* en UTF-8: los nombres llevan acentos
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(archivo)}"
        },
    )


# ── Filtros compartidos ──────────────────────────────────────────────────────

def filtros_entregas(
    desde: Optional[str] = Query(None, description="Fecha local YYYY-MM-DD (inclusive)"),
    hasta: Optional[str] = Query(None, description="Fecha local YYYY-MM-DD (inclusive)"),
    motivo: Optional[str] = Query(None, description="NUEVA | PERDIDA | DANO"),
    empresa_id: Optional[int] = None,
    area_id: Optional[int] = None,
    subarea_id: Optional[int] = None,
    producto_id: Optional[int] = None,
    categoria_id: Optional[int] = None,
    rut: Optional[str] = None,
) -> dict:
    return {
        "desde": desde, "hasta": hasta, "motivo": motivo,
        "empresa_id": empresa_id, "area_id": area_id, "subarea_id": subarea_id,
        "producto_id": producto_id, "categoria_id": categoria_id, "rut": rut,
    }


def filtros_vigentes(
    empresa_id: Optional[int] = None,
    area_id: Optional[int] = None,
    subarea_id: Optional[int] = None,
    producto_id: Optional[int] = None,
    categoria_id: Optional[int] = None,
    rut: Optional[str] = None,
    incluir_inactivos: bool = Query(False, description="Incluye desvinculados con EPP sin devolver"),
) -> dict:
    return {
        "empresa_id": empresa_id, "area_id": area_id, "subarea_id": subarea_id,
        "producto_id": producto_id, "categoria_id": categoria_id, "rut": rut,
        "incluir_inactivos": incluir_inactivos,
    }


# ── R1 · Trazabilidad de entregas ────────────────────────────────────────────

@router.get("/entregas", response_model=List[TrazabilidadRow])
def reporte_entregas(filtros: dict = Depends(filtros_entregas),
                     limit: int = Query(1000, le=10000),
                     db: Session = Depends(get_mysql_db),
                     _: dict = Depends(require_module("reportes"))):
    """Trazabilidad de entregas filtrable por motivo, área, fecha, producto y trabajador."""
    return ReportesService(db).trazabilidad(filtros, limit)


@router.get("/entregas.xlsx")
def reporte_entregas_excel(filtros: dict = Depends(filtros_entregas),
                           db: Session = Depends(get_mysql_db),
                           _: dict = Depends(require_module("reportes"))):
    """Mismo reporte que GET /entregas, sin límite de filas, en Excel."""
    return _descarga(ReportesService(db).trazabilidad_excel(filtros), "trazabilidad_entregas")


# ── R2 · EPP vigentes por trabajador ─────────────────────────────────────────

@router.get("/epp-vigentes", response_model=List[EppVigenteRow])
def reporte_epp_vigentes(filtros: dict = Depends(filtros_vigentes),
                         db: Session = Depends(get_mysql_db),
                         _: dict = Depends(require_module("reportes"))):
    """
    EPP vigentes por trabajador. Incluye a los trabajadores sin ningún EPP
    (marcados con `sin_epp`) — saber quién está descubierto es parte del reporte.
    """
    return ReportesService(db).epp_vigentes(filtros)


@router.get("/epp-vigentes.xlsx")
def reporte_epp_vigentes_excel(filtros: dict = Depends(filtros_vigentes),
                               db: Session = Depends(get_mysql_db),
                               _: dict = Depends(require_module("reportes"))):
    """Dos hojas: detalle por EPP y resumen por trabajador."""
    return _descarga(ReportesService(db).epp_vigentes_excel(filtros), "epp_vigentes")


# ── R3 · Stock y quiebres ────────────────────────────────────────────────────

@router.get("/stock", response_model=List[StockRow])
def reporte_stock(categoria_id: Optional[int] = None,
                  solo_alertas: bool = Query(False, description="Solo lo que está en o bajo el mínimo"),
                  dias_consumo: int = Query(90, ge=1, le=365),
                  db: Session = Depends(get_mysql_db),
                  _: dict = Depends(require_module("reportes"))):
    """Snapshot de stock con consumo de la ventana y cobertura estimada en días."""
    return ReportesService(db).stock(categoria_id, solo_alertas, dias_consumo)


@router.get("/stock.xlsx")
def reporte_stock_excel(categoria_id: Optional[int] = None,
                        solo_alertas: bool = False,
                        dias_consumo: int = Query(90, ge=1, le=365),
                        db: Session = Depends(get_mysql_db),
                        _: dict = Depends(require_module("reportes"))):
    return _descarga(
        ReportesService(db).stock_excel(categoria_id, solo_alertas, dias_consumo),
        "stock_epp",
    )
