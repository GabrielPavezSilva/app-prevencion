from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.repositories.superadmin_repository import SuperAdminRepository
from app.schemas.superadmin import (
    UsuarioCreate, UsuarioUpdate, UsuarioPasswordReset,
    UsuarioResponse, RolCreate, RolUpdate, RolResponse, ModuloResponse, RolModulosUpdate,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLES_PROTEGIDOS = {"admin"}


class SuperAdminService:
    def __init__(self, db: Session):
        self.repo = SuperAdminRepository(db)

    # ── Usuarios ──────────────────────────────────────────────────────────────

    def get_usuarios(self) -> list[UsuarioResponse]:
        rows = self.repo.get_all_usuarios()
        return [UsuarioResponse(**r) for r in rows]

    def create_usuario(self, data: UsuarioCreate) -> UsuarioResponse:
        if self.repo.username_exists(data.username):
            raise HTTPException(status.HTTP_409_CONFLICT, "El username ya está en uso")
        if self.repo.correo_exists(data.correo):
            raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está en uso")

        hashed = pwd_context.hash(data.contrasena)
        user_id = self.repo.create_usuario(
            data.username, data.correo, hashed, data.rol_id, data.activo
        )
        row = self.repo.get_usuario_by_id(user_id)
        return UsuarioResponse(**row)

    def update_usuario(self, user_id: int, data: UsuarioUpdate) -> UsuarioResponse:
        existing = self.repo.get_usuario_by_id(user_id)
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

        if data.username and self.repo.username_exists(data.username, exclude_id=user_id):
            raise HTTPException(status.HTTP_409_CONFLICT, "El username ya está en uso")
        if data.correo and self.repo.correo_exists(data.correo, exclude_id=user_id):
            raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está en uso")

        self.repo.update_usuario(user_id, data.username, data.correo, data.rol_id, data.activo)
        row = self.repo.get_usuario_by_id(user_id)
        return UsuarioResponse(**row)

    def reset_password(self, user_id: int, data: UsuarioPasswordReset) -> None:
        if not self.repo.get_usuario_by_id(user_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
        if len(data.nueva_contrasena) < 6:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                "La contraseña debe tener al menos 6 caracteres")
        hashed = pwd_context.hash(data.nueva_contrasena)
        self.repo.reset_password(user_id, hashed)

    def cambiar_password_propio(self, user_id: int,
                                contrasena_actual: str, nueva_contrasena: str) -> None:
        """El propio usuario cambia su contraseña verificando la actual."""
        existing = self.repo.get_usuario_by_id(user_id)
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

        try:
            valid = pwd_context.verify(contrasena_actual, existing["contrasena"])
        except Exception:
            valid = (contrasena_actual == existing["contrasena"])

        if not valid:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Contraseña actual incorrecta")
        if len(nueva_contrasena) < 6:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                "La nueva contraseña debe tener al menos 6 caracteres")

        hashed = pwd_context.hash(nueva_contrasena)
        self.repo.reset_password(user_id, hashed)

    # ── Roles ─────────────────────────────────────────────────────────────────

    def get_roles(self) -> list[RolResponse]:
        rows = self.repo.get_all_roles_with_modulos()
        return [
            RolResponse(
                rol_id=r["rol_id"],
                nombre_rol=r["nombre_rol"],
                modulos=[ModuloResponse(**m) for m in r["modulos"]],
            )
            for r in rows
        ]

    def get_modulos(self) -> list[ModuloResponse]:
        rows = self.repo.get_all_modulos()
        return [ModuloResponse(**r) for r in rows]

    def create_rol(self, data: RolCreate) -> RolResponse:
        if self.repo.rol_nombre_exists(data.nombre_rol):
            raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un rol con ese nombre")
        rol_id = self.repo.create_rol(data.nombre_rol, data.modulo_ids)
        rows = self.repo.get_all_roles_with_modulos()
        rol = next((r for r in rows if r["rol_id"] == rol_id), None)
        return RolResponse(
            rol_id=rol["rol_id"],
            nombre_rol=rol["nombre_rol"],
            modulos=[ModuloResponse(**m) for m in rol["modulos"]],
        )

    def update_rol(self, rol_id: int, data: RolUpdate) -> RolResponse:
        roles = self.repo.get_all_roles_with_modulos()
        existing = next((r for r in roles if r["rol_id"] == rol_id), None)
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Rol no encontrado")

        if data.nombre_rol and self.repo.rol_nombre_exists(data.nombre_rol, exclude_id=rol_id):
            raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un rol con ese nombre")

        self.repo.update_rol(rol_id, data.nombre_rol, data.modulo_ids)
        roles = self.repo.get_all_roles_with_modulos()
        rol = next(r for r in roles if r["rol_id"] == rol_id)
        return RolResponse(
            rol_id=rol["rol_id"],
            nombre_rol=rol["nombre_rol"],
            modulos=[ModuloResponse(**m) for m in rol["modulos"]],
        )

    def set_rol_modulos(self, rol_id: int, data: RolModulosUpdate) -> RolResponse:
        roles = self.repo.get_all_roles_with_modulos()
        existing = next((r for r in roles if r["rol_id"] == rol_id), None)
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Rol no encontrado")
        self.repo.update_rol(rol_id, None, data.modulo_ids)
        roles = self.repo.get_all_roles_with_modulos()
        rol = next(r for r in roles if r["rol_id"] == rol_id)
        return RolResponse(
            rol_id=rol["rol_id"],
            nombre_rol=rol["nombre_rol"],
            modulos=[ModuloResponse(**m) for m in rol["modulos"]],
        )

    def delete_rol(self, rol_id: int) -> None:
        roles = self.repo.get_all_roles_with_modulos()
        existing = next((r for r in roles if r["rol_id"] == rol_id), None)
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Rol no encontrado")

        if existing["nombre_rol"] in ROLES_PROTEGIDOS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                f"El rol '{existing['nombre_rol']}' es protegido y no puede eliminarse")

        count = self.repo.usuarios_count_for_rol(rol_id)
        if count > 0:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"No se puede eliminar: {count} usuario(s) tienen este rol asignado"
            )

        self.repo.delete_rol(rol_id)
