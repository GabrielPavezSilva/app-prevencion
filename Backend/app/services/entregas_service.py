"""
Service del flujo de entregas de EPP — validaciones de negocio sobre
EntregasRepository. Traduce errores de negocio (ValueError) a HTTPException.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.repositories.entregas_repository import EntregasRepository
from app.repositories.epp_repository import EppRepository
from app.schemas.entregas import MOTIVOS_ENTREGA
from app.services.acta_pdf import firma_desde_data_url, construir_acta_maestra


class EntregasService:
    def __init__(self, db: Session):
        self.repo = EntregasRepository(db)
        self.epp = EppRepository(db)

    def _validar_producto_talla(self, producto_id: int, talla_id: Optional[int]) -> None:
        producto = self.epp.get_producto_by_id(producto_id)
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {producto_id} no encontrado")
        if not producto["activo"]:
            raise HTTPException(status_code=400, detail=f"El producto '{producto['nombre']}' está desactivado")
        if producto["talla_aplica"] and talla_id is None:
            raise HTTPException(status_code=400, detail=f"El producto '{producto['nombre']}' requiere talla")
        if not producto["talla_aplica"] and talla_id is not None:
            raise HTTPException(status_code=400, detail=f"El producto '{producto['nombre']}' no maneja tallas")

    def _get_trabajador(self, rut: str, solo_activos: bool = True) -> Dict[str, Any]:
        trabajador = self.repo.get_trabajador(rut, solo_activos)
        if not trabajador:
            detalle = (f"Trabajador con RUT {rut} no encontrado o inactivo" if solo_activos
                       else f"Trabajador con RUT {rut} no encontrado")
            raise HTTPException(status_code=404, detail=detalle)
        return trabajador

    # ── Entregas (NUEVA / PERDIDA) ───────────────────────────────────────────

    def crear_entregas(self, rut: str, lineas: List[Dict[str, Any]],
                       usuario_id: Optional[int], firma: str) -> List[Dict[str, Any]]:
        trabajador = self._get_trabajador(rut)
        try:
            firma_png = firma_desde_data_url(firma)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        for linea in lineas:
            if linea["motivo"] not in MOTIVOS_ENTREGA:
                raise HTTPException(
                    status_code=400,
                    detail=f"Motivo '{linea['motivo']}' inválido en entrega directa "
                           f"(use {' o '.join(MOTIVOS_ENTREGA)}; para daño use /sustitucion)",
                )
            if linea.get("entrega_reemplazada_id") is not None and linea["motivo"] != "PERDIDA":
                raise HTTPException(
                    status_code=400,
                    detail="Solo una línea con motivo PERDIDA puede vincular la entrega "
                           "que se dio por perdida",
                )
            self._validar_producto_talla(linea["producto_id"], linea.get("talla_id"))
        try:
            return self.repo.crear_entregas(trabajador, lineas, usuario_id, firma_png)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ── Sustitución (DANO) ───────────────────────────────────────────────────

    def crear_sustitucion(self, rut: str, entrega_reemplazada_id: int, producto_id: int,
                          talla_id: Optional[int], cantidad: int, observacion: Optional[str],
                          usuario_id: Optional[int], uuid: Optional[str],
                          firma: str) -> Dict[str, Any]:
        trabajador = self._get_trabajador(rut)
        self._validar_producto_talla(producto_id, talla_id)
        try:
            firma_png = firma_desde_data_url(firma)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        try:
            return self.repo.crear_sustitucion(
                trabajador=trabajador, entrega_reemplazada_id=entrega_reemplazada_id,
                producto_id=producto_id, talla_id=talla_id, cantidad=cantidad,
                observacion=observacion, usuario_id=usuario_id, uuid=uuid,
                firma_png=firma_png,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ── Consultas ────────────────────────────────────────────────────────────

    def listar_entregas(self, rut: Optional[str] = None, motivo: Optional[str] = None,
                        area_id: Optional[int] = None, desde: Optional[str] = None,
                        hasta: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.repo.get_entregas(rut, motivo, area_id, desde, hasta)

    def get_acta_pdf(self, acta_id: int) -> Dict[str, Any]:
        acta = self.repo.get_acta_pdf(acta_id)
        if not acta:
            raise HTTPException(status_code=404, detail=f"Acta {acta_id} no encontrada")
        return acta

    def get_acta_maestra_pdf(self, rut: str) -> Dict[str, Any]:
        """
        Documento maestro del trabajador. Se arma al vuelo con todas sus
        entregas firmadas: cada entrega nueva aparece sin reescribir nada, y no
        hay forma de que el archivo pierda registros anteriores.
        """
        trabajador = self._get_trabajador(rut, solo_activos=False)
        filas = self.repo.get_entregas_firmadas(rut)
        return {"trabajador": trabajador, "pdf": construir_acta_maestra(trabajador, filas)}

    def listar_vigentes(self, rut: str) -> List[Dict[str, Any]]:
        # Consulta de lectura: incluye desvinculados, que son justamente los que
        # pueden tener EPP sin devolver.
        self._get_trabajador(rut, solo_activos=False)
        return self.repo.get_vigentes_por_rut(rut)
