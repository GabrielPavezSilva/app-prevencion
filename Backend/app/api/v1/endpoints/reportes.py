from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.deps import get_mysql_db
from app.services.reportes_service import ReportesService
from app.schemas.reportes import ReportConfigSchema

router = APIRouter()

@router.post("/generar")
def generar_reporte(
    config: ReportConfigSchema,
    db: Session = Depends(get_mysql_db)
):
    """
    Genera un reporte Excel personalizado basado en la configuración.
    """
    try:
        service = ReportesService(db)
        # Convertimos el modelo Pydantic a dict para el servicio
        excel_file = service.generar_reporte_personalizado(config.dict())
        
        headers = {
            'Content-Disposition': 'attachment; filename="reporte_personalizado.xlsx"'
        }
        
        return StreamingResponse(
            excel_file, 
            headers=headers, 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/importar/{template_id}")
def importar_datos(
    template_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_mysql_db)
):
    """
    Recibe un archivo Excel y un template_id para procesar la subida masiva 
    de datos según las columnas requeridas por dicho template.
    """
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx, .xls) o CSV (.csv)")
        
    try:
        service = ReportesService(db)
        # Leer el contenido del archivo subido en memoria
        content = file.file.read()
        resultado = service.procesar_importacion_excel(template_id, content, file.filename)
        return resultado
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")
