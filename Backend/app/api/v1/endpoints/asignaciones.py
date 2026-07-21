from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.services.asignaciones_service import AsignacionesService
from app.schemas.asignaciones import AsignacionesResponse
from app.db.deps import get_mysql_db
from app.core.security import get_current_user, require_module

router = APIRouter()

# Los paneles de Asignación y Recepción usan estos endpoints. Un operario que
# puede ver "Asignación"/"Recepción" debe poder asignar y corregir — no solo "personal".
_ASIGNACION_MODULES = ("personal", "worker_asignacion", "worker_recepcion")


@router.get("/todas", response_model=List[AsignacionesResponse])
async def obtener_asignaciones(db: Session = Depends(get_mysql_db), _: dict = Depends(require_module(*_ASIGNACION_MODULES))):
    """Obtiene todas las asignaciones"""
    service = AsignacionesService(db)
    return service.obtener_asignaciones()


@router.delete("/activa/{sku}", response_model=dict)
async def anular_asignacion_activa(
    sku: str,
    db: Session = Depends(get_mysql_db),
    current_user: dict = Depends(require_module(*_ASIGNACION_MODULES)),
):
    """Anula la asignación activa de un SKU (corrección in-situ desde el staging)."""
    service = AsignacionesService(db)
    try:
        return service.anular_asignacion_por_sku(
            sku,
            usuario_id=current_user.get("userId"),
            usuario_nombre=current_user.get("username"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{asignacion_id}", response_model=dict)
async def anular_asignacion(
    asignacion_id: int,
    db: Session = Depends(get_mysql_db),
    current_user: dict = Depends(require_module(*_ASIGNACION_MODULES)),
):
    """Anula una asignación activa por error. Restaura disponibilidad de la prenda y registra auditoría."""
    service = AsignacionesService(db)
    try:
        return service.anular_asignacion(
            asignacion_id,
            usuario_id=current_user.get("userId"),
            usuario_nombre=current_user.get("username"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
