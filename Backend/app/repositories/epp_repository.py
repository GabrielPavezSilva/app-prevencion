"""
Repository del dominio EPP — SQL crudo con sqlalchemy.text() (PostgreSQL).

Nota sobre stock y talla_id NULL:
  El UNIQUE(producto_id, talla_id) de stock_epp NO impide filas duplicadas
  cuando talla_id es NULL (en PostgreSQL NULL != NULL en índices únicos). Por
  eso los lookups usan `talla_id IS NOT DISTINCT FROM :talla_id`, que trata
  NULL = NULL, y el upsert es explícito (SELECT → INSERT/UPDATE).
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from app.core.logging_config import logger


class EppRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Categorías ───────────────────────────────────────────────────────────

    def get_all_categorias(self) -> List[Dict[str, Any]]:
        result = self.db.execute(
            text("SELECT categoria_id, nombre_categoria FROM categorias_epp ORDER BY nombre_categoria")
        )
        return [dict(r) for r in result.mappings().fetchall()]

    def get_categoria_by_id(self, categoria_id: int) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text("SELECT categoria_id, nombre_categoria FROM categorias_epp WHERE categoria_id = :id"),
            {"id": categoria_id},
        ).mappings().fetchone()
        return dict(row) if row else None

    def get_categoria_by_nombre(self, nombre: str) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text("SELECT categoria_id, nombre_categoria FROM categorias_epp WHERE LOWER(nombre_categoria) = LOWER(:nombre)"),
            {"nombre": nombre},
        ).mappings().fetchone()
        return dict(row) if row else None

    def categoria_tiene_productos(self, categoria_id: int) -> bool:
        total = self.db.execute(
            text("SELECT COUNT(*) FROM productos_epp WHERE categoria_id = :id"),
            {"id": categoria_id},
        ).scalar()
        return total > 0

    def create_categoria(self, nombre: str) -> Dict[str, Any]:
        try:
            new_id = self.db.execute(
                text("INSERT INTO categorias_epp (nombre_categoria) VALUES (:nombre) RETURNING categoria_id"),
                {"nombre": nombre},
            ).scalar()
            self.db.commit()
            return {"categoria_id": new_id, "nombre_categoria": nombre}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear categoría EPP: {type(e).__name__}: {str(e)}")
            raise

    def update_categoria(self, categoria_id: int, nombre: str) -> Dict[str, Any]:
        try:
            self.db.execute(
                text("UPDATE categorias_epp SET nombre_categoria = :nombre WHERE categoria_id = :id"),
                {"nombre": nombre, "id": categoria_id},
            )
            self.db.commit()
            return {"categoria_id": categoria_id, "nombre_categoria": nombre}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar categoría EPP: {type(e).__name__}: {str(e)}")
            raise

    def delete_categoria(self, categoria_id: int) -> None:
        try:
            self.db.execute(
                text("DELETE FROM categorias_epp WHERE categoria_id = :id"),
                {"id": categoria_id},
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar categoría EPP: {type(e).__name__}: {str(e)}")
            raise

    # ── Productos ────────────────────────────────────────────────────────────

    _PRODUCTO_SELECT = """
        SELECT p.producto_id, p.nombre, p.categoria_id, c.nombre_categoria,
               p.talla_aplica, p.certificacion, p.descripcion, p.activo
        FROM productos_epp p
        LEFT JOIN categorias_epp c ON c.categoria_id = p.categoria_id
    """

    def get_all_productos(self, categoria_id: Optional[int] = None,
                          activo: Optional[bool] = None,
                          search: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = self._PRODUCTO_SELECT + " WHERE 1=1"
        params: Dict[str, Any] = {}
        if categoria_id is not None:
            sql += " AND p.categoria_id = :categoria_id"
            params["categoria_id"] = categoria_id
        if activo is not None:
            sql += " AND p.activo = :activo"
            params["activo"] = activo
        if search:
            sql += " AND p.nombre ILIKE :search"
            params["search"] = f"%{search}%"
        sql += " ORDER BY p.nombre"
        result = self.db.execute(text(sql), params).mappings().fetchall()
        return [dict(r) for r in result]

    def get_producto_by_id(self, producto_id: int) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text(self._PRODUCTO_SELECT + " WHERE p.producto_id = :id"),
            {"id": producto_id},
        ).mappings().fetchone()
        return dict(row) if row else None

    def get_producto_by_nombre(self, nombre: str) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text("SELECT producto_id, nombre FROM productos_epp WHERE LOWER(nombre) = LOWER(:nombre)"),
            {"nombre": nombre},
        ).mappings().fetchone()
        return dict(row) if row else None

    def producto_tiene_dependencias(self, producto_id: int) -> bool:
        """True si el producto está referenciado en stock, movimientos o entregas."""
        total = self.db.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM stock_epp WHERE producto_id = :id)
                  + (SELECT COUNT(*) FROM movimientos_stock WHERE producto_id = :id)
                  + (SELECT COUNT(*) FROM entregas_epp WHERE producto_id = :id)
            """),
            {"id": producto_id},
        ).scalar()
        return total > 0

    def create_producto(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            new_id = self.db.execute(
                text("""
                    INSERT INTO productos_epp
                        (nombre, categoria_id, talla_aplica, certificacion, descripcion, activo)
                    VALUES
                        (:nombre, :categoria_id, :talla_aplica, :certificacion, :descripcion, TRUE)
                    RETURNING producto_id
                """),
                data,
            ).scalar()
            self.db.commit()
            return self.get_producto_by_id(new_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear producto EPP: {type(e).__name__}: {str(e)}")
            raise

    def update_producto(self, producto_id: int, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Actualización parcial: solo columnas informadas (whitelist)."""
        permitidas = {"nombre", "categoria_id", "talla_aplica", "certificacion", "descripcion", "activo"}
        sets = [f"{col} = :{col}" for col in fields if col in permitidas]
        if not sets:
            return self.get_producto_by_id(producto_id)
        params = {col: fields[col] for col in fields if col in permitidas}
        params["id"] = producto_id
        try:
            self.db.execute(
                text(f"UPDATE productos_epp SET {', '.join(sets)} WHERE producto_id = :id"),
                params,
            )
            self.db.commit()
            return self.get_producto_by_id(producto_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar producto EPP: {type(e).__name__}: {str(e)}")
            raise

    def delete_producto(self, producto_id: int) -> None:
        try:
            self.db.execute(
                text("DELETE FROM productos_epp WHERE producto_id = :id"),
                {"id": producto_id},
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar producto EPP: {type(e).__name__}: {str(e)}")
            raise

    # ── Stock ────────────────────────────────────────────────────────────────

    def get_stock(self, producto_id: Optional[int] = None,
                  categoria_id: Optional[int] = None,
                  bajo_minimo: bool = False) -> List[Dict[str, Any]]:
        sql = """
            SELECT s.stock_id, s.producto_id, p.nombre AS nombre_producto,
                   p.categoria_id, c.nombre_categoria,
                   s.talla_id, t.nombre_talla,
                   s.cantidad_actual, s.stock_minimo,
                   (s.cantidad_actual <= s.stock_minimo) AS bajo_minimo
            FROM stock_epp s
            JOIN productos_epp p ON p.producto_id = s.producto_id
            LEFT JOIN categorias_epp c ON c.categoria_id = p.categoria_id
            LEFT JOIN tallas t ON t.talla_id = s.talla_id
            WHERE 1=1
        """
        params: Dict[str, Any] = {}
        if producto_id is not None:
            sql += " AND s.producto_id = :producto_id"
            params["producto_id"] = producto_id
        if categoria_id is not None:
            sql += " AND p.categoria_id = :categoria_id"
            params["categoria_id"] = categoria_id
        if bajo_minimo:
            sql += " AND s.cantidad_actual <= s.stock_minimo"
        sql += " ORDER BY p.nombre, t.nombre_talla"
        result = self.db.execute(text(sql), params).mappings().fetchall()
        return [dict(r) for r in result]

    def get_stock_row(self, producto_id: int, talla_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """Fila cruda de stock (columnas mínimas) para lógica de upsert."""
        row = self.db.execute(
            text("""
                SELECT stock_id, producto_id, talla_id, cantidad_actual, stock_minimo
                FROM stock_epp
                WHERE producto_id = :producto_id
                  AND talla_id IS NOT DISTINCT FROM :talla_id
            """),
            {"producto_id": producto_id, "talla_id": talla_id},
        ).mappings().fetchone()
        return dict(row) if row else None

    def get_stock_detalle(self, producto_id: int, talla_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """Fila de stock enriquecida (nombres + bajo_minimo), forma StockResponse."""
        row = self.db.execute(
            text("""
                SELECT s.stock_id, s.producto_id, p.nombre AS nombre_producto,
                       p.categoria_id, c.nombre_categoria,
                       s.talla_id, t.nombre_talla,
                       s.cantidad_actual, s.stock_minimo,
                       (s.cantidad_actual <= s.stock_minimo) AS bajo_minimo
                FROM stock_epp s
                JOIN productos_epp p ON p.producto_id = s.producto_id
                LEFT JOIN categorias_epp c ON c.categoria_id = p.categoria_id
                LEFT JOIN tallas t ON t.talla_id = s.talla_id
                WHERE s.producto_id = :producto_id
                  AND s.talla_id IS NOT DISTINCT FROM :talla_id
            """),
            {"producto_id": producto_id, "talla_id": talla_id},
        ).mappings().fetchone()
        return dict(row) if row else None

    def ajustar_stock(self, producto_id: int, talla_id: Optional[int],
                      cantidad_nueva: int, observacion: str,
                      usuario_id: Optional[int]) -> Dict[str, Any]:
        """
        Fija el stock a un valor absoluto en una transacción atómica:
          1. Upsert de la fila de stock_epp (crea si no existe).
          2. Registra un MovimientoStock tipo AJUSTE con el delta.
        Devuelve la fila de stock resultante.
        """
        try:
            actual = self.get_stock_row(producto_id, talla_id)
            cantidad_anterior = actual["cantidad_actual"] if actual else 0
            delta = cantidad_nueva - cantidad_anterior

            if actual:
                self.db.execute(
                    text("UPDATE stock_epp SET cantidad_actual = :cant WHERE stock_id = :id"),
                    {"cant": cantidad_nueva, "id": actual["stock_id"]},
                )
            else:
                self.db.execute(
                    text("""
                        INSERT INTO stock_epp (producto_id, talla_id, cantidad_actual, stock_minimo)
                        VALUES (:producto_id, :talla_id, :cant, 0)
                    """),
                    {"producto_id": producto_id, "talla_id": talla_id, "cant": cantidad_nueva},
                )

            self.db.execute(
                text("""
                    INSERT INTO movimientos_stock
                        (producto_id, talla_id, tipo, cantidad, usuario_id, observacion)
                    VALUES
                        (:producto_id, :talla_id, 'AJUSTE', :delta, :usuario_id, :observacion)
                """),
                {
                    "producto_id": producto_id, "talla_id": talla_id, "delta": delta,
                    "usuario_id": usuario_id, "observacion": observacion,
                },
            )
            self.db.commit()
            return self.get_stock_detalle(producto_id, talla_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al ajustar stock: {type(e).__name__}: {str(e)}")
            raise

    # ── Movimientos ──────────────────────────────────────────────────────────

    def get_movimientos(self, producto_id: Optional[int] = None,
                        tipo: Optional[str] = None,
                        desde: Optional[str] = None,
                        hasta: Optional[str] = None,
                        limit: int = 200) -> List[Dict[str, Any]]:
        sql = """
            SELECT m.movimiento_id, m.producto_id, p.nombre AS nombre_producto,
                   m.talla_id, t.nombre_talla,
                   m.tipo, m.cantidad, m.referencia_id, m.usuario_id,
                   m.observacion, m.fecha
            FROM movimientos_stock m
            LEFT JOIN productos_epp p ON p.producto_id = m.producto_id
            LEFT JOIN tallas t ON t.talla_id = m.talla_id
            WHERE 1=1
        """
        params: Dict[str, Any] = {}
        if producto_id is not None:
            sql += " AND m.producto_id = :producto_id"
            params["producto_id"] = producto_id
        if tipo:
            sql += " AND m.tipo = :tipo"
            params["tipo"] = tipo
        if desde:
            sql += " AND m.fecha >= :desde"
            params["desde"] = desde
        if hasta:
            sql += " AND m.fecha <= :hasta"
            params["hasta"] = hasta
        sql += " ORDER BY m.fecha DESC, m.movimiento_id DESC LIMIT :limit"
        params["limit"] = limit
        result = self.db.execute(text(sql), params).mappings().fetchall()
        return [dict(r) for r in result]
