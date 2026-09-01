"""
Endpoints del flujo de entregas de EPP — /api/entregas
Patrón Endpoint → Service → Repository.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.deps import get_mysql_db
from app.core.security import get_current_user, require_module
from app.services.entregas_service import EntregasService
from app.schemas.entregas import EntregaCreate, SustitucionCreate, EntregaResponse

router = APIRouter()


@router.post("/", response_model=List[EntregaResponse])
def crear_entregas(payload: EntregaCreate, db: Session = Depends(get_mysql_db),
                   current_user: dict = Depends(require_module("entregas"))):
    """
    Registra un carrito de entregas (motivos NUEVA/PERDIDA) y descuenta stock.

    Exige la firma del trabajador: con ella se genera el acta en PDF, que queda
    guardada y vinculada a las entregas en la misma transacción.
    """
    lineas = [linea.model_dump() for linea in payload.lineas]
    return EntregasService(db).crear_entregas(
        payload.rut, lineas, current_user.get("userId"), payload.firma)


@router.get("/acta/{acta_id}")
def descargar_acta(acta_id: int, db: Session = Depends(get_mysql_db),
                   _: dict = Depends(get_current_user)):
    """Descarga el PDF del acta firmada."""
    acta = EntregasService(db).get_acta_pdf(acta_id)
    fecha = acta["fecha_creacion"].strftime("%Y%m%d")
    nombre = f"acta-{acta['rut']}-{fecha}-{acta_id}.pdf"
    return Response(
        content=bytes(acta["pdf"]), media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
    )


@router.post("/sustitucion", response_model=EntregaResponse)
def crear_sustitucion(payload: SustitucionCreate, db: Session = Depends(get_mysql_db),
                      current_user: dict = Depends(require_module("entregas"))):
    """Sustitución por daño: entrega nueva vinculada + baja del ítem dañado."""
    return EntregasService(db).crear_sustitucion(
        rut=payload.rut, entrega_reemplazada_id=payload.entrega_reemplazada_id,
        producto_id=payload.producto_id, talla_id=payload.talla_id,
        cantidad=payload.cantidad, observacion=payload.observacion,
        usuario_id=current_user.get("userId"), uuid=payload.uuid, firma=payload.firma,
    )


@router.get("/", response_model=List[EntregaResponse])
def listar_entregas(rut: Optional[str] = None, motivo: Optional[str] = None,
                    area_id: Optional[int] = None,
                    desde: Optional[str] = Query(None, description="Fecha ISO desde (inclusive)"),
                    hasta: Optional[str] = Query(None, description="Fecha ISO hasta (inclusive)"),
                    db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    """Historial de entregas con filtros (rut, motivo, área, rango de fechas)."""
    return EntregasService(db).listar_entregas(rut, motivo, area_id, desde, hasta)


@router.get("/trabajador/{rut}", response_model=List[EntregaResponse])
def listar_vigentes(rut: str, db: Session = Depends(get_mysql_db),
                    _: dict = Depends(get_current_user)):
    """EPP vigentes de un trabajador (no reemplazados). Alimenta el modal de EPP."""
    return EntregasService(db).listar_vigentes(rut)
