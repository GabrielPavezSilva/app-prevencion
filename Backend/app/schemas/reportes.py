"""
Schemas de reportabilidad EPP (Fase 5).

Reemplaza al `ReportConfigSchema` del dominio lavandería (constructor genérico
de columnas): en prevención los tres reportes son fijos y lo que varía son los
filtros.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TrazabilidadRow(BaseModel):
    entrega_id: int
    fecha_entrega: Optional[datetime] = None
    rut: str
    nombre_completo: str
    empresa: Optional[str] = None
    area: Optional[str] = None
    subarea: Optional[str] = None
    cargo: Optional[str] = None
    recinto: Optional[str] = None
    categoria: Optional[str] = None
    producto: Optional[str] = None
    talla: Optional[str] = None
    cantidad: int
    motivo: str
    entrega_reemplazada_id: Optional[int] = None
    fecha_reemplazada: Optional[datetime] = None
    observacion: Optional[str] = None
    registrado_por: Optional[str] = None


class EppVigenteRow(BaseModel):
    rut: str
    nombre_completo: str
    empresa: Optional[str] = None
    area: Optional[str] = None
    subarea: Optional[str] = None
    cargo: Optional[str] = None
    activo: bool = True
    recinto: Optional[str] = None
    categoria: Optional[str] = None
    producto: Optional[str] = None
    talla: Optional[str] = None
    cantidad: Optional[int] = None
    motivo: Optional[str] = None
    fecha_entrega: Optional[datetime] = None
    dias_desde_entrega: Optional[int] = None
    sin_epp: bool = False


class StockRow(BaseModel):
    recinto: Optional[str] = None
    categoria: Optional[str] = None
    producto: str
    talla: Optional[str] = None
    cantidad_actual: int
    stock_minimo: int
    deficit: int
    estado: str                      # QUIEBRE | BAJO | OK
    consumo: int                     # unidades entregadas en la ventana
    cobertura_dias: Optional[int] = None


class ResumenTrabajadorRow(BaseModel):
    rut: str
    nombre_completo: str
    empresa: Optional[str] = None
    area: Optional[str] = None
    subarea: Optional[str] = None
    cargo: Optional[str] = None
    activo: bool = True
    total_epp: int
    unidades: int
    detalle: str
    sin_epp: bool


class AreaCatalogo(BaseModel):
    area_id: int
    nombre_area: str
    empresa_id: Optional[int] = None
    nombre_empresa: Optional[str] = None


class SubAreaCatalogo(BaseModel):
    subarea_id: int
    nombre_subarea: str
    area_id: Optional[int] = None
    nombre_area: Optional[str] = None
