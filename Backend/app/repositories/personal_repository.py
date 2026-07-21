from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.schemas.personal import PersonalResponse
from app.core.logging_config import logger


# Output:
# Columnas: rut, nombre_completo, empresa, cargo, area_id, subarea_id, talla_id
class PersonalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_personal(self, search: str = None) -> List[PersonalResponse]:
        """Retorna el personal completo desde la BD, opcionalmente filtrado."""
        if search:
            query = text("""
                SELECT p.rut, p.nombre_completo, e.nombre_empresa AS empresa, p.cargo,
                       p.area_id, p.subarea_id, p.talla_id,
                       s.nombre_subarea, p.url_picture
                FROM personal p
                JOIN empresa e ON e.empresa_id = p.empresa_id
                LEFT JOIN subareas s ON s.subarea_id = p.subarea_id
                WHERE COALESCE(p.activo, TRUE) = TRUE
                  AND (p.nombre_completo ILIKE :search_name
                   OR LOWER(REPLACE(REPLACE(p.rut, '.', ''), '-', '')) LIKE :search_rut)
            """)
            params = {
                "search_name": f"%{search}%",
                "search_rut": f"%{search.lower()}%",
            }
        else:
            query = text("""
                SELECT p.rut, p.nombre_completo, e.nombre_empresa AS empresa, p.cargo,
                       p.area_id, p.subarea_id, p.talla_id,
                       s.nombre_subarea, p.url_picture
                FROM personal p
                JOIN empresa e ON e.empresa_id = p.empresa_id
                LEFT JOIN subareas s ON s.subarea_id = p.subarea_id
                WHERE COALESCE(p.activo, TRUE) = TRUE
            """)
            params = {}

        try:
            result = self.db.execute(query, params).mappings().fetchall()
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error al obtener personal: {type(e).__name__}: {str(e)}")
            raise

    def get_by_rut(self, rut: str):
        """Busca un empleado por su RUT."""
        query = text("""
            SELECT p.rut, p.nombre_completo, e.nombre_empresa AS empresa, p.cargo,
                   p.area_id, p.subarea_id, p.talla_id,
                   s.nombre_subarea, p.url_picture
            FROM personal p
            JOIN empresa e ON e.empresa_id = p.empresa_id
            LEFT JOIN subareas s ON s.subarea_id = p.subarea_id
            WHERE p.rut = :rut
              AND COALESCE(p.activo, TRUE) = TRUE
        """)
        try:
            row = self.db.execute(query, {"rut": rut}).mappings().fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error al buscar personal por RUT: {type(e).__name__}: {str(e)}")
            raise
    
    # def update_personal(self, URL_BUK: str):
    #     """Obtiene a todo el personal desde la API de BUK y actualiza la BD."""
    #     headers = {"auth_token": settings.BUK_TOKEN}

    #     url_actual = URL_BUK
    #     while url_actual:
    #         logger.info(f"Obteniendo personal desde la API de BUK")    
    #         try:
    #             respuesta = requests.get(url_actual, headers=headers, timeout=10)
    #             respuesta.raise_for_status()

    #             respuesta_api = respuesta.json()
    #             personal_pagina = respuesta_api['data']
    #             pagination_info = respuesta_api['pagination']

    #             for trabajador in personal_pagina:
    #                 trabajador_obtenido = {
    #                     "full_name" : trabajador.get("full_name"),
    #                     "rut" : trabajador.get("rut"),
    #                     "picture_url" : trabajador.get("picture_url"),
    #                     "status" : trabajador.get("status"),
    #                     "area_id" : trabajador.get("current_job").get("area_id"),
    #                     "cost_center" : trabajador.get("current_job").get("cost_center"),
    #                 }

    #             #TODO: Manejar inserción a la BD desde esta función
    #             self.db.execute(text("""
    #                 UPDATE personal
    #                 SET nombre_completo = :nombre_completo,
    #                     empresa = :empresa,
    #                     cargo = :cargo,
    #                     area_id = :area_id,
    #                     subarea_id = :subarea_id,
    #                     talla_id = :talla_id
    #                 WHERE rut = :rut
    #             """), {
    #                 "nombre_completo": trabajador["full_name"],
    #                 "area_id": trabajador["area_id"],
    #                 "subarea_id": trabajador["subarea_id"],
    #                 "talla_id": trabajador["talla_id"],
    #                 "rut": trabajador["rut"]
    #             })
    #         self.db.commit()
    #     except Exception as e:
    #         logger.error(f"Error al actualizar personal: {type(e).__name__}: {str(e)}")
    #         raise