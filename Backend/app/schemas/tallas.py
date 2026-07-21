from pydantic import BaseModel
from pydantic import ConfigDict


class TallasBase(BaseModel):
    talla_id: int
    nombre_talla: str


class TallasCreate(BaseModel):
    nombre_talla: str


class TallasUpdate(BaseModel):
    nombre_talla: str


class TallasResponse(BaseModel):
    talla_id: int
    nombre_talla: str
    model_config = ConfigDict(from_attributes=True)
