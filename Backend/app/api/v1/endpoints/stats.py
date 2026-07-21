from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.schemas.stats import InventarioStatsResponse
from app.db.deps import get_mysql_db
from app.core.security import require_module

router = APIRouter()


@router.get("/inventario", response_model=InventarioStatsResponse)
async def get_stats_inventario(
    db: Session = Depends(get_mysql_db),
    _: dict = Depends(require_module("dashboard")),
    tipo_id: Optional[int] = Query(default=None),
    talla_id: Optional[int] = Query(default=None),
    empresa_id: Optional[int] = Query(default=None),
    seccion_id: Optional[int] = Query(default=None),
    temporada_id: Optional[int] = Query(default=None),
):
    """Retorna estadísticas agregadas del inventario (lecturas_rfid) para el panel de control."""

    filtros_base = {
        "tipo_id": tipo_id, "talla_id": talla_id,
        "empresa_id": empresa_id, "seccion_id": seccion_id, "temporada_id": temporada_id,
    }

    resumen = db.execute(text("""
        SELECT
            COUNT(*)                                                                  AS total,
            SUM(CASE WHEN estado_disponible = true  THEN 1 ELSE 0 END)               AS disponibles,
            SUM(CASE WHEN tag_epc IS NOT NULL AND tag_epc != '' THEN 1 ELSE 0 END)   AS con_rfid,
            SUM(CASE WHEN tag_epc IS NULL OR tag_epc = ''  THEN 1 ELSE 0 END)        AS sin_rfid
        FROM lecturas_rfid
        WHERE (:tipo_id      IS NULL OR tipo_id      = :tipo_id)
          AND (:talla_id     IS NULL OR talla_id     = :talla_id)
          AND (:empresa_id   IS NULL OR empresa_id   = :empresa_id)
          AND (:seccion_id   IS NULL OR seccion_id   = :seccion_id)
          AND (:temporada_id IS NULL OR temporada_id = :temporada_id)
    """), filtros_base).mappings().fetchone()

    asignadas_row = db.execute(text("""
        SELECT COUNT(*) AS en_uso
        FROM asignaciones a
        JOIN lecturas_rfid lr ON lr.sku = a.sku
        WHERE a.fecha_devolucion IS NULL
          AND (:tipo_id      IS NULL OR lr.tipo_id      = :tipo_id)
          AND (:talla_id     IS NULL OR lr.talla_id     = :talla_id)
          AND (:empresa_id   IS NULL OR lr.empresa_id   = :empresa_id)
          AND (:seccion_id   IS NULL OR lr.seccion_id   = :seccion_id)
          AND (:temporada_id IS NULL OR lr.temporada_id = :temporada_id)
    """), filtros_base).mappings().fetchone()
    en_uso = asignadas_row["en_uso"] if asignadas_row else 0

    # Cada gráfico excluye su propio filtro para mostrar distribución completa
    tipos_rows = db.execute(text("""
        SELECT t.nombre_tipo AS nombre, COUNT(*) AS cantidad
        FROM lecturas_rfid lr
        JOIN tiposprendas t ON lr.tipo_id = t.tipo_id
        WHERE (:talla_id     IS NULL OR lr.talla_id     = :talla_id)
          AND (:empresa_id   IS NULL OR lr.empresa_id   = :empresa_id)
          AND (:seccion_id   IS NULL OR lr.seccion_id   = :seccion_id)
          AND (:temporada_id IS NULL OR lr.temporada_id = :temporada_id)
        GROUP BY t.tipo_id, t.nombre_tipo
        ORDER BY cantidad DESC
    """), {k: v for k, v in filtros_base.items() if k != "tipo_id"}).mappings().fetchall()

    tallas_rows = db.execute(text("""
        SELECT ta.nombre_talla AS nombre, COUNT(*) AS cantidad
        FROM lecturas_rfid lr
        JOIN tallas ta ON lr.talla_id = ta.talla_id
        WHERE (:tipo_id      IS NULL OR lr.tipo_id      = :tipo_id)
          AND (:empresa_id   IS NULL OR lr.empresa_id   = :empresa_id)
          AND (:seccion_id   IS NULL OR lr.seccion_id   = :seccion_id)
          AND (:temporada_id IS NULL OR lr.temporada_id = :temporada_id)
        GROUP BY ta.talla_id, ta.nombre_talla
        ORDER BY cantidad DESC
    """), {k: v for k, v in filtros_base.items() if k != "talla_id"}).mappings().fetchall()

    empresa_rows = db.execute(text("""
        SELECT e.nombre_empresa AS nombre, COUNT(*) AS cantidad
        FROM lecturas_rfid lr
        JOIN empresa e ON lr.empresa_id = e.empresa_id
        WHERE (:tipo_id      IS NULL OR lr.tipo_id      = :tipo_id)
          AND (:talla_id     IS NULL OR lr.talla_id     = :talla_id)
          AND (:seccion_id   IS NULL OR lr.seccion_id   = :seccion_id)
          AND (:temporada_id IS NULL OR lr.temporada_id = :temporada_id)
        GROUP BY e.empresa_id, e.nombre_empresa
        ORDER BY cantidad DESC
    """), {k: v for k, v in filtros_base.items() if k != "empresa_id"}).mappings().fetchall()

    seccion_rows = db.execute(text("""
        SELECT s.nombre_seccion AS nombre, COUNT(*) AS cantidad
        FROM lecturas_rfid lr
        JOIN secciones s ON lr.seccion_id = s.seccion_id
        WHERE (:tipo_id      IS NULL OR lr.tipo_id      = :tipo_id)
          AND (:talla_id     IS NULL OR lr.talla_id     = :talla_id)
          AND (:empresa_id   IS NULL OR lr.empresa_id   = :empresa_id)
          AND (:temporada_id IS NULL OR lr.temporada_id = :temporada_id)
        GROUP BY s.seccion_id, s.nombre_seccion
        ORDER BY cantidad DESC
    """), {k: v for k, v in filtros_base.items() if k != "seccion_id"}).mappings().fetchall()

    temporada_rows = db.execute(text("""
        SELECT t.nombre_temporada AS nombre, COUNT(*) AS cantidad
        FROM lecturas_rfid lr
        JOIN temporadas t ON lr.temporada_id = t.temporada_id
        WHERE (:tipo_id    IS NULL OR lr.tipo_id    = :tipo_id)
          AND (:talla_id   IS NULL OR lr.talla_id   = :talla_id)
          AND (:empresa_id IS NULL OR lr.empresa_id = :empresa_id)
          AND (:seccion_id IS NULL OR lr.seccion_id = :seccion_id)
        GROUP BY t.temporada_id, t.nombre_temporada
        ORDER BY cantidad DESC
    """), {k: v for k, v in filtros_base.items() if k != "temporada_id"}).mappings().fetchall()

    def to_list(rows):
        return [{"nombre": r["nombre"], "cantidad": r["cantidad"]} for r in rows]

    return InventarioStatsResponse(
        total=resumen["total"] or 0,
        disponibles=resumen["disponibles"] or 0,
        en_uso=en_uso,
        con_rfid=resumen["con_rfid"] or 0,
        sin_rfid=resumen["sin_rfid"] or 0,
        por_tipo=to_list(tipos_rows),
        por_talla=to_list(tallas_rows),
        por_empresa=to_list(empresa_rows),
        por_seccion=to_list(seccion_rows),
        por_temporada=to_list(temporada_rows),
    )
