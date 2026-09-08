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
from app.services.acta_pdf import construir_acta
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
        filtro_activo = " AND COALESCE(p.activo, TRUE) = TRUE" if solo_activos else ""
        row = self.db.execute(
            text(f"""
                SELECT p.rut, p.nombre_completo, p.empresa_id, p.cargo,
                       e.nombre_empresa AS empresa,
                       a.nombre_area,
                       COALESCE(p.activo, TRUE) AS activo
                FROM personal p
                LEFT JOIN empresa e ON e.empresa_id = p.empresa_id
                LEFT JOIN areas a ON a.area_id = p.area_id
                WHERE p.rut = :rut{filtro_activo}
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
               c.nombre_categoria, p.vida_util_meses,
               e.talla_id, t.nombre_talla,
               e.cantidad, e.motivo, e.entrega_reemplazada_id,
               e.estado_firma, e.acta_id, e.usuario_entrega, e.observacion, e.fecha_entrega
        FROM entregas_epp e
        LEFT JOIN productos_epp p ON p.producto_id = e.producto_id
        LEFT JOIN categorias_epp c ON c.categoria_id = p.categoria_id
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

    def crear_acta(self, trabajador: Dict[str, Any], entrega_ids: List[int],
                   pdf: bytes, usuario_id: Optional[int],
                   firma: Optional[bytes] = None) -> int:
        """
        Guarda el acta firmada y la vincula a las entregas del carrito.

        Sin commit: la llama `crear_entregas` dentro de su transacción, para que
        no pueda quedar una entrega registrada sin su acta ni al revés.
        """
        acta_id = self.db.execute(
            text("""
                INSERT INTO actas_entrega (rut, nombre_completo, empresa_id, pdf, firma, usuario_id)
                VALUES (:rut, :nombre_completo, :empresa_id, :pdf, :firma, :usuario_id)
                RETURNING acta_id
            """),
            {
                "rut": trabajador["rut"], "nombre_completo": trabajador["nombre_completo"],
                "empresa_id": trabajador.get("empresa_id"), "pdf": pdf, "firma": firma,
                "usuario_id": usuario_id,
            },
        ).scalar()
        self.db.execute(
            text("""
                UPDATE entregas_epp SET acta_id = :acta_id, estado_firma = 'FIRMADA'
                WHERE entrega_id = ANY(:ids)
            """),
            {"acta_id": acta_id, "ids": entrega_ids},
        )
        return acta_id

    def get_entregas_firmadas(self, rut: str) -> List[Dict[str, Any]]:
        """
        Filas del documento maestro del trabajador: todas sus entregas con acta
        firmada, en orden cronológico, cada una con la firma de su acta.

        Las entregas sin acta (carga histórica por importación) quedan fuera:
        el maestro es el respaldo firmado, no el historial completo.
        """
        filas = self.db.execute(
            text("""
                SELECT e.entrega_id, p.nombre AS nombre_producto, c.nombre_categoria,
                       p.vida_util_meses, t.nombre_talla, e.cantidad, e.motivo,
                       -- la base guarda UTC y el acta se lee en Chile
                       ((e.fecha_entrega AT TIME ZONE 'UTC')
                            AT TIME ZONE 'America/Santiago') AS fecha_entrega,
                       a.firma
                FROM entregas_epp e
                JOIN actas_entrega a ON a.acta_id = e.acta_id
                LEFT JOIN productos_epp p ON p.producto_id = e.producto_id
                LEFT JOIN categorias_epp c ON c.categoria_id = p.categoria_id
                LEFT JOIN tallas t ON t.talla_id = e.talla_id
                WHERE e.rut = :rut
                ORDER BY e.fecha_entrega, e.entrega_id
            """),
            {"rut": rut},
        ).mappings().fetchall()
        return [dict(f) for f in filas]

    def get_acta_pdf(self, acta_id: int) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text("SELECT acta_id, rut, nombre_completo, pdf, fecha_creacion "
                 "FROM actas_entrega WHERE acta_id = :id"),
            {"id": acta_id},
        ).mappings().fetchone()
        return dict(row) if row else None

    def crear_entregas(self, trabajador: Dict[str, Any], lineas: List[Dict[str, Any]],
                       usuario_id: Optional[int],
                       firma_png: Optional[bytes] = None) -> List[Dict[str, Any]]:
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
            detalles = [self.get_entrega_detalle(i) for i in creadas]
            # El acta se arma con las filas ya persistidas: así el PDF muestra
            # exactamente lo que quedó en la base, nombres de producto y talla
            # incluidos. `firma_png` es opcional solo para los seeds y smokes;
            # el endpoint la exige.
            if firma_png:
                acta_id = self.crear_acta(trabajador, creadas,
                                          construir_acta(trabajador, detalles, firma_png),
                                          usuario_id, firma_png)
                for d in detalles:
                    d["acta_id"] = acta_id
                    d["estado_firma"] = "FIRMADA"
            self.db.commit()
            return detalles
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
                          uuid: Optional[str],
                          firma_png: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Sustitución por daño (motivo DANO), transacción única:
          - entrega nueva vinculada a la reemplazada (descuenta stock)
          - movimiento BAJA_DANO del ítem dañado (traza, sin afectar stock)
          - acta firmada de la entrega de reemplazo

        `firma_png` es opcional solo para seeds y smokes; el endpoint la exige.
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
            detalle = self.get_entrega_detalle(entrega_id)
            if firma_png:
                acta_id = self.crear_acta(
                    trabajador, [entrega_id], construir_acta(trabajador, [detalle], firma_png),
                    usuario_id, firma_png)
                detalle["acta_id"] = acta_id
                detalle["estado_firma"] = "FIRMADA"
            self.db.commit()
            return detalle
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
