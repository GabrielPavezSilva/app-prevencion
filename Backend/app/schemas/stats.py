from pydantic import BaseModel
from typing import List


class CantidadPorNombre(BaseModel):
    nombre: str
    cantidad: int


class InventarioStatsResponse(BaseModel):
    total: int
    disponibles: int
    en_uso: int
    con_rfid: int
    sin_rfid: int
    por_tipo: List[CantidadPorNombre]
    por_talla: List[CantidadPorNombre]
    por_empresa: List[CantidadPorNombre]
    por_seccion: List[CantidadPorNombre]
    por_temporada: List[CantidadPorNombre]
