from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.repositories.catalogos_repository import CatalogosRepository


class CatalogosService:
    def __init__(self, db: Session):
        self.repo = CatalogosRepository(db)

    # ── Tipos de Prenda ──────────────────────────────────────────────────────

    def listar_tipos(self) -> List[Dict[str, Any]]:
        return self.repo.get_all_tipos()

    def crear_tipo(self, nombre: str) -> Dict[str, Any]:
        nombre = nombre.strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre del tipo no puede estar vacío")
        if self.repo.get_tipo_by_nombre(nombre):
            raise HTTPException(status_code=400, detail=f"Ya existe un tipo con el nombre '{nombre}'")
        return self.repo.create_tipo(nombre)

    def actualizar_tipo(self, tipo_id: int, nombre: str) -> Dict[str, Any]:
        nombre = nombre.strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre del tipo no puede estar vacío")
        if not self.repo.get_tipo_by_id(tipo_id):
            raise HTTPException(status_code=404, detail="Tipo de prenda no encontrado")
        existente = self.repo.get_tipo_by_nombre(nombre)
        if existente and existente["tipo_id"] != tipo_id:
            raise HTTPException(status_code=400, detail=f"Ya existe un tipo con el nombre '{nombre}'")
        return self.repo.update_tipo(tipo_id, nombre)

    def eliminar_tipo(self, tipo_id: int) -> Dict[str, str]:
        if not self.repo.get_tipo_by_id(tipo_id):
            raise HTTPException(status_code=404, detail="Tipo de prenda no encontrado")
        if self.repo.tipo_tiene_inventario(tipo_id):
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar: el tipo tiene prendas vinculadas en lecturas_rfid",
            )
        self.repo.delete_tipo(tipo_id)
        return {"message": "Tipo de prenda eliminado correctamente"}

    # ── Tallas ───────────────────────────────────────────────────────────────

    def listar_tallas(self) -> List[Dict[str, Any]]:
        return self.repo.get_all_tallas()

    def crear_talla(self, nombre: str) -> Dict[str, Any]:
        nombre = nombre.strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre de la talla no puede estar vacío")
        if self.repo.get_talla_by_nombre(nombre):
            raise HTTPException(status_code=400, detail=f"Ya existe una talla con el nombre '{nombre}'")
        return self.repo.create_talla(nombre)

    def actualizar_talla(self, talla_id: int, nombre: str) -> Dict[str, Any]:
        nombre = nombre.strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre de la talla no puede estar vacío")
        if not self.repo.get_talla_by_id(talla_id):
            raise HTTPException(status_code=404, detail="Talla no encontrada")
        existente = self.repo.get_talla_by_nombre(nombre)
        if existente and existente["talla_id"] != talla_id:
            raise HTTPException(status_code=400, detail=f"Ya existe una talla con el nombre '{nombre}'")
        return self.repo.update_talla(talla_id, nombre)

    def eliminar_talla(self, talla_id: int) -> Dict[str, str]:
        if not self.repo.get_talla_by_id(talla_id):
            raise HTTPException(status_code=404, detail="Talla no encontrada")
        if self.repo.talla_tiene_inventario(talla_id):
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar: la talla tiene prendas vinculadas en lecturas_rfid",
            )
        self.repo.delete_talla(talla_id)
        return {"message": "Talla eliminada correctamente"}
