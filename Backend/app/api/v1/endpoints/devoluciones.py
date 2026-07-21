from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.services.asignaciones_service import AsignacionesService
from app.db.deps import get_mysql_db
from app.core.security import get_current_user

router = APIRouter()


class ReturnItem(BaseModel):
    id: int
    sku: str
    quantityReturned: int = 0
    status: str = ""


class ProcessReturnRequest(BaseModel):
    employeeId: str
    items: List[ReturnItem]
    notes: str = ""


@router.get("/employees")
async def get_employees_with_returns(db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    service = AsignacionesService(db)
    return service.obtener_empleados_con_pendientes()


@router.get("/employees/{employee_id}/items")
async def get_employee_return_items(employee_id: str, db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    service = AsignacionesService(db)
    return service.obtener_prendas_pendientes(employee_id)


@router.post("/process")
async def process_return(request: ProcessReturnRequest, db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    service = AsignacionesService(db)
    return service.procesar_devolucion(
        request.employeeId,
        [item.model_dump() for item in request.items]
    )
