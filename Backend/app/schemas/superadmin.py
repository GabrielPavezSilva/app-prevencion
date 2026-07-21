from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UsuarioCreate(BaseModel):
    username: str
    correo: str
    contrasena: str
    rol_id: int
    activo: bool = True


class UsuarioUpdate(BaseModel):
    username: Optional[str] = None
    correo: Optional[str] = None
    rol_id: Optional[int] = None
    activo: Optional[bool] = None


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
