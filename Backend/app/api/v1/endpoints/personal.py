from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from app.schemas.personal import PersonalResponse
from app.services.personal_service import PersonalService
from app.db.deps import get_mysql_db
from app.core.security import get_current_user

router = APIRouter()


@router.get("/todos", response_model=List[PersonalResponse])
async def get_personal(search: str = None, db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    """
    Obtiene el personal desde la BD, opcionalmente filtrado por nombre o RUT.
    """
    service = PersonalService(db)
    return service.obtener_personal(search)


@router.get("/{rut}", response_model=PersonalResponse)
async def get_personal_por_rut(rut: str, db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    """
    Obtiene un empleado activo por RUT. Usado por el frontend tras identificación biométrica.
    """
    service = PersonalService(db)
    result = service.obtener_por_rut(rut)
    if not result:
        raise HTTPException(status_code=404, detail="Personal no encontrado")
    return result
