"""
Schemas Pydantic del flujo de entregas de EPP.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Motivos válidos
MOTIVOS_ENTREGA = ("NUEVA", "PERDIDA")   # descuentan stock, sin sustitución
MOTIVO_DANO = "DANO"                      # sustitución (endpoint dedicado)


class EntregaLinea(BaseModel):
    producto_id: int
    talla_id: Optional[int] = None
    cantidad: int = Field(1, gt=0)
    motivo: str = "NUEVA"                 # NUEVA | PERDIDA
    observacion: Optional[str] = None
    uuid: Optional[str] = None            # idempotencia offline (D3)


class EntregaCreate(BaseModel):
    rut: str
    lineas: List[EntregaLinea] = Field(..., min_length=1)


class SustitucionCreate(BaseModel):
    rut: str
    entrega_reemplazada_id: int
    producto_id: int
    talla_id: Optional[int] = None
    cantidad: int = Field(1, gt=0)
    observacion: Optional[str] = None
    uuid: Optional[str] = None


class EntregaResponse(BaseModel):
    entrega_id: int
    rut: str
    nombre_completo: str
    empresa_id: Optional[int] = None
    producto_id: int
    nombre_producto: Optional[str] = None
    talla_id: Optional[int] = None
    nombre_talla: Optional[str] = None
    cantidad: int
    motivo: str
    entrega_reemplazada_id: Optional[int] = None
    estado_firma: str
    usuario_entrega: Optional[int] = None
    observacion: Optional[str] = None
    fecha_entrega: datetime
