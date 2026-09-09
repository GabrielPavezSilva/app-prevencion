from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
from app.core.logging_config import logger


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Busca un usuario por su username en la tabla usuarios."""
        query = text("""
            SELECT u.user_id, u.username, u.correo, u.contrasena,
                   u.activo, u.rol_id, r.nombre_rol,
                   u.recinto_id, rec.nombre_recinto
            FROM usuarios u
            JOIN roles r ON u.rol_id = r.rol_id
            LEFT JOIN recintos rec ON rec.recinto_id = u.recinto_id
            WHERE u.username = :username
        """)
        try:
            result = self.db.execute(query, {"username": username})
            row = result.mappings().fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error al buscar usuario: {type(e).__name__}: {str(e)}")
            raise

    def get_modulos_for_rol(self, rol_id: int) -> list[str]:
        """Retorna la lista de nombres de módulos asignados a un rol."""
        query = text("""
            SELECT m.nombre_modulo
            FROM roles_modulos rm
            JOIN modulos m ON rm.modulo_id = m.modulo_id
            WHERE rm.rol_id = :rol_id
            ORDER BY m.nombre_modulo
        """)
        try:
            result = self.db.execute(query, {"rol_id": rol_id})
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error al obtener módulos del rol {rol_id}: {type(e).__name__}: {str(e)}")
            raise

    def get_user_by_correo(self, correo: str) -> Optional[Dict[str, Any]]:
        """Busca un usuario por su correo en la tabla usuarios."""
        query = text("""
            SELECT u.user_id, u.username, u.correo, u.contrasena,
                   u.activo, u.rol_id, r.nombre_rol
            FROM usuarios u
            JOIN roles r ON u.rol_id = r.rol_id
            WHERE u.correo = :correo
        """)
        try:
            result = self.db.execute(query, {"correo": correo})
            row = result.mappings().fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error al buscar usuario: {type(e).__name__}: {str(e)}")
            raise

