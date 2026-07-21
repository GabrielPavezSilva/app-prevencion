from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.deps import get_mysql_db
from app.core.security import get_current_user, require_module
from app.core.logging_config import logger
from pydantic import BaseModel
from typing import List

router = APIRouter()

# --- Modelos Pydantic para los requests
class TipoPrendaCreate(BaseModel):
    nombreTipo: str

class TallaCreate(BaseModel):
    nombreTalla: str

class SeccionCreate(BaseModel):
    nombreSeccion: str

class TemporadaCreate(BaseModel):
    nombreTemporada: str

# ---------------------------------------------------------
# Endpoints de Tipos de Prenda
# ---------------------------------------------------------

@router.get("/tipos", response_model=List[dict])
def get_tipos(db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    """Obtiene toda la lista de tipos de prenda desde la bd."""
    query = text('SELECT tipo_id AS "TipoID", nombre_tipo AS "nombreTipo" FROM tiposprendas ORDER BY nombre_tipo ASC')
    try:
        resultado = db.execute(query).mappings().fetchall()
        return [dict(r) for r in resultado]
    except Exception as e:
        logger.error(f"get_tipos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/tipos", response_model=dict)
def create_tipo(tipo: TipoPrendaCreate, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    """Crea un nuevo tipo de prenda."""
    query = text("INSERT INTO tiposprendas (nombre_tipo) VALUES (:nombre)")
    try:
        result = db.execute(query, {"nombre": tipo.nombreTipo.strip().upper()})
        db.commit()
        return {"TipoID": result.lastrowid, "nombreTipo": tipo.nombreTipo.strip().upper()}
    except Exception as e:
        db.rollback()
        logger.error(f"create_tipo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/tipos/{tipo_id}")
def update_tipo(tipo_id: int, tipo: TipoPrendaCreate, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    """Actualiza un tipo de prenda existente por su ID."""
    query = text("UPDATE tiposprendas SET nombre_tipo = :nombre WHERE tipo_id = :id")
    try:
        result = db.execute(query, {"nombre": tipo.nombreTipo.strip().upper(), "id": tipo_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tipo de prenda no encontrado.")
        db.commit()
        return {"message": "Tipo actualizado correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"update_tipo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/tipos/{tipo_id}")
def delete_tipo(tipo_id: int, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    query = text("DELETE FROM tiposprendas WHERE tipo_id = :id")
    try:
        result = db.execute(query, {"id": tipo_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tipo de prenda no encontrado")
        db.commit()
        return {"message": "Tipo de prenda eliminado"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        if "foreign key constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="No se puede eliminar porque hay prendas que usan este tipo.")
        logger.error(f"delete_tipo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

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


# ---------------------------------------------------------
# Endpoints de Empresas (para selector en Modo Inventario)
# ---------------------------------------------------------

@router.get("/empresas", response_model=List[dict])
def get_empresas(db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    """Obtiene la lista de empresas para el selector de modo inventario."""
    query = text("SELECT empresa_id AS empresa_id, nombre_empresa AS nombre_empresa FROM empresa ORDER BY nombre_empresa ASC")
    try:
        resultado = db.execute(query).mappings().fetchall()
        return [dict(r) for r in resultado]
    except Exception as e:
        logger.error(f"get_empresas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/tallas", response_model=dict)
def create_talla(talla: TallaCreate, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    """Crea una nueva talla."""
    query = text("INSERT INTO tallas (nombre_talla) VALUES (:nombre)")
    try:
        result = db.execute(query, {"nombre": talla.nombreTalla.strip().upper()})
        db.commit()
        return {"TallaID": result.lastrowid, "nombreTalla": talla.nombreTalla.strip().upper()}
    except Exception as e:
        db.rollback()
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
            raise HTTPException(status_code=400, detail="No se puede eliminar porque hay prendas con esta talla.")
        logger.error(f"delete_talla: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ---------------------------------------------------------
# Endpoints de Secciones
# ---------------------------------------------------------

@router.get("/secciones", response_model=List[dict])
def get_secciones(db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    query = text('SELECT seccion_id AS "SeccionID", nombre_seccion AS "nombreSeccion" FROM secciones ORDER BY nombre_seccion ASC')
    try:
        resultado = db.execute(query).mappings().fetchall()
        return [dict(r) for r in resultado]
    except Exception as e:
        logger.error(f"get_secciones: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/secciones", response_model=dict)
def create_seccion(seccion: SeccionCreate, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    nombre = seccion.nombreSeccion.strip().upper()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre de la sección no puede estar vacío.")
    query = text("INSERT INTO secciones (nombre_seccion) VALUES (:nombre) RETURNING seccion_id")
    try:
        result = db.execute(query, {"nombre": nombre})
        new_id = result.scalar()
        db.commit()
        return {"SeccionID": new_id, "nombreSeccion": nombre}
    except Exception as e:
        db.rollback()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="Ya existe una sección con ese nombre.")
        logger.error(f"create_seccion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/secciones/{seccion_id}")
def update_seccion(seccion_id: int, seccion: SeccionCreate, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    nombre = seccion.nombreSeccion.strip().upper()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre de la sección no puede estar vacío.")
    query = text("UPDATE secciones SET nombre_seccion = :nombre WHERE seccion_id = :id")
    try:
        result = db.execute(query, {"nombre": nombre, "id": seccion_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Sección no encontrada.")
        db.commit()
        return {"message": "Sección actualizada."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"update_seccion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/secciones/{seccion_id}")
def delete_seccion(seccion_id: int, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    query = text("DELETE FROM secciones WHERE seccion_id = :id")
    try:
        result = db.execute(query, {"id": seccion_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Sección no encontrada.")
        db.commit()
        return {"message": "Sección eliminada"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        if "foreign key constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="No se puede eliminar porque hay prendas con esta sección.")
        logger.error(f"delete_seccion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ---------------------------------------------------------
# Endpoints de Temporadas
# ---------------------------------------------------------

@router.get("/temporadas", response_model=List[dict])
def get_temporadas(db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    query = text('SELECT temporada_id AS "TemporadaID", nombre_temporada AS "nombreTemporada" FROM temporadas ORDER BY nombre_temporada ASC')
    try:
        resultado = db.execute(query).mappings().fetchall()
        return [dict(r) for r in resultado]
    except Exception as e:
        logger.error(f"get_temporadas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/temporadas", response_model=dict)
def create_temporada(temporada: TemporadaCreate, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    nombre = temporada.nombreTemporada.strip().upper()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre de la temporada no puede estar vacío.")
    query = text("INSERT INTO temporadas (nombre_temporada) VALUES (:nombre) RETURNING temporada_id")
    try:
        result = db.execute(query, {"nombre": nombre})
        new_id = result.scalar()
        db.commit()
        return {"TemporadaID": new_id, "nombreTemporada": nombre}
    except Exception as e:
        db.rollback()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="Ya existe una temporada con ese nombre.")
        logger.error(f"create_temporada: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/temporadas/{temporada_id}")
def update_temporada(temporada_id: int, temporada: TemporadaCreate, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    nombre = temporada.nombreTemporada.strip().upper()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre de la temporada no puede estar vacío.")
    query = text("UPDATE temporadas SET nombre_temporada = :nombre WHERE temporada_id = :id")
    try:
        result = db.execute(query, {"nombre": nombre, "id": temporada_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Temporada no encontrada.")
        db.commit()
        return {"message": "Temporada actualizada."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"update_temporada: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/temporadas/{temporada_id}")
def delete_temporada(temporada_id: int, db: Session = Depends(get_mysql_db), _: dict = Depends(require_module("inventario"))):
    query = text("DELETE FROM temporadas WHERE temporada_id = :id")
    try:
        result = db.execute(query, {"id": temporada_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Temporada no encontrada.")
        db.commit()
        return {"message": "Temporada eliminada"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        if "foreign key constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="No se puede eliminar porque hay prendas con esta temporada.")
        logger.error(f"delete_temporada: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
