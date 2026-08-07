"""
Repository del flujo de entregas de EPP — SQL crudo con sqlalchemy.text().

Transacciones atómicas: una entrega (o carrito de N líneas) inserta las filas
de entregas_epp + movimientos_stock ENTREGA (negativos) y descuenta stock_epp,
todo en una sola transacción. Si cualquier línea no tiene stock suficiente, se
revierte completa.

Invariante del libro mayor:
  stock_epp.cantidad_actual = SUM(movimientos_stock.cantidad
                                  WHERE tipo IN ('INGRESO_IMPORT','ENTREGA','AJUSTE'))
BAJA_DANO NO afecta el stock del bodegón (documenta la baja de una unidad que ya
estaba en terreno), por eso se registra pero no descuenta stock_epp.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from app.core.logging_config import logger


class EntregasRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Lecturas de apoyo ────────────────────────────────────────────────────

    def get_trabajador(self, rut: str, solo_activos: bool = True) -> Optional[Dict[str, Any]]:
        """
        Busca al trabajador. `solo_activos=False` para consultas de lectura: un
        desvinculado (soft-delete del sync de RRHH) puede tener EPP sin devolver
        y hay que poder verlos, aunque no se le pueda entregar nada nuevo.
        """
        filtro_activo = " AND COALESCE(activo, TRUE) = TRUE" if solo_activos else ""
        row = self.db.execute(
            text(f"""
                SELECT rut, nombre_completo, empresa_id, COALESCE(activo, TRUE) AS activo
                FROM personal
                WHERE rut = :rut{filtro_activo}
            """),
            {"rut": rut},
        ).mappings().fetchone()
        return dict(row) if row else None

    def _get_stock_row(self, producto_id: int, talla_id: Optional[int]) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text("""
                SELECT stock_id, cantidad_actual
                FROM stock_epp
                WHERE producto_id = :producto_id
                  AND talla_id IS NOT DISTINCT FROM :talla_id
            """),
            {"producto_id": producto_id, "talla_id": talla_id},
        ).mappings().fetchone()
        return dict(row) if row else None

    def get_entrega_by_uuid(self, uuid: str) -> Optional[int]:
        row = self.db.execute(
            text("SELECT entrega_id FROM entregas_epp WHERE uuid = :uuid"),
            {"uuid": uuid},
        ).fetchone()
        return row[0] if row else None

    _DETALLE_SELECT = """
        SELECT e.entrega_id, e.rut, e.nombre_completo, e.empresa_id,
               e.producto_id, p.nombre AS nombre_producto,
               e.talla_id, t.nombre_talla,
               e.cantidad, e.motivo, e.entrega_reemplazada_id,
               e.estado_firma, e.usuario_entrega, e.observacion, e.fecha_entrega
        FROM entregas_epp e
        LEFT JOIN productos_epp p ON p.producto_id = e.producto_id
        LEFT JOIN tallas t ON t.talla_id = e.talla_id
    """

    def get_entrega_detalle(self, entrega_id: int) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text(self._DETALLE_SELECT + " WHERE e.entrega_id = :id"),
            {"id": entrega_id},
        ).mappings().fetchone()
        return dict(row) if row else None

    # ── Escritura interna (sin commit) ───────────────────────────────────────

    def _insertar_entrega(self, trabajador: Dict[str, Any], producto_id: int,
                          talla_id: Optional[int], cantidad: int, motivo: str,
                          usuario_id: Optional[int], observacion: Optional[str],
                          uuid: Optional[str],
                          entrega_reemplazada_id: Optional[int] = None) -> int:
        """Inserta una fila de entrega + su movimiento ENTREGA y descuenta stock."""
        stock = self._get_stock_row(producto_id, talla_id)
        disponible = stock["cantidad_actual"] if stock else 0
        if disponible < cantidad:
            raise ValueError(
                f"Stock insuficiente para el producto {producto_id}"
                + (f" (talla {talla_id})" if talla_id else "")
                + f": disponible {disponible}, requerido {cantidad}"
            )

        entrega_id = self.db.execute(
            text("""
                INSERT INTO entregas_epp
                    (rut, nombre_completo, empresa_id, producto_id, talla_id, cantidad,
                     motivo, entrega_reemplazada_id, estado_firma, usuario_entrega,
                     observacion, uuid)
                VALUES
                    (:rut, :nombre_completo, :empresa_id, :producto_id, :talla_id, :cantidad,
                     :motivo, :entrega_reemplazada_id, 'PENDIENTE', :usuario_id,
                     :observacion, :uuid)
                RETURNING entrega_id
            """),
            {
                "rut": trabajador["rut"], "nombre_completo": trabajador["nombre_completo"],
                "empresa_id": trabajador.get("empresa_id"),
                "producto_id": producto_id, "talla_id": talla_id, "cantidad": cantidad,
                "motivo": motivo, "entrega_reemplazada_id": entrega_reemplazada_id,
                "usuario_id": usuario_id, "observacion": observacion, "uuid": uuid,
            },
        ).scalar()

        self.db.execute(
            text("""
                INSERT INTO movimientos_stock
                    (producto_id, talla_id, tipo, cantidad, referencia_id, usuario_id, observacion)
                VALUES
                    (:producto_id, :talla_id, 'ENTREGA', :cantidad, :ref, :usuario_id, :observacion)
            """),
            {
                "producto_id": producto_id, "talla_id": talla_id, "cantidad": -cantidad,
                "ref": entrega_id, "usuario_id": usuario_id, "observacion": observacion,
            },
        )
        self.db.execute(
            text("UPDATE stock_epp SET cantidad_actual = cantidad_actual - :cant WHERE stock_id = :id"),
            {"cant": cantidad, "id": stock["stock_id"]},
        )
        return entrega_id

    # ── Operaciones transaccionales ──────────────────────────────────────────

    def crear_entregas(self, trabajador: Dict[str, Any], lineas: List[Dict[str, Any]],
                       usuario_id: Optional[int]) -> List[Dict[str, Any]]:
        """
        Carrito de N líneas (motivos NUEVA/PERDIDA) en una sola transacción.

        Una línea PERDIDA puede vincular la entrega que se dio por perdida
        (`entrega_reemplazada_id`): así deja de contar como vigente. No genera
        BAJA_DANO — el ítem perdido no vuelve al bodegón y su stock ya se
        descontó cuando se entregó.
        """
        try:
            creadas: List[int] = []
            for linea in lineas:
                uuid = linea.get("uuid")
                if uuid:
                    existente = self.get_entrega_by_uuid(uuid)
                    if existente:
                        creadas.append(existente)   # idempotencia offline
                        continue
                reemplazada_id = linea.get("entrega_reemplazada_id")
                if reemplazada_id is not None:
                    self.get_entrega_reemplazable(reemplazada_id, trabajador["rut"])
                entrega_id = self._insertar_entrega(
                    trabajador=trabajador,
                    producto_id=linea["producto_id"],
                    talla_id=linea.get("talla_id"),
                    cantidad=linea["cantidad"],
                    motivo=linea["motivo"],
                    usuario_id=usuario_id,
                    observacion=linea.get("observacion"),
                    uuid=uuid,
                    entrega_reemplazada_id=reemplazada_id,
                )
                creadas.append(entrega_id)
            self.db.commit()
            return [self.get_entrega_detalle(i) for i in creadas]
        except Exception as e:
            self.db.rollback()
            if not isinstance(e, ValueError):
                logger.error(f"Error al crear entregas: {type(e).__name__}: {str(e)}")
            raise

    def get_entrega_reemplazable(self, entrega_id: int, rut: str) -> Dict[str, Any]:
        """Valida que la entrega exista, sea del trabajador y esté vigente."""
        reemplazada = self.db.execute(
            text("SELECT entrega_id, rut, producto_id, talla_id, cantidad FROM entregas_epp WHERE entrega_id = :id"),
            {"id": entrega_id},
        ).mappings().fetchone()
        if not reemplazada:
            raise ValueError("La entrega a reemplazar no existe")
        if reemplazada["rut"] != rut:
            raise ValueError("La entrega a reemplazar no pertenece a este trabajador")
        ya_reemplazada = self.db.execute(
            text("SELECT 1 FROM entregas_epp WHERE entrega_reemplazada_id = :id LIMIT 1"),
            {"id": entrega_id},
        ).fetchone()
        if ya_reemplazada:
            raise ValueError("Esa entrega ya fue reemplazada anteriormente")
        return dict(reemplazada)

    def crear_sustitucion(self, trabajador: Dict[str, Any], entrega_reemplazada_id: int,
                          producto_id: int, talla_id: Optional[int], cantidad: int,
                          observacion: Optional[str], usuario_id: Optional[int],
                          uuid: Optional[str]) -> Dict[str, Any]:
        """
        Sustitución por daño (motivo DANO), transacción única:
          - entrega nueva vinculada a la reemplazada (descuenta stock)
          - movimiento BAJA_DANO del ítem dañado (traza, sin afectar stock)
        """
        try:
            if uuid:
                existente = self.get_entrega_by_uuid(uuid)
                if existente:
                    return self.get_entrega_detalle(existente)   # idempotencia

            reemplazada = self.get_entrega_reemplazable(entrega_reemplazada_id, trabajador["rut"])

            entrega_id = self._insertar_entrega(
                trabajador=trabajador, producto_id=producto_id, talla_id=talla_id,
                cantidad=cantidad, motivo="DANO", usuario_id=usuario_id,
                observacion=observacion, uuid=uuid,
                entrega_reemplazada_id=entrega_reemplazada_id,
            )

            # Baja del ítem dañado (unidad en terreno) — no afecta stock del bodegón.
            self.db.execute(
                text("""
                    INSERT INTO movimientos_stock
                        (producto_id, talla_id, tipo, cantidad, referencia_id, usuario_id, observacion)
                    VALUES
                        (:producto_id, :talla_id, 'BAJA_DANO', :cantidad, :ref, :usuario_id, :observacion)
                """),
                {
                    "producto_id": reemplazada["producto_id"], "talla_id": reemplazada["talla_id"],
                    "cantidad": -reemplazada["cantidad"], "ref": entrega_reemplazada_id,
                    "usuario_id": usuario_id,
                    "observacion": observacion or f"Baja por daño (reemplaza entrega {entrega_reemplazada_id})",
                },
            )
            self.db.commit()
            return self.get_entrega_detalle(entrega_id)
        except Exception as e:
            self.db.rollback()
            if not isinstance(e, ValueError):
                logger.error(f"Error al crear sustitución: {type(e).__name__}: {str(e)}")
            raise

    # ── Consultas ────────────────────────────────────────────────────────────

    def get_entregas(self, rut: Optional[str] = None, motivo: Optional[str] = None,
                     area_id: Optional[int] = None, desde: Optional[str] = None,
                     hasta: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
        sql = self._DETALLE_SELECT + " LEFT JOIN personal per ON per.rut = e.rut WHERE 1=1"
        params: Dict[str, Any] = {}
        if rut:
            sql += " AND e.rut = :rut"
            params["rut"] = rut
        if motivo:
            sql += " AND e.motivo = :motivo"
            params["motivo"] = motivo
        if area_id is not None:
            sql += " AND per.area_id = :area_id"
            params["area_id"] = area_id
        if desde:
            sql += " AND e.fecha_entrega >= :desde"
            params["desde"] = desde
        if hasta:
            sql += " AND e.fecha_entrega <= :hasta"
            params["hasta"] = hasta
        sql += " ORDER BY e.fecha_entrega DESC, e.entrega_id DESC LIMIT :limit"
        params["limit"] = limit
        result = self.db.execute(text(sql), params).mappings().fetchall()
        return [dict(r) for r in result]

    def get_vigentes_por_rut(self, rut: str) -> List[Dict[str, Any]]:
        """EPP vigentes del trabajador: entregas no reemplazadas por una sustitución."""
        sql = self._DETALLE_SELECT + """
            WHERE e.rut = :rut
              AND NOT EXISTS (
                  SELECT 1 FROM entregas_epp r WHERE r.entrega_reemplazada_id = e.entrega_id
              )
            ORDER BY e.fecha_entrega DESC, e.entrega_id DESC
        """
        result = self.db.execute(text(sql), {"rut": rut}).mappings().fetchall()
        return [dict(r) for r in result]
