"""
Schemas del dashboard EPP (Fase 5).

Reemplaza a `InventarioStatsResponse` (dominio lavandería: prendas con/sin RFID,
secciones, temporadas).
"""
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.reportes import StockRow


class CantidadPorNombre(BaseModel):
    nombre: str
    cantidad: int


class PuntoSerie(BaseModel):
    mes: str            # 'YYYY-MM'
    nueva: int
    perdida: int
    dano: int
    total: int


class DashboardKpis(BaseModel):
    # Del periodo consultado — en UNIDADES (SUM de cantidad), no en filas.
    entregas_periodo: int
    lineas_periodo: int
    reposiciones_perdida: int
    sustituciones_dano: int
    trabajadores_atendidos: int
    # Estado actual, independiente del periodo
    productos_bajo_minimo: int      # incluye los que están en quiebre
    productos_en_quiebre: int
    unidades_en_bodega: int
    trabajadores_activos: int
    trabajadores_sin_epp: int


class Periodo(BaseModel):
    desde: Optional[str] = None
    hasta: Optional[str] = None


class DashboardResponse(BaseModel):
    periodo: Periodo
    kpis: DashboardKpis
    serie_mensual: List[PuntoSerie]
    por_motivo: List[CantidadPorNombre]
    por_area: List[CantidadPorNombre]
    top_productos: List[CantidadPorNombre]
    alertas_stock: List[StockRow]
