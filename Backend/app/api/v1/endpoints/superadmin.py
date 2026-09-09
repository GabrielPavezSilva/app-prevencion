from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.deps import get_mysql_db
from app.core.security import get_current_user
from app.services.superadmin_service import SuperAdminService
from app.schemas.superadmin import (
    UsuarioCreate, UsuarioUpdate, UsuarioPasswordReset, UsuarioCambiarPassword,
    UsuarioResponse, RolCreate, RolUpdate, RolResponse, ModuloResponse, RolModulosUpdate,
    RecintoResponse,
)

router = APIRouter()


def _require_superadmin(current_user: dict = Depends(get_current_user)) -> dict:
    """Permite acceso solo a admin o a quienes tengan el módulo 'superadmin'."""
    role = current_user.get("role", "")
    modulos = current_user.get("modulos", [])
    if role != "admin" and "superadmin" not in modulos:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso denegado")
    return current_user


# ── Usuarios ──────────────────────────────────────────────────────────────────

@router.get("/usuarios", response_model=list[UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(_require_superadmin),
):
    return SuperAdminService(db).get_usuarios()


@router.post("/usuarios", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    data: UsuarioCreate,
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(_require_superadmin),
):
    return SuperAdminService(db).create_usuario(data)


@router.put("/usuarios/{user_id}", response_model=UsuarioResponse)
def actualizar_usuario(
    user_id: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(_require_superadmin),
):
    return SuperAdminService(db).update_usuario(user_id, data)


@router.put("/usuarios/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def resetear_password(
    user_id: int,
    data: UsuarioPasswordReset,
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(_require_superadmin),
):
    SuperAdminService(db).reset_password(user_id, data)


# ── Cambio de contraseña propio (cualquier usuario autenticado) ────────────────

@router.put("/usuarios/me/password", status_code=status.HTTP_204_NO_CONTENT)
def cambiar_password_propio(
    data: UsuarioCambiarPassword,
    db: Session = Depends(get_mysql_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("userId")
    SuperAdminService(db).cambiar_password_propio(
        user_id, data.contrasena_actual, data.nueva_contrasena
    )


# ── Roles ──────────────────────────────────────────────────────────────────────

@router.get("/roles", response_model=list[RolResponse])
def listar_roles(
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(_require_superadmin),
):
    return SuperAdminService(db).get_roles()


@router.post("/roles", response_model=RolResponse, status_code=status.HTTP_201_CREATED)
def crear_rol(
    data: RolCreate,
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(_require_superadmin),
):
    return SuperAdminService(db).create_rol(data)


@router.put("/roles/{rol_id}", response_model=RolResponse)
def actualizar_rol(
    rol_id: int,
    data: RolUpdate,
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(_require_superadmin),
):
    return SuperAdminService(db).update_rol(rol_id, data)


@router.delete("/roles/{rol_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_rol(
    rol_id: int,
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(_require_superadmin),
):
    SuperAdminService(db).delete_rol(rol_id)


@router.put("/roles/{rol_id}/modulos", response_model=RolResponse)
def asignar_modulos_a_rol(
    rol_id: int,
    data: RolModulosUpdate,
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(_require_superadmin),
):
    return SuperAdminService(db).set_rol_modulos(rol_id, data)


# ── Recintos ──────────────────────────────────────────────────────────────────

@router.get("/recintos", response_model=list[RecintoResponse])
def listar_recintos(
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(_require_superadmin),
):
    """Catálogo para el selector de recinto al crear o editar un usuario."""
    return SuperAdminService(db).get_recintos()


# ── Módulos ────────────────────────────────────────────────────────────────────

@router.get("/modulos", response_model=list[ModuloResponse])
def listar_modulos(
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(_require_superadmin),
):
    return SuperAdminService(db).get_modulos()
