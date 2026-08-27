from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from app.schemas.personal import PersonalResponse, SyncEstado
from app.schemas.reportes import AreaCatalogo, SubAreaCatalogo
from app.services.personal_service import PersonalService
from app.services.personal_sync_service import PersonalSyncService
from app.db.deps import get_mysql_db
from app.core.security import get_current_user

router = APIRouter()


@router.get("/todos", response_model=List[PersonalResponse])
async def get_personal(search: str = None, incluir_inactivos: bool = False,
                       db: Session = Depends(get_mysql_db),
                       _: dict = Depends(get_current_user)):
    """
    Obtiene el personal desde la BD, opcionalmente filtrado por nombre o RUT.
    Por defecto solo activos; `incluir_inactivos=true` agrega a los desvinculados.
    """
    service = PersonalService(db)
    return service.obtener_personal(search, incluir_inactivos)


@router.get("/sync/estado", response_model=SyncEstado)
async def estado_sync(db: Session = Depends(get_mysql_db),
                      _: dict = Depends(get_current_user)):
    """Fecha de la última sincronización con RRHH (encabezado de la página Personal)."""
    return PersonalSyncService(db).estado()


# El sync no se dispara desde la API a propósito: corre solo por el scheduler
# (label de Ofelia en compose.yml → `python sync_personal.py`). Es una escritura
# masiva sobre la nómina completa, con capacidad de desactivar a cientos de
# personas de una, y no queremos esa palanca al alcance de un usuario. Para una
# corrida manual: `docker compose exec backend python sync_personal.py`.
# El servicio sigue expuesto acá solo de lectura, en /sync/estado.


@router.get("/areas", response_model=List[AreaCatalogo])
async def get_areas(empresa_id: int = None, db: Session = Depends(get_mysql_db),
                    _: dict = Depends(get_current_user)):
    """Catálogo de áreas (pobla los filtros de reportes y dashboard)."""
    return PersonalService(db).obtener_areas(empresa_id)


@router.get("/subareas", response_model=List[SubAreaCatalogo])
async def get_subareas(area_id: int = None, db: Session = Depends(get_mysql_db),
                       _: dict = Depends(get_current_user)):
    """Catálogo de subáreas, opcionalmente acotado a un área."""
    return PersonalService(db).obtener_subareas(area_id)


@router.get("/{rut}", response_model=PersonalResponse)
async def get_personal_por_rut(rut: str, db: Session = Depends(get_mysql_db),
                               _: dict = Depends(get_current_user)):
    """Obtiene un empleado por RUT. Va último: si no, /areas, /subareas y
    /sync/estado caerían en esta ruta."""
    service = PersonalService(db)
    result = service.obtener_por_rut(rut)
    if not result:
        raise HTTPException(status_code=404, detail="Personal no encontrado")
    return result
