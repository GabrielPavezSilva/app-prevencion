from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional


class SuperAdminRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Usuarios ──────────────────────────────────────────────────────────────

    def get_all_usuarios(self) -> list[dict]:
        result = self.db.execute(text("""
            SELECT u.user_id, u.username, u.correo, u.rol_id,
                   r.nombre_rol, COALESCE(u.activo, true) AS activo, u.creado_en
            FROM usuarios u
            JOIN roles r ON u.rol_id = r.rol_id
            ORDER BY u.user_id
        """))
        return [dict(row) for row in result.mappings().fetchall()]

    def get_usuario_by_id(self, user_id: int) -> Optional[dict]:
        result = self.db.execute(text("""
            SELECT u.user_id, u.username, u.correo, u.contrasena,
                   u.rol_id, r.nombre_rol, COALESCE(u.activo, true) AS activo, u.creado_en
            FROM usuarios u
            JOIN roles r ON u.rol_id = r.rol_id
            WHERE u.user_id = :user_id
        """), {"user_id": user_id})
        row = result.mappings().fetchone()
        return dict(row) if row else None

    def get_usuario_by_username(self, username: str) -> Optional[dict]:
        result = self.db.execute(text("""
            SELECT user_id, username, contrasena FROM usuarios WHERE username = :username
        """), {"username": username})
        row = result.mappings().fetchone()
        return dict(row) if row else None

    def username_exists(self, username: str, exclude_id: Optional[int] = None) -> bool:
        if exclude_id:
            result = self.db.execute(text(
                "SELECT 1 FROM usuarios WHERE username = :u AND user_id != :id"
            ), {"u": username, "id": exclude_id})
        else:
            result = self.db.execute(text(
                "SELECT 1 FROM usuarios WHERE username = :u"
            ), {"u": username})
        return result.fetchone() is not None

    def correo_exists(self, correo: str, exclude_id: Optional[int] = None) -> bool:
        if exclude_id:
            result = self.db.execute(text(
                "SELECT 1 FROM usuarios WHERE correo = :c AND user_id != :id"
            ), {"c": correo, "id": exclude_id})
        else:
            result = self.db.execute(text(
                "SELECT 1 FROM usuarios WHERE correo = :c"
            ), {"c": correo})
        return result.fetchone() is not None

    def create_usuario(self, username: str, correo: str, hashed_password: str,
                       rol_id: int, activo: bool) -> int:
        result = self.db.execute(text("""
            INSERT INTO usuarios (username, correo, contrasena, rol_id, activo)
            VALUES (:username, :correo, :contrasena, :rol_id, :activo)
            RETURNING user_id
        """), {
            "username": username,
            "correo": correo,
            "contrasena": hashed_password,
            "rol_id": rol_id,
            "activo": activo,
        })
        self.db.commit()
        return result.scalar()

    def update_usuario(self, user_id: int, username: Optional[str], correo: Optional[str],
                       rol_id: Optional[int], activo: Optional[bool]) -> bool:
        parts = []
        params: dict = {"user_id": user_id}
        if username is not None:
            parts.append("username = :username")
            params["username"] = username
        if correo is not None:
            parts.append("correo = :correo")
            params["correo"] = correo
        if rol_id is not None:
            parts.append("rol_id = :rol_id")
            params["rol_id"] = rol_id
        if activo is not None:
            parts.append("activo = :activo")
            params["activo"] = activo
        if not parts:
            return False
        self.db.execute(text(
            f"UPDATE usuarios SET {', '.join(parts)} WHERE user_id = :user_id"
        ), params)
        self.db.commit()
        return True

    def reset_password(self, user_id: int, hashed_password: str) -> None:
        self.db.execute(text("""
            UPDATE usuarios SET contrasena = :pwd WHERE user_id = :user_id
        """), {"pwd": hashed_password, "user_id": user_id})
        self.db.commit()

    # ── Roles ─────────────────────────────────────────────────────────────────

    def get_all_roles_with_modulos(self) -> list[dict]:
        roles_result = self.db.execute(text(
            "SELECT rol_id, nombre_rol FROM roles ORDER BY rol_id"
        ))
        roles = [dict(r) for r in roles_result.mappings().fetchall()]

        for rol in roles:
            mods_result = self.db.execute(text("""
                SELECT m.modulo_id, m.nombre_modulo
                FROM roles_modulos rm
                JOIN modulos m ON rm.modulo_id = m.modulo_id
                WHERE rm.rol_id = :rol_id
                ORDER BY m.nombre_modulo
            """), {"rol_id": rol["rol_id"]})
            rol["modulos"] = [dict(m) for m in mods_result.mappings().fetchall()]

        return roles

    def get_all_modulos(self) -> list[dict]:
        result = self.db.execute(text(
            "SELECT modulo_id, nombre_modulo FROM modulos ORDER BY nombre_modulo"
        ))
        return [dict(r) for r in result.mappings().fetchall()]

    def rol_nombre_exists(self, nombre_rol: str, exclude_id: Optional[int] = None) -> bool:
        if exclude_id:
            result = self.db.execute(text(
                "SELECT 1 FROM roles WHERE nombre_rol = :n AND rol_id != :id"
            ), {"n": nombre_rol, "id": exclude_id})
        else:
            result = self.db.execute(text(
                "SELECT 1 FROM roles WHERE nombre_rol = :n"
            ), {"n": nombre_rol})
        return result.fetchone() is not None

    def usuarios_count_for_rol(self, rol_id: int) -> int:
        result = self.db.execute(text(
            "SELECT COUNT(*) FROM usuarios WHERE rol_id = :rol_id"
        ), {"rol_id": rol_id})
        return result.scalar() or 0

    def create_rol(self, nombre_rol: str, modulo_ids: list[int]) -> int:
        result = self.db.execute(text(
            "INSERT INTO roles (nombre_rol) VALUES (:nombre_rol) RETURNING rol_id"
        ), {"nombre_rol": nombre_rol})
        rol_id = result.scalar()

        for modulo_id in modulo_ids:
            self.db.execute(text("""
                INSERT INTO roles_modulos (rol_id, modulo_id)
                VALUES (:rol_id, :modulo_id)
                ON CONFLICT (rol_id, modulo_id) DO NOTHING
            """), {"rol_id": rol_id, "modulo_id": modulo_id})

        self.db.commit()
        return rol_id

    def update_rol(self, rol_id: int, nombre_rol: Optional[str],
                   modulo_ids: Optional[list[int]]) -> None:
        if nombre_rol is not None:
            self.db.execute(text(
                "UPDATE roles SET nombre_rol = :nombre_rol WHERE rol_id = :rol_id"
            ), {"nombre_rol": nombre_rol, "rol_id": rol_id})

        if modulo_ids is not None:
            self.db.execute(text(
                "DELETE FROM roles_modulos WHERE rol_id = :rol_id"
            ), {"rol_id": rol_id})
            for modulo_id in modulo_ids:
                self.db.execute(text("""
                    INSERT INTO roles_modulos (rol_id, modulo_id)
                    VALUES (:rol_id, :modulo_id)
                    ON CONFLICT (rol_id, modulo_id) DO NOTHING
                """), {"rol_id": rol_id, "modulo_id": modulo_id})

        self.db.commit()

    def delete_rol(self, rol_id: int) -> None:
        self.db.execute(text(
            "DELETE FROM roles_modulos WHERE rol_id = :rol_id"
        ), {"rol_id": rol_id})
        self.db.execute(text(
            "DELETE FROM roles WHERE rol_id = :rol_id"
        ), {"rol_id": rol_id})
        self.db.commit()
