"""
Service del dominio EPP — validaciones de negocio sobre EppRepository.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.core.security import resolver_recinto
from app.repositories.epp_repository import EppRepository


class EppService:
    def __init__(self, db: Session):
        self.repo = EppRepository(db)

    # ── Categorías ───────────────────────────────────────────────────────────

    def listar_categorias(self) -> List[Dict[str, Any]]:
        return self.repo.get_all_categorias()

    def crear_categoria(self, nombre: str) -> Dict[str, Any]:
        nombre = (nombre or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre de la categoría no puede estar vacío")
        if self.repo.get_categoria_by_nombre(nombre):
            raise HTTPException(status_code=400, detail=f"Ya existe una categoría con el nombre '{nombre}'")
        return self.repo.create_categoria(nombre)

    def actualizar_categoria(self, categoria_id: int, nombre: str) -> Dict[str, Any]:
        nombre = (nombre or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre de la categoría no puede estar vacío")
        if not self.repo.get_categoria_by_id(categoria_id):
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        existente = self.repo.get_categoria_by_nombre(nombre)
        if existente and existente["categoria_id"] != categoria_id:
            raise HTTPException(status_code=400, detail=f"Ya existe una categoría con el nombre '{nombre}'")
        return self.repo.update_categoria(categoria_id, nombre)

    def eliminar_categoria(self, categoria_id: int) -> Dict[str, str]:
        if not self.repo.get_categoria_by_id(categoria_id):
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        if self.repo.categoria_tiene_productos(categoria_id):
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar: la categoría tiene productos vinculados",
            )
        self.repo.delete_categoria(categoria_id)
        return {"message": "Categoría eliminada correctamente"}

    # ── Productos ────────────────────────────────────────────────────────────

    def listar_productos(self, categoria_id: Optional[int] = None,
                         activo: Optional[bool] = None,
                         search: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.repo.get_all_productos(categoria_id, activo, search)

    def obtener_producto(self, producto_id: int) -> Dict[str, Any]:
        producto = self.repo.get_producto_by_id(producto_id)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return producto

    def crear_producto(self, data: Dict[str, Any]) -> Dict[str, Any]:
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre del producto no puede estar vacío")
        if self.repo.get_producto_by_nombre(nombre):
            raise HTTPException(status_code=400, detail=f"Ya existe un producto con el nombre '{nombre}'")
        if data.get("categoria_id") is not None and not self.repo.get_categoria_by_id(data["categoria_id"]):
            raise HTTPException(status_code=400, detail="La categoría indicada no existe")
        payload = {
            "nombre": nombre,
            "categoria_id": data.get("categoria_id"),
            "talla_aplica": bool(data.get("talla_aplica", False)),
            "certificacion": (data.get("certificacion") or None),
            "descripcion": (data.get("descripcion") or None),
            "vida_util_meses": data.get("vida_util_meses"),
        }
        return self.repo.create_producto(payload)

    def actualizar_producto(self, producto_id: int, fields: Dict[str, Any]) -> Dict[str, Any]:
        if not self.repo.get_producto_by_id(producto_id):
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        if "nombre" in fields and fields["nombre"] is not None:
            nombre = fields["nombre"].strip()
            if not nombre:
                raise HTTPException(status_code=400, detail="El nombre del producto no puede estar vacío")
            existente = self.repo.get_producto_by_nombre(nombre)
            if existente and existente["producto_id"] != producto_id:
                raise HTTPException(status_code=400, detail=f"Ya existe un producto con el nombre '{nombre}'")
            fields["nombre"] = nombre
        if fields.get("categoria_id") is not None and not self.repo.get_categoria_by_id(fields["categoria_id"]):
            raise HTTPException(status_code=400, detail="La categoría indicada no existe")
        return self.repo.update_producto(producto_id, fields)

    def eliminar_producto(self, producto_id: int) -> Dict[str, str]:
        if not self.repo.get_producto_by_id(producto_id):
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        if self.repo.producto_tiene_dependencias(producto_id):
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar: el producto tiene stock, movimientos o entregas. "
                       "Desactívelo en su lugar (activo = false).",
            )
        self.repo.delete_producto(producto_id)
        return {"message": "Producto eliminado correctamente"}

    # ── Stock y movimientos ──────────────────────────────────────────────────

    def listar_stock(self, producto_id: Optional[int] = None,
                     categoria_id: Optional[int] = None,
                     bajo_minimo: bool = False,
                     recinto_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Lectura: sin filtro trae los tres recintos, a propósito."""
        return self.repo.get_stock(producto_id, categoria_id, bajo_minimo, recinto_id)

    def listar_recintos(self) -> List[Dict[str, Any]]:
        return self.repo.get_recintos()

    def ajustar_stock(self, producto_id: int, talla_id: Optional[int],
                      cantidad_nueva: int, observacion: str,
                      usuario_id: Optional[int], current_user: Dict[str, Any],
                      recinto_id: Optional[int] = None) -> Dict[str, Any]:
        observacion = (observacion or "").strip()
        if not observacion:
            raise HTTPException(status_code=400, detail="La observación del ajuste es obligatoria")
        if cantidad_nueva < 0:
            raise HTTPException(status_code=400, detail="La cantidad no puede ser negativa")
        producto = self.repo.get_producto_by_id(producto_id)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        # Coherencia talla ↔ producto
        if producto["talla_aplica"] and talla_id is None:
            raise HTTPException(status_code=400, detail="Este producto requiere talla")
        if not producto["talla_aplica"] and talla_id is not None:
            raise HTTPException(status_code=400, detail="Este producto no maneja tallas")
        # Escritura: el recinto lo decide resolver_recinto, no el cliente.
        recinto = resolver_recinto(current_user, recinto_id)
        return self.repo.ajustar_stock(producto_id, talla_id, recinto,
                                       cantidad_nueva, observacion, usuario_id)

    def listar_movimientos(self, producto_id: Optional[int] = None,
                          tipo: Optional[str] = None,
                          recinto_id: Optional[int] = None,
                          desde: Optional[str] = None,
                          hasta: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.repo.get_movimientos(producto_id, tipo, desde, hasta)
