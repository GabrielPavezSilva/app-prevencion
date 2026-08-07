"""
Repository de importaciones EPP — primitivas SIN commit (el service las envuelve
en savepoints por fila y hace un único commit al final).

Todo ingreso de stock (stock_inicial / ingreso_stock) es ADITIVO y genera un
movimiento INGRESO_IMPORT, manteniendo la invariante del libro mayor. Las
entregas históricas NO afectan el stock actual (son registro de migración).
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any, List
from datetime import datetime


class ImportacionesRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Resolvers de catálogo ────────────────────────────────────────────────

    def get_categoria_id(self, nombre: str) -> Optional[int]:
        row = self.db.execute(
            text("SELECT categoria_id FROM categorias_epp WHERE LOWER(nombre_categoria) = LOWER(:n)"),
            {"n": nombre},
        ).fetchone()
        return row[0] if row else None

    def crear_categoria(self, nombre: str) -> int:
        return self.db.execute(
            text("INSERT INTO categorias_epp (nombre_categoria) VALUES (:n) RETURNING categoria_id"),
            {"n": nombre},
        ).scalar()

    def get_producto(self, nombre: str) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text("SELECT producto_id, nombre, talla_aplica, activo FROM productos_epp WHERE LOWER(nombre) = LOWER(:n)"),
            {"n": nombre},
        ).mappings().fetchone()
        return dict(row) if row else None

    def crear_producto(self, nombre: str, categoria_id: Optional[int],
                       talla_aplica: bool, certificacion: Optional[str]) -> int:
        return self.db.execute(
            text("""
                INSERT INTO productos_epp (nombre, categoria_id, talla_aplica, certificacion, activo)
                VALUES (:nombre, :categoria_id, :talla_aplica, :certificacion, TRUE)
                RETURNING producto_id
            """),
            {"nombre": nombre, "categoria_id": categoria_id,
             "talla_aplica": talla_aplica, "certificacion": certificacion},
        ).scalar()

    def get_talla_id(self, nombre: str) -> Optional[int]:
        row = self.db.execute(
            text("SELECT talla_id FROM tallas WHERE LOWER(nombre_talla) = LOWER(:n)"),
            {"n": nombre},
        ).fetchone()
        return row[0] if row else None

    def get_trabajador(self, rut: str) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text("SELECT rut, nombre_completo, empresa_id FROM personal WHERE rut = :rut"),
            {"rut": rut},
        ).mappings().fetchone()
        return dict(row) if row else None

    # ── Operaciones de stock (aditivas, sin commit) ──────────────────────────

    def ingresar_stock(self, producto_id: int, talla_id: Optional[int], cantidad: int,
                       stock_minimo: Optional[int], usuario_id: Optional[int],
                       observacion: Optional[str]) -> None:
        stock = self.db.execute(
            text("""
                SELECT stock_id, cantidad_actual FROM stock_epp
                WHERE producto_id = :p AND talla_id IS NOT DISTINCT FROM :t
            """),
            {"p": producto_id, "t": talla_id},
        ).mappings().fetchone()

        if stock:
            self.db.execute(
                text("""
                    UPDATE stock_epp
                    SET cantidad_actual = cantidad_actual + :cant,
                        stock_minimo = COALESCE(:sm, stock_minimo)
                    WHERE stock_id = :id
                """),
                {"cant": cantidad, "sm": stock_minimo, "id": stock["stock_id"]},
            )
        else:
            self.db.execute(
                text("""
                    INSERT INTO stock_epp (producto_id, talla_id, cantidad_actual, stock_minimo)
                    VALUES (:p, :t, :cant, COALESCE(:sm, 0))
                """),
                {"p": producto_id, "t": talla_id, "cant": cantidad, "sm": stock_minimo},
            )

        self.db.execute(
            text("""
                INSERT INTO movimientos_stock
                    (producto_id, talla_id, tipo, cantidad, usuario_id, observacion)
                VALUES (:p, :t, 'INGRESO_IMPORT', :cant, :u, :obs)
            """),
            {"p": producto_id, "t": talla_id, "cant": cantidad, "u": usuario_id, "obs": observacion},
        )

    def insertar_entrega_historica(self, trabajador: Dict[str, Any], producto_id: int,
                                   talla_id: Optional[int], cantidad: int, motivo: str,
                                   fecha: datetime, usuario_id: Optional[int]) -> None:
        self.db.execute(
            text("""
                INSERT INTO entregas_epp
                    (rut, nombre_completo, empresa_id, producto_id, talla_id, cantidad,
                     motivo, estado_firma, usuario_entrega, fecha_entrega)
                VALUES
                    (:rut, :nombre, :empresa_id, :producto_id, :talla_id, :cantidad,
                     :motivo, 'PENDIENTE', :usuario_id, :fecha)
            """),
            {
                "rut": trabajador["rut"], "nombre": trabajador["nombre_completo"],
                "empresa_id": trabajador.get("empresa_id"), "producto_id": producto_id,
                "talla_id": talla_id, "cantidad": cantidad, "motivo": motivo,
                "usuario_id": usuario_id, "fecha": fecha,
            },
        )

    # ── Registro de la importación (sin commit) ──────────────────────────────

    def registrar_importacion(self, template_id: str, nombre_archivo: str,
                              filas_ok: int, filas_error: int,
                              detalle_errores: Optional[str], usuario_id: Optional[int]) -> int:
        return self.db.execute(
            text("""
                INSERT INTO importaciones
                    (template_id, nombre_archivo, filas_ok, filas_error, detalle_errores, usuario_id)
                VALUES (:tid, :arch, :ok, :err, :detalle, :usuario_id)
                RETURNING importacion_id
            """),
            {"tid": template_id, "arch": nombre_archivo, "ok": filas_ok,
             "err": filas_error, "detalle": detalle_errores, "usuario_id": usuario_id},
        ).scalar()

    def listar_importaciones(self, limit: int = 100) -> List[Dict[str, Any]]:
        result = self.db.execute(
            text("""
                SELECT importacion_id, template_id, nombre_archivo, filas_ok, filas_error,
                       detalle_errores, usuario_id, fecha
                FROM importaciones
                ORDER BY fecha DESC, importacion_id DESC
                LIMIT :limit
            """),
            {"limit": limit},
        ).mappings().fetchall()
        return [dict(r) for r in result]
