"""
Schemas Pydantic del dominio EPP — categorías, productos, stock y movimientos.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Categorías ───────────────────────────────────────────────────────────────

class CategoriaCreate(BaseModel):
    nombre_categoria: str


class CategoriaResponse(BaseModel):
    categoria_id: int
    nombre_categoria: str


# ── Productos ────────────────────────────────────────────────────────────────

class ProductoCreate(BaseModel):
    nombre: str
    categoria_id: Optional[int] = None
    talla_aplica: bool = False
    certificacion: Optional[str] = None
    descripcion: Optional[str] = None
    vida_util_meses: Optional[int] = None


class ProductoUpdate(BaseModel):
    """Actualización parcial: solo se aplican los campos informados."""
    nombre: Optional[str] = None
    categoria_id: Optional[int] = None
    talla_aplica: Optional[bool] = None
    certificacion: Optional[str] = None
    descripcion: Optional[str] = None
    vida_util_meses: Optional[int] = None
    activo: Optional[bool] = None


class ProductoResponse(BaseModel):
    producto_id: int
    nombre: str
    categoria_id: Optional[int] = None
    nombre_categoria: Optional[str] = None
    talla_aplica: bool
    certificacion: Optional[str] = None
    descripcion: Optional[str] = None
    vida_util_meses: Optional[int] = None
    activo: bool


# ── Stock ────────────────────────────────────────────────────────────────────

class StockResponse(BaseModel):
    stock_id: int
    producto_id: int
    nombre_producto: str
    categoria_id: Optional[int] = None
    nombre_categoria: Optional[str] = None
    talla_id: Optional[int] = None
    nombre_talla: Optional[str] = None
    cantidad_actual: int
    stock_minimo: int
    bajo_minimo: bool


class AjusteStockRequest(BaseModel):
    """
    Ajuste manual de stock. Fija la cantidad a un valor absoluto; el movimiento
    resultante (tipo AJUSTE) registra el delta contra la cantidad anterior.
    La observación es obligatoria (regla de oro del libro mayor).
    """
    producto_id: int
    talla_id: Optional[int] = None
    cantidad_nueva: int = Field(..., ge=0)
    observacion: str


# ── Movimientos ──────────────────────────────────────────────────────────────

class MovimientoResponse(BaseModel):
    movimiento_id: int
    producto_id: int
    nombre_producto: Optional[str] = None
    talla_id: Optional[int] = None
    nombre_talla: Optional[str] = None
    tipo: str
    cantidad: int
    referencia_id: Optional[int] = None
    usuario_id: Optional[int] = None
    observacion: Optional[str] = None
    fecha: datetime
