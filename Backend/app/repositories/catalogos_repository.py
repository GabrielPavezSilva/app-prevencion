from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from app.core.logging_config import logger


class CatalogosRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Tipos de Prenda ──────────────────────────────────────────────────────

    def get_all_tipos(self) -> List[Dict[str, Any]]:
        result = self.db.execute(
            text("SELECT tipo_id, nombre_tipo FROM tiposprendas ORDER BY nombre_tipo")
        )
        return [dict(r) for r in result.mappings().fetchall()]

    def get_tipo_by_id(self, tipo_id: int) -> Optional[Dict[str, Any]]:
        result = self.db.execute(
            text("SELECT tipo_id, nombre_tipo FROM tiposprendas WHERE tipo_id = :id"),
            {"id": tipo_id},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None

    def get_tipo_by_nombre(self, nombre: str) -> Optional[Dict[str, Any]]:
        result = self.db.execute(
            text("SELECT tipo_id, nombre_tipo FROM tiposprendas WHERE LOWER(nombre_tipo) = LOWER(:nombre)"),
            {"nombre": nombre},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None

    def tipo_tiene_inventario(self, tipo_id: int) -> bool:
        result = self.db.execute(
            text("SELECT COUNT(*) AS total FROM lecturas_rfid WHERE tipo_id = :id"),
            {"id": tipo_id},
        )
        return result.scalar() > 0

    def create_tipo(self, nombre: str) -> Dict[str, Any]:
        try:
            self.db.execute(
                text("INSERT INTO tiposprendas (nombre_tipo) VALUES (:nombre)"),
                {"nombre": nombre},
            )
            self.db.commit()
            result = self.db.execute(
                text("SELECT tipo_id, nombre_tipo FROM tiposprendas WHERE LOWER(nombre_tipo) = LOWER(:nombre)"),
                {"nombre": nombre},
            )
            return dict(result.mappings().fetchone())
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear tipo de prenda: {type(e).__name__}: {str(e)}")
            raise

    def update_tipo(self, tipo_id: int, nombre: str) -> Dict[str, Any]:
        try:
            self.db.execute(
                text("UPDATE tiposprendas SET nombre_tipo = :nombre WHERE tipo_id = :id"),
                {"nombre": nombre, "id": tipo_id},
            )
            self.db.commit()
            return {"tipo_id": tipo_id, "nombre_tipo": nombre}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar tipo de prenda: {type(e).__name__}: {str(e)}")
            raise

    def delete_tipo(self, tipo_id: int) -> None:
        try:
            self.db.execute(
                text("DELETE FROM tiposprendas WHERE tipo_id = :id"),
                {"id": tipo_id},
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar tipo de prenda: {type(e).__name__}: {str(e)}")
            raise

    # ── Tallas ───────────────────────────────────────────────────────────────

    def get_all_tallas(self) -> List[Dict[str, Any]]:
        result = self.db.execute(
            text("SELECT talla_id, nombre_talla FROM tallas ORDER BY nombre_talla")
        )
        return [dict(r) for r in result.mappings().fetchall()]

    def get_talla_by_id(self, talla_id: int) -> Optional[Dict[str, Any]]:
        result = self.db.execute(
            text("SELECT talla_id, nombre_talla FROM tallas WHERE talla_id = :id"),
            {"id": talla_id},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None

    def get_talla_by_nombre(self, nombre: str) -> Optional[Dict[str, Any]]:
        result = self.db.execute(
            text("SELECT talla_id, nombre_talla FROM tallas WHERE LOWER(nombre_talla) = LOWER(:nombre)"),
            {"nombre": nombre},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None

    def talla_tiene_inventario(self, talla_id: int) -> bool:
        result = self.db.execute(
            text("SELECT COUNT(*) AS total FROM lecturas_rfid WHERE talla_id = :id"),
            {"id": talla_id},
        )
        return result.scalar() > 0

    def create_talla(self, nombre: str) -> Dict[str, Any]:
        try:
            self.db.execute(
                text("INSERT INTO tallas (nombre_talla) VALUES (:nombre)"),
                {"nombre": nombre},
            )
            self.db.commit()
            result = self.db.execute(
                text("SELECT talla_id, nombre_talla FROM tallas WHERE LOWER(nombre_talla) = LOWER(:nombre)"),
                {"nombre": nombre},
            )
            return dict(result.mappings().fetchone())
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear talla: {type(e).__name__}: {str(e)}")
            raise

    def update_talla(self, talla_id: int, nombre: str) -> Dict[str, Any]:
        try:
            self.db.execute(
                text("UPDATE tallas SET nombre_talla = :nombre WHERE talla_id = :id"),
                {"nombre": nombre, "id": talla_id},
            )
            self.db.commit()
            return {"talla_id": talla_id, "nombre_talla": nombre}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar talla: {type(e).__name__}: {str(e)}")
            raise

    def delete_talla(self, talla_id: int) -> None:
        try:
            self.db.execute(
                text("DELETE FROM tallas WHERE talla_id = :id"),
                {"id": talla_id},
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar talla: {type(e).__name__}: {str(e)}")
            raise
