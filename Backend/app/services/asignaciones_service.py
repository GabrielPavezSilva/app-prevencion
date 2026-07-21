from sqlalchemy.orm import Session
from typing import List
from app.repositories.asignaciones_repository import AsignacionesRepository
from app.schemas.asignaciones import AsignacionesResponse
#from app.core.exceptions import InventarioNotFoundError
import logging

logger = logging.getLogger(__name__)

class AsignacionesService:
    def __init__(self, db: Session):
        self.repository = AsignacionesRepository(db)

    def obtener_asignaciones(self) -> List[AsignacionesResponse]:
        logger.info(f"Obteniendo asignaciones completas")
        return self.repository.get_asignaciones()

    def obtener_empleados_con_pendientes(self) -> List[dict]:
        logger.info("Obteniendo empleados con devoluciones pendientes")
        empleados = self.repository.get_empleados_con_pendientes()
        return [
            {
                "id": e["id"],
                "name": e["name"],
                "department": e["department"],
                "status": "ACTIVO",
                "returnStatus": "PENDIENTE",
                "pendingItems": e["pending_items"],
                "expirationDate": "—",
            }
            for e in empleados
        ]

    def obtener_prendas_pendientes(self, rut: str) -> dict:
        logger.info(f"Obteniendo prendas pendientes para RUT={rut}")
        items = self.repository.get_prendas_pendientes_por_rut(rut)
        return {
            "items": [
                {
                    "id": item["id"],
                    "name": item["name"] or "Prenda",
                    "sku": item["sku"],
                    "size": item["size"],
                    "fecha_entrega": item.get("fecha_entrega"),
                    "quantityRequested": 1,
                    "quantityReturned": 0,
                    "status": "",
                }
                for item in items
            ]
        }

    def anular_asignacion(self, asignacion_id: int, usuario_id: int, usuario_nombre: str) -> dict:
        """Anula asignación por error. Restaura disponibilidad y registra auditoría."""
        from app.repositories.auditoria_repository import AuditoriaRepository
        logger.info(f"Anulando asignación {asignacion_id} por usuario {usuario_nombre}")
        auditoria_repo = AuditoriaRepository(self.repository.db)
        asig = self.repository.anular_asignacion(asignacion_id)
        auditoria_repo.registrar_auditoria(
            sku=asig["sku"],
            accion="ANULACION_ASIGNACION",
            usuario_id=usuario_id,
            usuario_nombre=usuario_nombre,
            detalle={
                "asignacion_id": asignacion_id,
                "rut": asig["rut"],
                "nombre_completo": asig["nombre_completo"],
                "sku": asig["sku"],
                "fecha_entrega": str(asig["fecha_entrega"]),
            },
        )
        return {"anulada": True, "sku": asig["sku"], "asignacion_id": asignacion_id}

    def anular_asignacion_por_sku(self, sku: str, usuario_id: int, usuario_nombre: str) -> dict:
        """Anula la asignación activa de un SKU (corrección in-situ). Reusa anular_asignacion."""
        activa = self.repository.get_asignacion_activa_por_sku(sku)
        if not activa:
            raise ValueError(f"No hay asignación activa para el SKU {sku}.")
        return self.anular_asignacion(activa["asignacion_id"], usuario_id, usuario_nombre)

    def procesar_devolucion(self, employee_id: str, items: list) -> dict:
        logger.info(f"Procesando devolución para RUT={employee_id}")
        skus = [item["sku"] for item in items if item.get("quantityReturned", 0) > 0]
        if not skus:
            return {"devueltas": 0}
        self.repository.procesar_devolucion(skus)
        return {"devueltas": len(skus)}