from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.schemas.personal import PersonalResponse
from app.core.logging_config import logger


# Un trabajador puede tener EPP vigentes: entregas que ninguna sustitución reemplazó
# (misma definición que EntregasRepository.get_vigentes_por_rut).
_SELECT_PERSONAL = """
    SELECT p.rut, p.nombre_completo, e.nombre_empresa AS empresa, p.cargo,
           p.area_id, p.subarea_id,
           a.nombre_area, s.nombre_subarea,
           p.url_picture, COALESCE(p.activo, TRUE) AS activo, p.sync_at,
           (SELECT COUNT(*)
              FROM entregas_epp en
             WHERE en.rut = p.rut
               AND NOT EXISTS (
                   SELECT 1 FROM entregas_epp r
                    WHERE r.entrega_reemplazada_id = en.entrega_id
               )
           ) AS epp_vigentes
    FROM personal p
    JOIN empresa e ON e.empresa_id = p.empresa_id
    LEFT JOIN areas a ON a.area_id = p.area_id
    LEFT JOIN subareas s ON s.subarea_id = p.subarea_id
"""


class PersonalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_personal(self, search: str = None,
                     incluir_inactivos: bool = False) -> List[PersonalResponse]:
        """
        Retorna el personal desde la BD, opcionalmente filtrado por nombre o RUT.

        Por defecto solo activos: los desvinculados se conservan (soft-delete del
        sync) para no perder su historial de entregas, pero no se listan.
        """
        condiciones = []
        params = {}

        if not incluir_inactivos:
            condiciones.append("COALESCE(p.activo, TRUE) = TRUE")

        if search:
            condiciones.append(
                "(p.nombre_completo ILIKE :search_name"
                " OR LOWER(REPLACE(REPLACE(p.rut, '.', ''), '-', '')) LIKE :search_rut)"
            )
            params["search_name"] = f"%{search}%"
            params["search_rut"] = f"%{search.lower().replace('.', '').replace('-', '')}%"

        sql = _SELECT_PERSONAL
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " ORDER BY p.nombre_completo"

        try:
            result = self.db.execute(text(sql), params).mappings().fetchall()
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error al obtener personal: {type(e).__name__}: {str(e)}")
            raise

    def get_by_rut(self, rut: str):
        """Busca un empleado por su RUT (activo o no)."""
        sql = _SELECT_PERSONAL + " WHERE p.rut = :rut"
        try:
            row = self.db.execute(text(sql), {"rut": rut}).mappings().fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error al buscar personal por RUT: {type(e).__name__}: {str(e)}")
            raise
