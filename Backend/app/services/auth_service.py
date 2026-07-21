from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import LoginResponse, UserResponse
from app.core.security import create_access_token
from app.core.logging_config import logger

# Hasher para contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: Session):
        self.repository = AuthRepository(db)

    def authenticate_user(self, username: str, contrasena: str) -> LoginResponse:
        """Autentica un usuario y retorna token JWT"""
        logger.info(f"Intento de login: {username}")

        # Buscar usuario en la BD
        user = self.repository.get_user_by_username(username)
        if not user:
            logger.warning(f"Usuario no encontrado: {username}")
            raise ValueError("Usuario o contraseña incorrectos")

        # Verificar contraseña (solo bcrypt — sin fallback a texto plano)
        try:
            is_valid = pwd_context.verify(contrasena, user["contrasena"])
        except Exception:
            logger.warning(f"Hash inválido para usuario {username} — contrasena no hasheada en BD")
            is_valid = False

        if not is_valid:
            logger.warning(f"Contraseña incorrecta para usuario: {username}")
            raise ValueError("Usuario o contraseña incorrectos")

        # Obtener módulos del rol (admin usa lista vacía — bypass total en frontend/rutas)
        modulos = self.repository.get_modulos_for_rol(user["rol_id"])

        # Generar token JWT
        token_data = {
            "userId": user["user_id"],
            "username": user["username"],
            "role": user["nombre_rol"],
            "modulos": modulos,
        }
        token = create_access_token(data=token_data)

        user_response = UserResponse(
            id=user["user_id"],
            username=user["username"],
            email=user["correo"],
            role=user["nombre_rol"],
            modulos=modulos,
        )

        logger.info(f"Login exitoso: {username} (role: {user['nombre_rol']}, módulos: {modulos})")
        return LoginResponse(token=token, user=user_response)
