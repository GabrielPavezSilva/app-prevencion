from sqlalchemy.orm import Session
from typing import List
from app.repositories.personal_repository import PersonalRepository
from app.schemas.personal import PersonalResponse
from app.core.logging_config import logger

class PersonalService:
    def __init__(self, db: Session):
        self.repository = PersonalRepository(db)

    def obtener_personal(self, search: str = None,
                         incluir_inactivos: bool = False) -> List[PersonalResponse]:
        logger.info(f"Obteniendo personal (search={search}, inactivos={incluir_inactivos})")
        return self.repository.get_personal(search, incluir_inactivos)

    def obtener_por_rut(self, rut: str):
        return self.repository.get_by_rut(rut)

    def obtener_areas(self, empresa_id: int = None) -> List[dict]:
        return self.repository.get_areas(empresa_id)

    def obtener_subareas(self, area_id: int = None) -> List[dict]:
        return self.repository.get_subareas(area_id)
