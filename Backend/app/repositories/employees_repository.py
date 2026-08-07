"""
Lectura de la nómina desde la base de RRHH (`rh_cramer`, schema `rh`).

Único punto del sistema que toca esa base, y solo con SELECT.
Ver `app/db/session_employees.py` para la conexión.
"""
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging_config import logger

# Empresa de testing en el origen (1 sola persona) — excluida por decisión de negocio.
EMPRESAS_EXCLUIDAS = ("PRUEBA",)

# LEFT JOIN a propósito, y sin el join al jefe de la query original:
#   - `personal` no guarda jefe, así que traerlo solo servía para perder gente:
#     con INNER JOIN, quien no tenga `rut_boss` desaparece del payload y el sync
#     lo marcaría inactivo. Hoy no pasa (0 casos), pero un alta futura sin jefe sí.
#   - `rh.areas.id` es único global (163/163 verificado), así que el join por
#     `cost_center AND id` es redundante; se conserva por fidelidad al origen.
_QUERY_NOMINA = text("""
    SELECT e.rut,
           e.full_name                AS nombre_completo,
           e.name_role                AS cargo,
           e.person_id                AS buk_id,
           e.picture_url              AS url_picture,
           a.first_level_id           AS empresa_origen_id,
           a.first_level_name         AS empresa,
           a.second_level_id          AS area_origen_id,
           a.second_level_name        AS area,
           a.id                       AS subarea_origen_id,
           a."name"                   AS subarea
    FROM rh.employees e
    LEFT JOIN rh.areas a
           ON a.cost_center = e.cost_center
          AND a.id = e.area_id
    WHERE e.status = 'activo'
      AND COALESCE(TRIM(a.first_level_name), '') <> ALL(:empresas_excluidas)
    ORDER BY e.rut
""")


class EmployeesRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_nomina_activa(self) -> List[Dict[str, Any]]:
        """
        Retorna la nómina activa (~590 filas). Sync full: `updated_at` no sirve
        para incremental porque el ETL de RRHH reescribe la tabla entera en cada
        corrida (todos los registros comparten timestamp).
        """
        try:
            rows = self.db.execute(
                _QUERY_NOMINA, {"empresas_excluidas": list(EMPRESAS_EXCLUIDAS)}
            ).mappings().fetchall()
            logger.info(f"Nómina leída desde RRHH: {len(rows)} activos")
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error al leer la nómina de RRHH: {type(e).__name__}: {e}")
            raise
