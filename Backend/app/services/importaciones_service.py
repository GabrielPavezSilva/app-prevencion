"""
Service de importaciones EPP — parsea Excel/CSV y aplica cada fila en su propio
savepoint. Registra la importación y hace un único commit al final.

Hay dos políticas de error, según lo que toque el template (`_ATOMICOS`):

- **Parcial** (catálogos): una fila mala no aborta el resto. Cargar 28 de 30
  productos y corregir dos es más cómodo que rehacer el archivo entero, y el
  catálogo tolera estar incompleto un rato.
- **Todo o nada** (stock): si una sola fila falla, no se aplica ninguna. Un
  ingreso a medias deja el bodegón mintiendo, y como el ingreso es *aditivo*,
  reintentar el archivo corregido volvería a sumar las filas que sí habían
  entrado. Nadie se acuerda de recortar el Excel antes del segundo intento.
"""
import io
from typing import Optional, Dict, Any, List
import pandas as pd
from sqlalchemy.orm import Session

from app.repositories.importaciones_repository import ImportacionesRepository
from app.schemas.templates import DEFAULT_TEMPLATES
from app.core.logging_config import logger

# Templates que se aplican en bloque: o entran todas las filas, o ninguna.
_ATOMICOS = frozenset({"stock_inicial", "ingreso_stock"})

_MOTIVOS_HIST = ("NUEVA", "PERDIDA", "DANO")
_BOOL_TRUE = {"SI", "SÍ", "S", "TRUE", "1", "X", "V", "VERDADERO", "YES", "Y"}
_BOOL_FALSE = {"NO", "N", "FALSE", "0", "F", "FALSO"}


def _clean(v) -> Optional[str]:
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s or None


def _parse_int(v, campo: str, requerido: bool = True) -> Optional[int]:
    s = _clean(v)
    if s is None:
        if requerido:
            raise ValueError(f"'{campo}' es obligatorio")
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        raise ValueError(f"'{campo}' debe ser un número entero (valor: {s})")


def _parse_bool(v, campo: str) -> bool:
    s = _clean(v)
    if s is None:
        raise ValueError(f"'{campo}' es obligatorio (SI/NO)")
    u = s.upper()
    if u in _BOOL_TRUE:
        return True
    if u in _BOOL_FALSE:
        return False
    raise ValueError(f"'{campo}' debe ser SI o NO (valor: {s})")


def _parse_fecha(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        raise ValueError("'Fecha' es obligatoria")
    try:
        return pd.to_datetime(v, dayfirst=True).to_pydatetime()
    except Exception:
        raise ValueError(f"'Fecha' inválida (valor: {v})")


class ImportacionesService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ImportacionesRepository(db)

    # ── Orquestación ─────────────────────────────────────────────────────────

    def procesar(self, template_id: str, contenido: bytes, nombre_archivo: str,
                 usuario_id: Optional[int]) -> Dict[str, Any]:
        template = next((t for t in DEFAULT_TEMPLATES if t.id == template_id), None)
        if not template:
            raise ValueError(f"Template '{template_id}' no existe")

        try:
            if nombre_archivo.lower().endswith(".csv"):
                df = pd.read_csv(io.BytesIO(contenido))
            else:
                df = pd.read_excel(io.BytesIO(contenido))
        except Exception as e:
            logger.error(f"Error al leer archivo importado: {e}")
            raise ValueError("El archivo está corrupto o no se pudo leer.")

        requeridas = [c.name for c in template.columns if c.required]
        faltantes = [c for c in requeridas if c not in set(df.columns)]
        if faltantes:
            raise ValueError(f"Faltan columnas requeridas: {', '.join(faltantes)}")

        df = df.dropna(how="all")
        if df.empty:
            raise ValueError("El archivo no contiene datos para importar.")

        name_to_field = {c.name: c.field for c in template.columns}
        handler = {
            "productos_epp": self._row_productos,
            "stock_inicial": self._row_stock,
            "ingreso_stock": self._row_stock,
            "entregas_historicas": self._row_entregas_historicas,
        }[template_id]

        filas_ok, errores = 0, []
        for idx, fila in df.iterrows():
            r = {name_to_field[k]: v for k, v in fila.items() if k in name_to_field}
            fila_num = int(idx) + 2  # +1 header, +1 base-1
            try:
                with self.db.begin_nested():
                    handler(r, usuario_id)
                filas_ok += 1
            except ValueError as e:
                errores.append(f"Fila {fila_num}: {e}")
            except Exception as e:  # noqa: BLE001 — no romper el batch por un error inesperado
                logger.error(f"Import fila {fila_num}: {type(e).__name__}: {e}")
                errores.append(f"Fila {fila_num}: error inesperado ({type(e).__name__})")

        total = filas_ok + len(errores)

        # Todo o nada: se descartan también las filas que sí habían entrado. El
        # rollback deja la sesión limpia para registrar la importación fallida,
        # que es justamente lo que hay que conservar como rastro.
        aplicado = not (errores and template_id in _ATOMICOS)
        if not aplicado:
            self.db.rollback()
            logger.warning(
                f"Importación '{template_id}' revertida: {len(errores)} de {total} "
                f"filas con error (política todo o nada)"
            )
            filas_ok = 0

        detalle = "\n".join(errores) if errores else None
        importacion_id = self.repo.registrar_importacion(
            template_id, nombre_archivo, filas_ok, len(errores), detalle, usuario_id
        )
        self.db.commit()

        return {
            "importacion_id": importacion_id,
            "template_id": template_id,
            "total": total,
            "filas_ok": filas_ok,
            "filas_error": len(errores),
            "errores": errores,
            "aplicado": aplicado,
        }

    # ── Handlers por template ────────────────────────────────────────────────

    def _resolver_talla(self, prod: Dict[str, Any], talla_nombre: Optional[str]) -> Optional[int]:
        if prod["talla_aplica"]:
            if not talla_nombre:
                raise ValueError(f"el producto '{prod['nombre']}' requiere talla")
            talla_id = self.repo.get_talla_id(talla_nombre)
            if talla_id is None:
                raise ValueError(f"la talla '{talla_nombre}' no existe en el catálogo")
            return talla_id
        return None  # producto sin tallas: se ignora cualquier talla informada

    def _row_productos(self, r: Dict[str, Any], usuario_id: Optional[int]) -> None:
        nombre = _clean(r.get("nombre"))
        if not nombre:
            raise ValueError("'Nombre' es obligatorio")
        categoria = _clean(r.get("categoria"))
        if not categoria:
            raise ValueError("'Categoría' es obligatoria")
        talla_aplica = _parse_bool(r.get("talla_aplica"), "Aplica Talla")
        certificacion = _clean(r.get("certificacion"))

        if self.repo.get_producto(nombre):
            raise ValueError(f"el producto '{nombre}' ya existe")
        categoria_id = self.repo.get_categoria_id(categoria) or self.repo.crear_categoria(categoria)
        self.repo.crear_producto(nombre, categoria_id, talla_aplica, certificacion)

    def _row_stock(self, r: Dict[str, Any], usuario_id: Optional[int]) -> None:
        nombre = _clean(r.get("producto"))
        if not nombre:
            raise ValueError("'Producto' es obligatorio")
        prod = self.repo.get_producto(nombre)
        if not prod:
            raise ValueError(f"el producto '{nombre}' no existe (créelo primero)")
        cantidad = _parse_int(r.get("cantidad"), "Cantidad")
        if cantidad <= 0:
            raise ValueError("'Cantidad' debe ser mayor a 0")
        talla_id = self._resolver_talla(prod, _clean(r.get("talla")))
        stock_minimo = _parse_int(r.get("stock_minimo"), "Stock Mínimo", requerido=False)

        partes = []
        prov = _clean(r.get("proveedor"))
        obs = _clean(r.get("observacion"))
        if prov:
            partes.append(f"Proveedor: {prov}")
        if obs:
            partes.append(obs)
        observacion = " · ".join(partes) if partes else None

        self.repo.ingresar_stock(prod["producto_id"], talla_id, cantidad,
                                 stock_minimo, usuario_id, observacion)

    def _row_entregas_historicas(self, r: Dict[str, Any], usuario_id: Optional[int]) -> None:
        rut = _clean(r.get("rut"))
        if not rut:
            raise ValueError("'RUT' es obligatorio")
        trabajador = self.repo.get_trabajador(rut)
        if not trabajador:
            raise ValueError(f"el trabajador con RUT {rut} no existe")
        nombre = _clean(r.get("producto"))
        if not nombre:
            raise ValueError("'Producto' es obligatorio")
        prod = self.repo.get_producto(nombre)
        if not prod:
            raise ValueError(f"el producto '{nombre}' no existe")
        motivo = (_clean(r.get("motivo")) or "").upper()
        if motivo not in _MOTIVOS_HIST:
            raise ValueError(f"'Motivo' debe ser uno de {', '.join(_MOTIVOS_HIST)}")
        cantidad = _parse_int(r.get("cantidad"), "Cantidad", requerido=False) or 1
        if cantidad <= 0:
            raise ValueError("'Cantidad' debe ser mayor a 0")
        talla_id = self._resolver_talla(prod, _clean(r.get("talla")))
        fecha = _parse_fecha(r.get("fecha"))

        self.repo.insertar_entrega_historica(
            trabajador, prod["producto_id"], talla_id, cantidad, motivo, fecha, usuario_id
        )

    # ── Consulta ─────────────────────────────────────────────────────────────

    def listar_importaciones(self) -> List[Dict[str, Any]]:
        return self.repo.listar_importaciones()
