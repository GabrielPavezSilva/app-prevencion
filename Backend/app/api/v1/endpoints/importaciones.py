"""
Endpoints de importación masiva EPP — /api/importaciones
Sube un Excel/CSV según un template y aplica las filas (productos, stock o
entregas históricas). Devuelve un resumen con filas OK y errores por fila.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.db.deps import get_mysql_db
from app.core.security import get_current_user, require_module
from app.services.importaciones_service import ImportacionesService

router = APIRouter()


@router.post("/{template_id}")
def importar(template_id: str, file: UploadFile = File(...),
             db: Session = Depends(get_mysql_db),
             current_user: dict = Depends(require_module("inventario"))):
    """Procesa un archivo Excel/CSV según el template indicado."""
    if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx/.xls) o CSV (.csv)")
    try:
        contenido = file.file.read()
        return ImportacionesService(db).procesar(
            template_id, contenido, file.filename, current_user.get("userId"),
            current_user=current_user
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[dict])
def listar_importaciones(db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    """Historial de importaciones ejecutadas."""
    return ImportacionesService(db).listar_importaciones()
