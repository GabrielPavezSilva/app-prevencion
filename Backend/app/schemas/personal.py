from pydantic import BaseModel
from typing import Optional


class PersonalBase(BaseModel):
    rut: str
    nombre_completo: str
    empresa: str
    cargo: str
    area_id: int
    subarea_id: Optional[int] = None
    talla_id: Optional[int] = None
    nombre_subarea: Optional[str] = None
    url_picture: Optional[str] = None


class PersonalResponse(PersonalBase):
    activo: Optional[bool] = True
