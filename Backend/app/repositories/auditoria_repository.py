"""
Repositorio de auditoría — registro de acciones sensibles sobre inventario/entregas.
Extraído del antiguo RFIDRepository durante la poda de Fase 0 (clon prevención).
"""
import json
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.logging_config import logger


class AuditoriaRepository:
    def __init__(self, db: Session):
        self.db = db

    def registrar_auditoria(self, sku: str, accion: str, usuario_id: Optional[int],
                            usuario_nombre: Optional[str], detalle: dict) -> None:
        """Inserta un registro en auditoria_prendas."""
        query = text("""
            INSERT INTO auditoria_prendas (sku, accion, usuario_id, usuario_nombre, detalle)
            VALUES (:sku, :accion, :usuario_id, :usuario_nombre, :detalle)
        """)
        try:
            self.db.execute(query, {
                "sku": sku,
                "accion": accion,
                "usuario_id": usuario_id,
                "usuario_nombre": usuario_nombre,
                "detalle": json.dumps(detalle, ensure_ascii=False),
            })
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al registrar auditoría: {type(e).__name__}: {e}")
