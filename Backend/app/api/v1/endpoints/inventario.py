"""
Endpoints de catálogos vivos — /api/inventario
Reducido en Fase 2 a los catálogos que sobreviven al dominio EPP: tallas y
empresas. Los catálogos de prenda (tipos, secciones, temporadas) se eliminaron
junto con el dominio de lavandería.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.deps import get_mysql_db
from app.core.security import get_current_user, require_module
from app.core.logging_config import logger
from pydantic import BaseModel
from typing import List

router = APIRouter()


class TallaCreate(BaseModel):
    nombreTalla: str


# ---------------------------------------------------------
# Endpoints de Tallas
# ---------------------------------------------------------

@router.get("/tallas", response_model=List[dict])
def get_tallas(db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    """Obtiene todas las tallas desde la base de datos."""
    query = text('SELECT talla_id AS "TallaID", nombre_talla AS "nombreTalla" FROM tallas ORDER BY nombre_talla ASC')
    try:
        resultado = db.execute(query).mappings().fetchall()
        return [dict(r) for r in resultado]
    except Exception as e:
        logger.error(f"get_tallas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/tallas", response_model=dict)
def create_talla(talla: TallaCreate, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    """Crea una nueva talla."""
    query = text("INSERT INTO tallas (nombre_talla) VALUES (:nombre) RETURNING talla_id")
    try:
        new_id = db.execute(query, {"nombre": talla.nombreTalla.strip().upper()}).scalar()
        db.commit()
        return {"TallaID": new_id, "nombreTalla": talla.nombreTalla.strip().upper()}
    except Exception as e:
        db.rollback()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="Ya existe una talla con ese nombre.")
        logger.error(f"create_talla: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.put("/tallas/{talla_id}")
def update_talla(talla_id: int, talla: TallaCreate, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    """Actualiza una talla."""
    query = text("UPDATE tallas SET nombre_talla = :nombre WHERE talla_id = :id")
    try:
        result = db.execute(query, {"nombre": talla.nombreTalla.strip().upper(), "id": talla_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Talla no encontrada.")
        db.commit()
        return {"message": "Talla actualizada."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"update_talla: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.delete("/tallas/{talla_id}")
def delete_talla(talla_id: int, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    """Elimina una talla."""
    query = text("DELETE FROM tallas WHERE talla_id = :id")
    try:
        result = db.execute(query, {"id": talla_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Talla no encontrada.")
        db.commit()
        return {"message": "Talla eliminada"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        if "foreign key constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="No se puede eliminar: hay stock o entregas con esta talla.")
        logger.error(f"delete_talla: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ---------------------------------------------------------
# Endpoints de Empresas (selector multiempresa)
# ---------------------------------------------------------

@router.get("/empresas", response_model=List[dict])
def get_empresas(db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    """Obtiene la lista de empresas para selectores multiempresa."""
    query = text("SELECT empresa_id, nombre_empresa FROM empresa ORDER BY nombre_empresa ASC")
    try:
        resultado = db.execute(query).mappings().fetchall()
        return [dict(r) for r in resultado]
    except Exception as e:
        logger.error(f"get_empresas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
