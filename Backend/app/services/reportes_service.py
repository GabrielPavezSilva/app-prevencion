"""
Service de reportabilidad EPP (Fase 5).

Principio: **una query por reporte, dos presentaciones**. Cada reporte tiene un
único método que devuelve `List[dict]` y una declaración de columnas; el JSON y
el Excel consumen exactamente las mismas filas, así que la tabla en pantalla y
el archivo exportado no pueden divergir.

Reemplaza por completo al ReportesService del dominio lavandería (mapas de
columnas de prendas + importador Excel obsoleto, que en Fase 3 pasó a
/api/importaciones).
"""
import io
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.repositories.reportes_repository import ReportesRepository
from app.services.excel_builder import Columna, ExcelBuilder

_FECHA = "dd-mm-yyyy"
_FECHA_HORA = "dd-mm-yyyy hh:mm"

_MOTIVO_LABEL = {"NUEVA": "Nueva", "PERDIDA": "Reposición por pérdida", "DANO": "Sustitución por daño"}


def _motivo(v: Any) -> Any:
    return _MOTIVO_LABEL.get(v, v)


COLUMNAS_TRAZABILIDAD = [
    Columna("fecha_entrega", "Fecha", ancho=17, formato=_FECHA_HORA),
    Columna("rut", "RUT", ancho=13),
    Columna("nombre_completo", "Trabajador", ancho=30),
    Columna("empresa", "Empresa", ancho=22),
    Columna("area", "Área", ancho=22),
    Columna("subarea", "Subárea", ancho=24),
    Columna("cargo", "Cargo", ancho=26),
    Columna("recinto", "Recinto", ancho=16),
    Columna("categoria", "Categoría", ancho=20),
    Columna("producto", "Producto", ancho=28),
    Columna("talla", "Talla", ancho=10),
    Columna("cantidad", "Cantidad", ancho=10),
    Columna("motivo", "Motivo", ancho=22, fmt=_motivo),
    Columna("entrega_reemplazada_id", "Reemplaza entrega", ancho=17),
    Columna("fecha_reemplazada", "Fecha reemplazada", ancho=17, formato=_FECHA),
    Columna("observacion", "Observación", ancho=34),
    Columna("registrado_por", "Registró", ancho=18),
]

COLUMNAS_VIGENTES = [
    Columna("rut", "RUT", ancho=13),
    Columna("nombre_completo", "Trabajador", ancho=30),
    Columna("empresa", "Empresa", ancho=22),
    Columna("area", "Área", ancho=22),
    Columna("subarea", "Subárea", ancho=24),
    Columna("cargo", "Cargo", ancho=26),
    Columna("activo", "Activo", ancho=8),
    Columna("recinto", "Recinto", ancho=16),
    Columna("categoria", "Categoría", ancho=20),
    Columna("producto", "Producto", ancho=28),
    Columna("talla", "Talla", ancho=10),
    Columna("cantidad", "Cantidad", ancho=10),
    Columna("motivo", "Motivo", ancho=22, fmt=_motivo),
    Columna("fecha_entrega", "Fecha entrega", ancho=15, formato=_FECHA),
    Columna("dias_desde_entrega", "Días desde entrega", ancho=17),
    Columna("sin_epp", "Sin EPP", ancho=9),
]

COLUMNAS_RESUMEN = [
    Columna("rut", "RUT", ancho=13),
    Columna("nombre_completo", "Trabajador", ancho=30),
    Columna("empresa", "Empresa", ancho=22),
    Columna("area", "Área", ancho=22),
    Columna("subarea", "Subárea", ancho=24),
    Columna("cargo", "Cargo", ancho=26),
    Columna("activo", "Activo", ancho=8),
    Columna("total_epp", "EPP vigentes", ancho=13),
    Columna("unidades", "Unidades", ancho=10),
    Columna("detalle", "Detalle", ancho=45),
]

COLUMNAS_STOCK = [
    Columna("recinto", "Recinto", ancho=16),
    Columna("categoria", "Categoría", ancho=20),
    Columna("producto", "Producto", ancho=30),
    Columna("talla", "Talla", ancho=10),
    Columna("cantidad_actual", "Stock actual", ancho=12),
    Columna("stock_minimo", "Stock mínimo", ancho=12),
    Columna("deficit", "Déficit", ancho=10),
    Columna("estado", "Estado", ancho=11),
    Columna("consumo", "Consumo periodo", ancho=15),
    Columna("cobertura_dias", "Cobertura (días)", ancho=15),
]


class ReportesService:
    def __init__(self, db: Session):
        self.repo = ReportesRepository(db)

    # ── R1 · Trazabilidad de entregas ────────────────────────────────────────

    def trazabilidad(self, filtros: Dict[str, Any],
                     limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.repo.trazabilidad_entregas(filtros, limit)

    def trazabilidad_excel(self, filtros: Dict[str, Any]) -> io.BytesIO:
        filas = self.trazabilidad(filtros)
        return (ExcelBuilder()
                .add_sheet("Trazabilidad", filas, COLUMNAS_TRAZABILIDAD)
                .build())

    # ── R2 · EPP vigentes por trabajador ─────────────────────────────────────

    def epp_vigentes(self, filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.repo.epp_vigentes(filtros)

    def epp_vigentes_excel(self, filtros: Dict[str, Any]) -> io.BytesIO:
        detalle = self.repo.epp_vigentes(filtros)
        resumen = self.repo.epp_vigentes_resumen(filtros)
        return (ExcelBuilder()
                .add_sheet("EPP vigentes", detalle, COLUMNAS_VIGENTES)
                .add_sheet("Resumen por trabajador", resumen, COLUMNAS_RESUMEN)
                .build())

    # ── R3 · Stock y quiebres ────────────────────────────────────────────────

    def stock(self, categoria_id: Optional[int] = None, solo_alertas: bool = False,
              dias_consumo: int = 90,
              recinto_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.repo.stock_quiebres(categoria_id, solo_alertas, dias_consumo, recinto_id)

    def stock_excel(self, categoria_id: Optional[int] = None, solo_alertas: bool = False,
                    dias_consumo: int = 90,
                    recinto_id: Optional[int] = None) -> io.BytesIO:
        filas = self.stock(categoria_id, solo_alertas, dias_consumo, recinto_id)
        return (ExcelBuilder()
                .add_sheet("Stock", filas, COLUMNAS_STOCK)
                .build())

    # ── Dashboard ────────────────────────────────────────────────────────────

    def dashboard(self, desde: Optional[str] = None, hasta: Optional[str] = None,
                  empresa_id: Optional[int] = None, area_id: Optional[int] = None,
                  meses: int = 12) -> Dict[str, Any]:
        """
        Los KPI, el donut de motivos y los rankings responden al periodo
        (`desde`/`hasta`). La serie mensual tiene ventana propia: los últimos
        `meses` terminando en el mes de `hasta` — las tarjetas muestran el
        periodo, el gráfico da el contexto alrededor.
        """
        if not desde and not hasta:
            hoy = date.today()
            desde = hoy.replace(day=1).isoformat()
            hasta = hoy.isoformat()

        filtros = {"desde": desde, "hasta": hasta,
                   "empresa_id": empresa_id, "area_id": area_id}

        entregas = self.repo.kpis_entregas(filtros)
        stock = self.repo.kpis_stock()
        personal = self.repo.kpis_personal()

        return {
            "periodo": {"desde": desde, "hasta": hasta},
            "kpis": {
                "entregas_periodo": entregas.get("unidades", 0),
                "lineas_periodo": entregas.get("lineas", 0),
                "reposiciones_perdida": entregas.get("unidades_perdida", 0),
                "sustituciones_dano": entregas.get("unidades_dano", 0),
                "trabajadores_atendidos": entregas.get("trabajadores_atendidos", 0),
                "productos_bajo_minimo": stock.get("bajo_minimo", 0),
                "productos_en_quiebre": stock.get("quiebre", 0),
                "unidades_en_bodega": stock.get("unidades_en_bodega", 0),
                "trabajadores_activos": personal.get("trabajadores_activos", 0),
                "trabajadores_sin_epp": personal.get("trabajadores_sin_epp", 0),
            },
            "serie_mensual": self.repo.serie_mensual(meses, hasta, filtros),
            "por_motivo": [
                {"nombre": _motivo(r["nombre"]), "cantidad": r["cantidad"]}
                for r in self.repo.por_motivo(filtros)
            ],
            "por_area": self.repo.por_area(filtros),
            "top_productos": self.repo.top_productos(filtros),
            "alertas_stock": self.repo.alertas_stock(),
        }
