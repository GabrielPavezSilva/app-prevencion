from pydantic import BaseModel, field_validator
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    contrasena: str

    @field_validator("username", "contrasena")
    @classmethod
    def no_empty(cls, v: str, info) -> str:
        v = v.strip()
        if not v:
            raise ValueError(f"{info.field_name} no puede estar vacío")
        if len(v) > 150:
            raise ValueError(f"{info.field_name} excede el largo máximo")
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    modulos: list[str] = []


class LoginResponse(BaseModel):
    token: str
    user: UserResponse
