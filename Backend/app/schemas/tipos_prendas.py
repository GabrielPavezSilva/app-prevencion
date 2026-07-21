from pydantic import BaseModel
from pydantic import ConfigDict


class TiposPrendasBase(BaseModel):
    tipo_id: int
    nombre_tipo: str


class TiposPrendasCreate(BaseModel):
    nombre_tipo: str


class TiposPrendasUpdate(BaseModel):
    nombre_tipo: str


class TiposPrendasResponse(BaseModel):
    tipo_id: int
    nombre_tipo: str
    model_config = ConfigDict(from_attributes=True)
