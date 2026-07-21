from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.schemas.asignaciones import AsignacionesResponse
from app.core.logging_config import logger


# Output:
# Columnas: asignacion_id, rut, nombre_completo, sku, tag_epc, fecha_entrega, fecha_devolucion
class AsignacionesRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_asignaciones(self) -> List[AsignacionesResponse]:
        """Retorna las asignaciones completas desde la BD."""
        query = text("""
            SELECT 
                a.asignacion_id, 
                a.rut, 
                a.nombre_completo,
                a.sku, 
                a.tag_epc,
                a.fecha_entrega, 
                a.fecha_devolucion,
                TRIM(CONCAT(
                    COALESCE(tp.nombre_tipo, ''), 
                    CASE WHEN t.nombre_talla IS NOT NULL THEN CONCAT(' ', t.nombre_talla) ELSE '' END
                )) AS item_nombre
            FROM asignaciones a
            LEFT JOIN lecturas_rfid lr ON lr.sku = a.sku
            LEFT JOIN tiposprendas tp ON tp.tipo_id = lr.tipo_id
            LEFT JOIN tallas t ON t.talla_id = lr.talla_id
            ORDER BY a.fecha_entrega DESC
        """)
        try:
            result = self.db.execute(query).mappings().fetchall()
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error al obtener asignaciones: {type(e).__name__}: {str(e)}")
            raise

    def get_asignacion_activa_por_sku(self, sku: str):
        """Retorna la asignación activa (fecha_devolucion IS NULL) para un SKU, o None."""
        query = text("""
            SELECT asignacion_id, rut, nombre_completo, sku, tag_epc, fecha_entrega
            FROM asignaciones
            WHERE sku = :sku AND fecha_devolucion IS NULL
            ORDER BY fecha_entrega DESC
            LIMIT 1
        """)
        try:
            row = self.db.execute(query, {"sku": sku}).mappings().fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error al obtener asignación activa: {type(e).__name__}: {str(e)}")
            raise

    def crear_asignacion(self, rut: str, nombre_completo: str, sku: str, tag_epc: str,
                         uuid: str = None):
        """
        Crea una nueva asignación.

        Si uuid viene informado y ya existe en la tabla, retorna sin duplicar
        (idempotencia para sincronización offline).

        Regla de negocio: si ya existe una asignación activa para ese SKU
        (fecha_devolucion IS NULL), NO se permite reasignar hasta que se reciba
        la prenda. En ese caso se lanza ValueError.
        """
        try:
            # Idempotencia: si ya procesamos esta operación (mismo UUID) no duplicar
            if uuid:
                existing = self.db.execute(
                    text("SELECT asignacion_id FROM asignaciones WHERE uuid = :uuid"),
                    {"uuid": uuid}
                ).fetchone()
                if existing:
                    return

            activa = self.get_asignacion_activa_por_sku(sku)
            if activa:
                # Bloquear reasignación sin recepción previa
                raise ValueError(
                    "La prenda ya está asignada. Debe recibirse antes de poder asignarla nuevamente."
                )

            query = text("""
                INSERT INTO asignaciones (rut, nombre_completo, sku, tag_epc, fecha_entrega, uuid)
                VALUES (:rut, :nombre_completo, :sku, :tag_epc, NOW(), :uuid)
            """)
            self.db.execute(query, {
                "rut": rut,
                "nombre_completo": nombre_completo,
                "sku": sku,
                "tag_epc": tag_epc,
                "uuid": uuid,
            })
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear asignación: {type(e).__name__}: {str(e)}")
            raise

    def get_empleados_con_pendientes(self) -> List[dict]:
        """Retorna empleados con prendas asignadas sin devolver, agrupados por RUT."""
        query = text("""
            SELECT
                a.rut                          AS id,
                a.nombre_completo              AS name,
                COALESCE(e.nombre_empresa, '') AS department,
                COUNT(a.asignacion_id)         AS pending_items
            FROM asignaciones a
            LEFT JOIN personal p ON p.rut = a.rut
            LEFT JOIN empresa e ON e.empresa_id = p.empresa_id
            WHERE a.fecha_devolucion IS NULL
            GROUP BY a.rut, a.nombre_completo, e.nombre_empresa
            ORDER BY a.nombre_completo
        """)
        try:
            result = self.db.execute(query).mappings().fetchall()
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error al obtener empleados con pendientes: {type(e).__name__}: {str(e)}")
            raise

    def get_prendas_pendientes_por_rut(self, rut: str) -> List[dict]:
        """Retorna prendas asignadas sin devolver para un RUT."""
        query = text("""
            SELECT
                a.asignacion_id AS id,
                TRIM(CONCAT(
                    COALESCE(tp.nombre_tipo, ''),
                    CASE WHEN t.nombre_talla IS NOT NULL THEN CONCAT(' ', t.nombre_talla) ELSE '' END
                )) AS name,
                a.sku,
                COALESCE(t.nombre_talla, '') AS size,
                a.fecha_entrega
            FROM asignaciones a
            LEFT JOIN lecturas_rfid lr ON lr.sku = a.sku
            LEFT JOIN tiposprendas tp ON tp.tipo_id = lr.tipo_id
            LEFT JOIN tallas t ON t.talla_id = lr.talla_id
            WHERE a.rut = :rut AND a.fecha_devolucion IS NULL
            ORDER BY a.fecha_entrega DESC
        """)
        try:
            result = self.db.execute(query, {"rut": rut}).mappings().fetchall()
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error al obtener prendas pendientes: {type(e).__name__}: {str(e)}")
            raise

    def procesar_devolucion(self, skus: List[str]):
        """Finaliza asignaciones y marca prendas como disponibles para los SKUs dados."""
        try:
            for sku in skus:
                self.db.execute(
                    text("UPDATE asignaciones SET fecha_devolucion = NOW() WHERE sku = :sku AND fecha_devolucion IS NULL"),
                    {"sku": sku}
                )
                self.db.execute(
                    text("UPDATE lecturas_rfid SET estado_disponible = TRUE, accion = 'DEVOLUCION' WHERE sku = :sku"),
                    {"sku": sku}
                )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al procesar devolución: {type(e).__name__}: {str(e)}")
            raise

    def finalizar_asignacion(self, sku: str):
        """Finaliza (devuelve) la asignación activa de un SKU."""
        query = text("""
            UPDATE asignaciones
            SET fecha_devolucion = NOW()
            WHERE sku = :sku AND fecha_devolucion IS NULL
        """)
        try:
            self.db.execute(query, {"sku": sku})
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al finalizar asignación: {type(e).__name__}: {str(e)}")
            raise

    def get_asignacion_por_id(self, asignacion_id: int):
        """Retorna una asignación por ID, o None si no existe."""
        query = text("""
            SELECT asignacion_id, rut, nombre_completo, sku, tag_epc, fecha_entrega, fecha_devolucion
            FROM asignaciones
            WHERE asignacion_id = :id
        """)
        try:
            row = self.db.execute(query, {"id": asignacion_id}).mappings().fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error al obtener asignación por ID: {type(e).__name__}: {str(e)}")
            raise

    def anular_asignacion(self, asignacion_id: int) -> dict:
        """Anula una asignación activa: marca fecha_devolucion y restaura disponibilidad."""
        asig = self.get_asignacion_por_id(asignacion_id)
        if not asig:
            raise ValueError(f"Asignación {asignacion_id} no encontrada.")
        if asig["fecha_devolucion"] is not None:
            raise ValueError("La asignación ya fue finalizada.")
        sku = asig["sku"]
        try:
            self.db.execute(
                text("UPDATE asignaciones SET fecha_devolucion = NOW() WHERE asignacion_id = :id"),
                {"id": asignacion_id}
            )
            self.db.execute(
                text("UPDATE lecturas_rfid SET estado_disponible = TRUE, accion = 'ANULACION' WHERE sku = :sku"),
                {"sku": sku}
            )
            self.db.commit()
            return asig
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al anular asignación: {type(e).__name__}: {str(e)}")
            raise
