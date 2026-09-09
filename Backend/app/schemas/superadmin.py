from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UsuarioCreate(BaseModel):
    username: str
    correo: str
    contrasena: str
    rol_id: int
    activo: bool = True
    # Recinto en el que opera. None solo para los roles de FULL_ACCESS_ROLES:
    # un usuario común sin recinto no puede mover stock (403).
    recinto_id: Optional[int] = None


class UsuarioUpdate(BaseModel):
    username: Optional[str] = None
    correo: Optional[str] = None
    rol_id: Optional[int] = None
    activo: Optional[bool] = None
    # Se distingue "no informado" de "ponerlo en NULL" con el flag de abajo:
    # en este schema None ya significa lo primero.
    recinto_id: Optional[int] = None
    limpiar_recinto: bool = False


class UsuarioPasswordReset(BaseModel):
    nueva_contrasena: str


class UsuarioCambiarPassword(BaseModel):
    contrasena_actual: str
    nueva_contrasena: str


class UsuarioResponse(BaseModel):
    user_id: int
    username: str
    correo: str
    rol_id: int
    nombre_rol: str
    activo: bool
    creado_en: Optional[datetime] = None
    recinto_id: Optional[int] = None
    nombre_recinto: Optional[str] = None


class RecintoResponse(BaseModel):
    recinto_id: int
    nombre_recinto: str


class ModuloResponse(BaseModel):
    modulo_id: int
    nombre_modulo: str


class RolCreate(BaseModel):
    nombre_rol: str
    modulo_ids: list[int] = []


class RolUpdate(BaseModel):
    nombre_rol: Optional[str] = None
    modulo_ids: Optional[list[int]] = None


class RolResponse(BaseModel):
    rol_id: int
    nombre_rol: str
    modulos: list[ModuloResponse] = []


class RolModulosUpdate(BaseModel):
    modulo_ids: list[int]
