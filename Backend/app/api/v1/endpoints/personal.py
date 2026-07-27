from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
from app.schemas.personal import PersonalResponse, SyncEstado, SyncResumen
from app.services.personal_service import PersonalService
from app.services.personal_sync_service import PersonalSyncService
from app.db.deps import get_mysql_db
from app.db.session_employees import EmployeesNotConfigured
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


@router.post("/sync", response_model=SyncResumen)
async def sincronizar_personal(dry_run: bool = False,
                               db: Session = Depends(get_mysql_db),
                               current_user: dict = Depends(get_current_user)):
    """
    Sincroniza `personal` con la nómina activa de RRHH (base `rh_cramer`).

    RRHH es la fuente de verdad: pisa todos los campos y desactiva (nunca borra)
    a quienes salieron de la nómina. Con `dry_run=true` se calcula el resultado
    sin escribir.

    Corre a diario de forma automática; este endpoint es para el alta del día.
    """
    role = current_user.get("role", "")
    modulos = current_user.get("modulos", []) or []
    if role not in ("admin", "administrador") and "personal" not in modulos:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No autorizado para sincronizar personal")

    try:
        return PersonalSyncService(db).sincronizar(
            usuario_id=current_user.get("userId"), dry_run=dry_run
        )
    except EmployeesNotConfigured as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{rut}", response_model=PersonalResponse)
async def get_personal_por_rut(rut: str, db: Session = Depends(get_mysql_db),
                               _: dict = Depends(get_current_user)):
    """Obtiene un empleado por RUT. Va último: si no, /sync caería en esta ruta."""
    service = PersonalService(db)
    result = service.obtener_por_rut(rut)
    if not result:
        raise HTTPException(status_code=404, detail="Personal no encontrado")
    return result
