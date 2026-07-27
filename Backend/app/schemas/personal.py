from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


class PersonalBase(BaseModel):
    rut: str
    nombre_completo: str
    empresa: str
    cargo: Optional[str] = None
    area_id: Optional[int] = None
    subarea_id: Optional[int] = None
    nombre_area: Optional[str] = None
    nombre_subarea: Optional[str] = None
    url_picture: Optional[str] = None


class PersonalResponse(PersonalBase):
    activo: Optional[bool] = True
    sync_at: Optional[datetime] = None
    epp_vigentes: Optional[int] = None


class SyncResumen(BaseModel):
    """Resultado de una corrida de sincronización desde RRHH (Fase 4)."""
    dry_run: bool = False
    fecha: datetime
    leidos: int
    creados: int
    actualizados: int
    sin_cambios: int
    desactivados: int
    errores: List[str] = []
    ruts_creados: List[str] = []
    ruts_desactivados: List[str] = []


class SyncEstado(BaseModel):
    ultima_sincronizacion: Optional[datetime] = None
