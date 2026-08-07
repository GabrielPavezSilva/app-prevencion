import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from typing import List
from app.core.security import require_module
from app.schemas.templates import ImportTemplate, DEFAULT_TEMPLATES

# Los templates describen la estructura de las importaciones: mismo módulo que
# la página que los consume (Importaciones vive bajo `inventario`).
router = APIRouter(dependencies=[Depends(require_module("inventario"))])

@router.get("/", response_model=List[ImportTemplate])
def obtener_templates():
    """
    Retorna la lista de templates de importación disponibles en el sistema.
    """
    # TODO: Podría extraerse de la base de datos más adelante.
    return DEFAULT_TEMPLATES

@router.get("/{template_id}", response_model=ImportTemplate)
def obtener_template_por_id(template_id: str):
    """
    Retorna un template de importación específico por su ID.
    """
    template = next((t for t in DEFAULT_TEMPLATES if t.id == template_id), None)
    if not template:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Template no encontrado")
    return template

@router.get("/descargar/{template_id}")
def descargar_plantilla(template_id: str):
    """
    Genera y descarga un archivo Excel vacio (.xlsx) con las columnas
    requeridas según el template indicado.
    """
    template = next((t for t in DEFAULT_TEMPLATES if t.id == template_id), None)
    if not template:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Template no encontrado")
        
    wb = Workbook()
    ws = wb.active
    ws.title = "Plantilla"
    
    # Escribir cabeceras en la primera fila
    headers = [col.name for col in template.columns]
    ws.append(headers)
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    safe_id = "".join(c for c in template_id if c.isalnum() or c in "-_")
    headers_response = {
        'Content-Disposition': f'attachment; filename="plantilla_{safe_id}.xlsx"'
    }
    
    return StreamingResponse(
        output,
        headers=headers_response,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
