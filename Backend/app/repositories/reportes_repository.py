"""
Repository de reportabilidad EPP (Fase 5) — SQL crudo con sqlalchemy.text().

Reemplaza por completo al repository del dominio lavandería (consultaba
lecturas_rfid / tiposprendas / secciones / temporadas, tablas eliminadas en
Fase 1).

Dos convenciones que NO hay que romper al agregar queries acá:

1. **Zona horaria.** La BD corre en UTC y `fecha_entrega` es TIMESTAMP sin tz
   (`server_default=now()` → hora UTC). El negocio opera en Chile. Sin convertir,
   una entrega del 31 a las 21:00 hora local queda registrada el día 1 del mes
   siguiente en UTC y cae en el mes equivocado. Todo agrupamiento y todo filtro
   por fecha pasa por `FECHA_LOCAL`.

2. **Talla NULL.** Los joins contra `stock_epp` / `movimientos_stock` por
   (producto, talla) usan `IS NOT DISTINCT FROM`: en PostgreSQL `NULL = NULL`
   es NULL y los productos sin talla se perderían del join.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

# Fecha de la entrega expresada en hora de Chile (ver nota 1 del docstring).
FECHA_LOCAL = "((e.fecha_entrega AT TIME ZONE 'UTC') AT TIME ZONE 'America/Santiago')"
FECHA_LOCAL_REEMP = "((rep.fecha_entrega AT TIME ZONE 'UTC') AT TIME ZONE 'America/Santiago')"

# Joins compartidos por los reportes que parten de `entregas_epp`.
_JOINS_ENTREGA = """
    LEFT JOIN personal        per ON per.rut          = e.rut
    LEFT JOIN empresa         emp ON emp.empresa_id   = e.empresa_id
    LEFT JOIN areas           a   ON a.area_id        = per.area_id
    LEFT JOIN subareas        sa  ON sa.subarea_id    = per.subarea_id
    LEFT JOIN productos_epp   p   ON p.producto_id    = e.producto_id
    LEFT JOIN categorias_epp  cat ON cat.categoria_id = p.categoria_id
    LEFT JOIN tallas          t   ON t.talla_id       = e.talla_id
"""


def _filtros_entregas(f: Dict[str, Any], params: Dict[str, Any]) -> str:
    """
    Construye el WHERE de los reportes basados en entregas y carga `params`.

    El filtro por empresa usa `e.empresa_id` (denormalizado al momento de la
    entrega) y no el de `personal`: un traslado de empresa no debe reescribir
    el pasado. Área y subárea sí salen de `personal` — son el valor actual del
    trabajador (decisión Q2 del diseño de Fase 5).
    """
    sql = ""
    if f.get("desde"):
        sql += f" AND {FECHA_LOCAL}::date >= CAST(:desde AS date)"
        params["desde"] = f["desde"]
    if f.get("hasta"):
        sql += f" AND {FECHA_LOCAL}::date <= CAST(:hasta AS date)"
        params["hasta"] = f["hasta"]
    if f.get("motivo"):
        sql += " AND e.motivo = :motivo"
        params["motivo"] = f["motivo"]
    if f.get("empresa_id") is not None:
        sql += " AND e.empresa_id = :empresa_id"
        params["empresa_id"] = f["empresa_id"]
    if f.get("area_id") is not None:
        sql += " AND per.area_id = :area_id"
        params["area_id"] = f["area_id"]
    if f.get("subarea_id") is not None:
        sql += " AND per.subarea_id = :subarea_id"
        params["subarea_id"] = f["subarea_id"]
    if f.get("producto_id") is not None:
        sql += " AND e.producto_id = :producto_id"
        params["producto_id"] = f["producto_id"]
    if f.get("categoria_id") is not None:
        sql += " AND p.categoria_id = :categoria_id"
        params["categoria_id"] = f["categoria_id"]
    if f.get("rut"):
        sql += " AND e.rut = :rut"
        params["rut"] = f["rut"]
    return sql


class ReportesRepository:
    def __init__(self, db: Session):
        self.db = db

    def _rows(self, sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.db.execute(text(sql), params).mappings().fetchall()]

    # ── R1 · Trazabilidad de entregas ────────────────────────────────────────

    def trazabilidad_entregas(self, filtros: Dict[str, Any],
                              limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Una fila por entrega, con toda la ficha organizacional del trabajador.
        Es el reporte que reemplaza al seguimiento de pérdidas por correo.
        """
        params: Dict[str, Any] = {}
        sql = f"""
            SELECT
                {FECHA_LOCAL}          AS fecha_entrega,
                e.entrega_id,
                e.rut,
                e.nombre_completo,
                emp.nombre_empresa     AS empresa,
                a.nombre_area          AS area,
                sa.nombre_subarea      AS subarea,
                per.cargo,
                cat.nombre_categoria   AS categoria,
                p.nombre               AS producto,
                t.nombre_talla         AS talla,
                e.cantidad,
                e.motivo,
                e.entrega_reemplazada_id,
                {FECHA_LOCAL_REEMP}    AS fecha_reemplazada,
                e.observacion,
                u.username             AS registrado_por
            FROM entregas_epp e
            {_JOINS_ENTREGA}
            LEFT JOIN entregas_epp rep ON rep.entrega_id = e.entrega_reemplazada_id
            LEFT JOIN usuarios     u   ON u.user_id      = e.usuario_entrega
            WHERE 1=1
        """
        sql += _filtros_entregas(filtros, params)
        sql += " ORDER BY e.fecha_entrega DESC, e.entrega_id DESC"
        if limit is not None:
            sql += " LIMIT :limit"
            params["limit"] = limit
        return self._rows(sql, params)

    # ── R2 · EPP vigentes por trabajador ─────────────────────────────────────

    def _cond_vigente(self) -> str:
        """Entrega no reemplazada por una posterior (sustitución o reposición)."""
        return """
            NOT EXISTS (
                SELECT 1 FROM entregas_epp r
                WHERE r.entrega_reemplazada_id = e.entrega_id
            )
        """

    def epp_vigentes(self, filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Una fila por (trabajador × EPP vigente).

        LEFT JOIN a propósito: los trabajadores SIN EPP vigente salen con la
        fila en blanco y `sin_epp = true` — saber quién está descubierto es la
        mitad del valor del reporte (Q3).

        Los filtros de producto/categoría van dentro del ON del join, no en el
        WHERE: filtrando por "botas de seguridad" el reporte debe seguir
        listando a quien NO tiene botas, marcado como sin_epp.

        La categoría se filtra con EXISTS y no contra el alias `p`: ese join se
        resuelve después de `e` y el ON no puede referenciarlo todavía.
        """
        params: Dict[str, Any] = {}

        cond_join = ""
        if filtros.get("producto_id") is not None:
            cond_join += " AND e.producto_id = :producto_id"
            params["producto_id"] = filtros["producto_id"]
        if filtros.get("categoria_id") is not None:
            cond_join += """
                  AND EXISTS (
                      SELECT 1 FROM productos_epp pf
                      WHERE pf.producto_id = e.producto_id
                        AND pf.categoria_id = :categoria_id
                  )"""
            params["categoria_id"] = filtros["categoria_id"]

        where = ""
        if not filtros.get("incluir_inactivos"):
            where += " AND COALESCE(per.activo, TRUE) = TRUE"
        if filtros.get("empresa_id") is not None:
            where += " AND per.empresa_id = :empresa_id"
            params["empresa_id"] = filtros["empresa_id"]
        if filtros.get("area_id") is not None:
            where += " AND per.area_id = :area_id"
            params["area_id"] = filtros["area_id"]
        if filtros.get("subarea_id") is not None:
            where += " AND per.subarea_id = :subarea_id"
            params["subarea_id"] = filtros["subarea_id"]
        if filtros.get("rut"):
            where += " AND per.rut = :rut"
            params["rut"] = filtros["rut"]

        sql = f"""
            SELECT
                per.rut,
                per.nombre_completo,
                emp.nombre_empresa    AS empresa,
                a.nombre_area         AS area,
                sa.nombre_subarea     AS subarea,
                per.cargo,
                COALESCE(per.activo, TRUE) AS activo,
                cat.nombre_categoria  AS categoria,
                p.nombre              AS producto,
                t.nombre_talla        AS talla,
                e.cantidad,
                e.motivo,
                {FECHA_LOCAL}         AS fecha_entrega,
                CASE WHEN e.entrega_id IS NULL THEN NULL
                     ELSE (CURRENT_DATE - {FECHA_LOCAL}::date) END AS dias_desde_entrega,
                (e.entrega_id IS NULL) AS sin_epp
            FROM personal per
            LEFT JOIN entregas_epp e
                   ON e.rut = per.rut
                  AND {self._cond_vigente()}
                  {cond_join}
            LEFT JOIN productos_epp  p   ON p.producto_id    = e.producto_id
            LEFT JOIN categorias_epp cat ON cat.categoria_id = p.categoria_id
            LEFT JOIN tallas         t   ON t.talla_id       = e.talla_id
            LEFT JOIN empresa        emp ON emp.empresa_id   = per.empresa_id
            LEFT JOIN areas          a   ON a.area_id        = per.area_id
            LEFT JOIN subareas       sa  ON sa.subarea_id    = per.subarea_id
            WHERE 1=1 {where}
            ORDER BY per.nombre_completo, p.nombre, t.nombre_talla
        """
        return self._rows(sql, params)

    def epp_vigentes_resumen(self, filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Una fila por trabajador: cuántos EPP vigentes tiene y cuáles."""
        detalle = self.epp_vigentes(filtros)
        resumen: Dict[str, Dict[str, Any]] = {}
        for fila in detalle:
            r = resumen.setdefault(fila["rut"], {
                "rut": fila["rut"],
                "nombre_completo": fila["nombre_completo"],
                "empresa": fila["empresa"],
                "area": fila["area"],
                "subarea": fila["subarea"],
                "cargo": fila["cargo"],
                "activo": fila["activo"],
                "total_epp": 0,
                "unidades": 0,
                "detalle": [],
            })
            if not fila["sin_epp"]:
                r["total_epp"] += 1
                r["unidades"] += fila["cantidad"] or 0
                etiqueta = " · ".join(x for x in (fila["producto"], fila["talla"]) if x)
                r["detalle"].append(etiqueta)
        for r in resumen.values():
            r["detalle"] = ", ".join(r["detalle"])
            r["sin_epp"] = r["total_epp"] == 0
        return sorted(resumen.values(), key=lambda x: x["nombre_completo"] or "")

    # ── R3 · Stock y quiebres ────────────────────────────────────────────────

    def stock_quiebres(self, categoria_id: Optional[int] = None,
                       solo_alertas: bool = False,
                       dias_consumo: int = 90) -> List[Dict[str, Any]]:
        """
        Snapshot de stock con consumo de la ventana y cobertura estimada.

        `consumo` sale de movimientos_stock tipo ENTREGA (cantidades negativas,
        por eso el SUM(-cantidad)). BAJA_DANO se excluye a propósito: no descuenta
        del bodegón, documenta la baja de una unidad que ya estaba en terreno.
        """
        params: Dict[str, Any] = {"dias": dias_consumo}
        sql = """
            WITH consumo AS (
                SELECT producto_id, talla_id, SUM(-cantidad) AS consumido
                FROM movimientos_stock
                WHERE tipo = 'ENTREGA'
                  AND fecha >= now() - make_interval(days => :dias)
                GROUP BY producto_id, talla_id
            )
            SELECT
                cat.nombre_categoria AS categoria,
                p.nombre             AS producto,
                t.nombre_talla       AS talla,
                s.cantidad_actual,
                s.stock_minimo,
                GREATEST(s.stock_minimo - s.cantidad_actual, 0) AS deficit,
                CASE
                    WHEN s.cantidad_actual <= 0             THEN 'QUIEBRE'
                    WHEN s.cantidad_actual <= s.stock_minimo THEN 'BAJO'
                    ELSE 'OK'
                END AS estado,
                COALESCE(c.consumido, 0) AS consumo,
                CASE WHEN COALESCE(c.consumido, 0) > 0
                     THEN ROUND(s.cantidad_actual / (c.consumido::numeric / :dias))
                END AS cobertura_dias
            FROM stock_epp s
            JOIN productos_epp p ON p.producto_id = s.producto_id
            LEFT JOIN categorias_epp cat ON cat.categoria_id = p.categoria_id
            LEFT JOIN tallas t ON t.talla_id = s.talla_id
            LEFT JOIN consumo c
                   ON c.producto_id = s.producto_id
                  AND c.talla_id IS NOT DISTINCT FROM s.talla_id
            WHERE 1=1
        """
        if categoria_id is not None:
            sql += " AND p.categoria_id = :categoria_id"
            params["categoria_id"] = categoria_id
        if solo_alertas:
            sql += " AND s.cantidad_actual <= s.stock_minimo"
        sql += """
            ORDER BY
                CASE WHEN s.cantidad_actual <= 0 THEN 0
                     WHEN s.cantidad_actual <= s.stock_minimo THEN 1
                     ELSE 2 END,
                p.nombre, t.nombre_talla
        """
        return self._rows(sql, params)

    # ── Dashboard ────────────────────────────────────────────────────────────

    def kpis_entregas(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        sql = f"""
            SELECT
                COALESCE(SUM(e.cantidad), 0) AS unidades,
                COUNT(*)                     AS lineas,
                COALESCE(SUM(CASE WHEN e.motivo = 'NUEVA'   THEN e.cantidad ELSE 0 END), 0) AS unidades_nueva,
                COALESCE(SUM(CASE WHEN e.motivo = 'PERDIDA' THEN e.cantidad ELSE 0 END), 0) AS unidades_perdida,
                COALESCE(SUM(CASE WHEN e.motivo = 'DANO'    THEN e.cantidad ELSE 0 END), 0) AS unidades_dano,
                COUNT(DISTINCT e.rut)        AS trabajadores_atendidos
            FROM entregas_epp e
            LEFT JOIN personal      per ON per.rut       = e.rut
            LEFT JOIN productos_epp p   ON p.producto_id = e.producto_id
            WHERE 1=1
        """
        sql += _filtros_entregas(filtros, params)
        row = self.db.execute(text(sql), params).mappings().fetchone()
        return dict(row) if row else {}

    def kpis_stock(self) -> Dict[str, Any]:
        row = self.db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE cantidad_actual <= stock_minimo) AS bajo_minimo,
                COUNT(*) FILTER (WHERE cantidad_actual <= 0)            AS quiebre,
                COALESCE(SUM(cantidad_actual), 0)                       AS unidades_en_bodega
            FROM stock_epp
        """)).mappings().fetchone()
        return dict(row) if row else {}

    def kpis_personal(self) -> Dict[str, Any]:
        row = self.db.execute(text("""
            SELECT
                COUNT(*) AS trabajadores_activos,
                COUNT(*) FILTER (
                    WHERE NOT EXISTS (
                        SELECT 1 FROM entregas_epp e
                        WHERE e.rut = per.rut
                          AND NOT EXISTS (
                              SELECT 1 FROM entregas_epp r
                              WHERE r.entrega_reemplazada_id = e.entrega_id
                          )
                    )
                ) AS trabajadores_sin_epp
            FROM personal per
            WHERE COALESCE(per.activo, TRUE) = TRUE
        """)).mappings().fetchone()
        return dict(row) if row else {}

    def serie_mensual(self, meses: int, hasta: Optional[str],
                      filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Serie de N meses terminando en el mes de `hasta` (o el mes en curso).

        `generate_series` LEFT JOIN la agregación: los meses sin entregas salen
        en 0 en vez de desaparecer. Si faltan, Recharts dibuja un hueco y se lee
        como un bug de datos.
        """
        params: Dict[str, Any] = {"meses": meses, "hasta": hasta}
        # Los filtros de periodo no aplican a la serie: su ventana es propia.
        filtros_serie = {k: v for k, v in filtros.items() if k not in ("desde", "hasta")}
        where = _filtros_entregas(filtros_serie, params)

        sql = f"""
            WITH ref AS (
                SELECT date_trunc('month',
                    COALESCE(CAST(:hasta AS date), CURRENT_DATE)
                )::date AS fin
            ),
            meses AS (
                SELECT generate_series(
                    (SELECT fin FROM ref) - make_interval(months => :meses - 1),
                    (SELECT fin FROM ref),
                    INTERVAL '1 month'
                )::date AS mes
            ),
            agg AS (
                SELECT
                    date_trunc('month', {FECHA_LOCAL})::date AS mes,
                    COALESCE(SUM(CASE WHEN e.motivo = 'NUEVA'   THEN e.cantidad ELSE 0 END), 0) AS nueva,
                    COALESCE(SUM(CASE WHEN e.motivo = 'PERDIDA' THEN e.cantidad ELSE 0 END), 0) AS perdida,
                    COALESCE(SUM(CASE WHEN e.motivo = 'DANO'    THEN e.cantidad ELSE 0 END), 0) AS dano,
                    COALESCE(SUM(e.cantidad), 0) AS total
                FROM entregas_epp e
                LEFT JOIN personal      per ON per.rut       = e.rut
                LEFT JOIN productos_epp p   ON p.producto_id = e.producto_id
                WHERE date_trunc('month', {FECHA_LOCAL})::date
                      BETWEEN (SELECT fin FROM ref) - make_interval(months => :meses - 1)
                          AND (SELECT fin FROM ref)
                      {where}
                GROUP BY 1
            )
            SELECT
                to_char(m.mes, 'YYYY-MM')  AS mes,
                COALESCE(agg.nueva, 0)     AS nueva,
                COALESCE(agg.perdida, 0)   AS perdida,
                COALESCE(agg.dano, 0)      AS dano,
                COALESCE(agg.total, 0)     AS total
            FROM meses m
            LEFT JOIN agg ON agg.mes = m.mes
            ORDER BY m.mes
        """
        return self._rows(sql, params)

    def _agrupado(self, expresion: str, filtros: Dict[str, Any],
                  limit: int) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        sql = f"""
            SELECT {expresion} AS nombre, COALESCE(SUM(e.cantidad), 0) AS cantidad
            FROM entregas_epp e
            LEFT JOIN personal      per ON per.rut          = e.rut
            LEFT JOIN areas         a   ON a.area_id        = per.area_id
            LEFT JOIN productos_epp p   ON p.producto_id    = e.producto_id
            LEFT JOIN categorias_epp cat ON cat.categoria_id = p.categoria_id
            WHERE 1=1
        """
        sql += _filtros_entregas(filtros, params)
        sql += " GROUP BY 1 ORDER BY cantidad DESC LIMIT :limit"
        return self._rows(sql, params)

    def por_motivo(self, filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._agrupado("e.motivo", filtros, limit=10)

    def por_area(self, filtros: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        return self._agrupado("COALESCE(a.nombre_area, 'Sin área')", filtros, limit)

    def top_productos(self, filtros: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        return self._agrupado("COALESCE(p.nombre, 'Sin producto')", filtros, limit)

    def alertas_stock(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.stock_quiebres(solo_alertas=True)[:limit]
