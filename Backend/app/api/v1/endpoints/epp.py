"""
Endpoints del dominio EPP — /api/epp
Categorías, productos, stock y movimientos. Patrón Endpoint → Service → Repository.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.deps import get_mysql_db
from app.core.security import get_current_user, require_module
from app.services.epp_service import EppService
from app.schemas.epp import (
    CategoriaCreate, CategoriaResponse,
    ProductoCreate, ProductoUpdate, ProductoResponse,
    StockResponse, AjusteStockRequest, MovimientoResponse, RecintoResponse,
)

router = APIRouter()


# ── Categorías ───────────────────────────────────────────────────────────────

@router.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(db: Session = Depends(get_mysql_db), _: dict = Depends(get_current_user)):
    return EppService(db).listar_categorias()


@router.post("/categorias", response_model=CategoriaResponse)
def crear_categoria(payload: CategoriaCreate, db: Session = Depends(get_mysql_db),
                    _: dict = Depends(require_module("inventario"))):
    return EppService(db).crear_categoria(payload.nombre_categoria)


@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
def actualizar_categoria(categoria_id: int, payload: CategoriaCreate,
                         db: Session = Depends(get_mysql_db),
                         _: dict = Depends(require_module("inventario"))):
    return EppService(db).actualizar_categoria(categoria_id, payload.nombre_categoria)


@router.delete("/categorias/{categoria_id}")
def eliminar_categoria(categoria_id: int, db: Session = Depends(get_mysql_db),
                       _: dict = Depends(require_module("inventario"))):
    return EppService(db).eliminar_categoria(categoria_id)


# ── Productos ────────────────────────────────────────────────────────────────

@router.get("/productos", response_model=List[ProductoResponse])
def listar_productos(categoria_id: Optional[int] = None,
                     activo: Optional[bool] = None,
                     search: Optional[str] = None,
                     db: Session = Depends(get_mysql_db),
                     _: dict = Depends(get_current_user)):
    return EppService(db).listar_productos(categoria_id, activo, search)


@router.get("/productos/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: int, db: Session = Depends(get_mysql_db),
                     _: dict = Depends(get_current_user)):
    return EppService(db).obtener_producto(producto_id)


@router.post("/productos", response_model=ProductoResponse)
def crear_producto(payload: ProductoCreate, db: Session = Depends(get_mysql_db),
                   _: dict = Depends(require_module("inventario"))):
    return EppService(db).crear_producto(payload.model_dump())


@router.put("/productos/{producto_id}", response_model=ProductoResponse)
def actualizar_producto(producto_id: int, payload: ProductoUpdate,
                        db: Session = Depends(get_mysql_db),
                        _: dict = Depends(require_module("inventario"))):
    return EppService(db).actualizar_producto(producto_id, payload.model_dump(exclude_unset=True))


@router.delete("/productos/{producto_id}")
def eliminar_producto(producto_id: int, db: Session = Depends(get_mysql_db),
                      _: dict = Depends(require_module("inventario"))):
    return EppService(db).eliminar_producto(producto_id)


# ── Stock ────────────────────────────────────────────────────────────────────

@router.get("/stock", response_model=List[StockResponse])
def listar_stock(producto_id: Optional[int] = None,
                 categoria_id: Optional[int] = None,
                 bajo_minimo: bool = Query(False, description="Solo ítems con cantidad ≤ stock mínimo"),
                 recinto_id: Optional[int] = Query(None, description="Filtra por recinto; sin él trae los tres"),
                 db: Session = Depends(get_mysql_db),
                 _: dict = Depends(get_current_user)):
    return EppService(db).listar_stock(producto_id, categoria_id, bajo_minimo, recinto_id)


@router.get("/recintos", response_model=List[RecintoResponse])
def listar_recintos(db: Session = Depends(get_mysql_db),
                    _: dict = Depends(get_current_user)):
    """Catálogo de recintos activos, para los selectores de la UI."""
    return EppService(db).listar_recintos()


@router.post("/stock/ajuste", response_model=StockResponse)
def ajustar_stock(payload: AjusteStockRequest, db: Session = Depends(get_mysql_db),
                  current_user: dict = Depends(require_module("inventario"))):
    return EppService(db).ajustar_stock(
        producto_id=payload.producto_id,
        talla_id=payload.talla_id,
        cantidad_nueva=payload.cantidad_nueva,
        observacion=payload.observacion,
        usuario_id=current_user.get("userId"),
        current_user=current_user,
        recinto_id=payload.recinto_id,
    )


# ── Movimientos ──────────────────────────────────────────────────────────────

@router.get("/movimientos", response_model=List[MovimientoResponse])
def listar_movimientos(producto_id: Optional[int] = None,
                       tipo: Optional[str] = None,
                       recinto_id: Optional[int] = Query(None, description="Filtra por recinto"),
                       desde: Optional[str] = Query(None, description="Fecha ISO desde (inclusive)"),
                       hasta: Optional[str] = Query(None, description="Fecha ISO hasta (inclusive)"),
                       db: Session = Depends(get_mysql_db),
                       _: dict = Depends(get_current_user)):
    return EppService(db).listar_movimientos(producto_id, tipo, recinto_id, desde, hasta)
