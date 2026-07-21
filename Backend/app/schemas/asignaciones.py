from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AsignacionesBase(BaseModel):
    asignacion_id: int
    rut: str
    nombre_completo: str
    sku: str
    tag_epc: str
    fecha_entrega: datetime
    fecha_devolucion: Optional[datetime] = None
    item_nombre: Optional[str] = None  # Nombre legible (tipo + talla), desde JOIN con inventario

class AsignacionesResponse(AsignacionesBase):
    pass