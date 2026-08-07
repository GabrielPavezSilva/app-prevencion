"""
Sincronización de `personal` desde la base de RRHH (Fase 4).

Flujo:
    rh_cramer (solo lectura)  →  normalizar  →  catálogos  →  upsert  →  bajas

RRHH es la fuente de verdad: pisa todos los campos, sin edición manual en
Prevención. Una corrida = una transacción sobre `db_prevencion`.
"""
import re
from contextlib import closing
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.logging_config import logger
from app.db.session_employees import EmployeesNotConfigured, get_employees_session
from app.repositories.employees_repository import EmployeesRepository
from app.repositories.personal_sync_repository import (
    CAMPOS_SINCRONIZADOS,
    PersonalSyncRepository,
)

_RUT_VALIDO = re.compile(r"^\d{1,3}(\.\d{3})*-[\dK]$")


def normalizar_rut(rut: Optional[str]) -> str:
    """
    Formato canónico `11.111.111-1`, que es el que usa RRHH en el 100% de los
    activos. Lo único que hay que corregir es el dígito verificador: 51 de los
    592 traen la `k` en minúscula.
    """
    if not rut:
        return ""
    return rut.strip().upper()


class PersonalSyncService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PersonalSyncRepository(db)

    def sincronizar(self, usuario_id: Optional[int] = None,
                    dry_run: bool = False) -> Dict[str, Any]:
        """
        Ejecuta el sync completo. Con `dry_run=True` calcula el resultado y hace
        rollback: sirve para revisar una corrida antes de escribir de verdad.
        """
        momento = datetime.now()
        logger.info(f"Iniciando sync de personal (dry_run={dry_run})")

        nomina = self._leer_nomina()

        errores: List[str] = []
        filas: List[Dict[str, Any]] = []
        vistos: Dict[str, str] = {}          # rut → nombre, para detectar duplicados

        cache_empresa: Dict[Any, int] = {}
        cache_area: Dict[Any, int] = {}
        cache_subarea: Dict[Any, int] = {}

        for emp in nomina:
            rut = normalizar_rut(emp.get("rut"))
            nombre = (emp.get("nombre_completo") or "").strip()

            if not rut:
                errores.append(f"'{nombre or 'sin nombre'}': viene sin RUT — omitido")
                continue
            if not _RUT_VALIDO.match(rut):
                errores.append(f"{rut}: formato de RUT inesperado — omitido")
                continue
            if rut in vistos:
                errores.append(f"{rut}: duplicado en la nómina ({vistos[rut]} / {nombre}) — omitido")
                continue
            if not nombre:
                errores.append(f"{rut}: viene sin nombre — omitido")
                continue

            empresa = (emp.get("empresa") or "").strip()
            if not empresa:
                # `personal.empresa_id` es NOT NULL: sin empresa no hay fila posible.
                errores.append(f"{rut} ({nombre}): sin empresa en el origen — omitido")
                continue

            try:
                empresa_id = self._resolver_empresa(cache_empresa, empresa,
                                                    emp.get("empresa_origen_id"))
                area_id = self._resolver_area(cache_area, emp, empresa_id)
                subarea_id = self._resolver_subarea(cache_subarea, emp, area_id)
            except Exception as e:
                errores.append(f"{rut} ({nombre}): error al resolver catálogos "
                               f"({type(e).__name__}: {e}) — omitido")
                continue

            vistos[rut] = nombre
            filas.append({
                "rut": rut,
                "nombre_completo": nombre[:100],
                "empresa_id": empresa_id,
                "cargo": (emp.get("cargo") or None),
                "area_id": area_id,
                "subarea_id": subarea_id,
                "url_picture": emp.get("url_picture"),
                "buk_id": emp.get("buk_id"),
            })

        resumen = self._aplicar(filas, momento, errores, usuario_id, dry_run)
        logger.info(f"Sync de personal finalizado: {resumen}")
        return resumen

    # ── Pasos internos ──────────────────────────────────────────────────────

    def _leer_nomina(self) -> List[Dict[str, Any]]:
        try:
            with closing(get_employees_session()) as sesion_rrhh:
                return EmployeesRepository(sesion_rrhh).get_nomina_activa()
        except EmployeesNotConfigured:
            raise
        except Exception as e:
            logger.error(f"No se pudo leer la nómina de RRHH: {type(e).__name__}: {e}")
            raise RuntimeError(
                f"No se pudo conectar a la base de RRHH ({type(e).__name__}). "
                "Verificá el túnel SSH y las credenciales."
            ) from e

    def _resolver_empresa(self, cache, nombre: str, origen_id) -> int:
        clave = origen_id if origen_id is not None else nombre
        if clave not in cache:
            cache[clave] = self.repo.get_or_create_empresa(nombre[:100], origen_id)
        return cache[clave]

    def _resolver_area(self, cache, emp: Dict[str, Any], empresa_id: int) -> Optional[int]:
        nombre = (emp.get("area") or "").strip()
        if not nombre:
            return None       # `area_id` es nullable desde la Fase 1
        clave = (empresa_id, nombre)
        if clave not in cache:
            cache[clave] = self.repo.get_or_create_area(
                nombre[:100], empresa_id, emp.get("area_origen_id")
            )
        return cache[clave]

    def _resolver_subarea(self, cache, emp: Dict[str, Any],
                          area_id: Optional[int]) -> Optional[int]:
        nombre = (emp.get("subarea") or "").strip()
        if not nombre or area_id is None:
            return None
        origen_id = emp.get("subarea_origen_id")
        clave = origen_id if origen_id is not None else (area_id, nombre)
        if clave not in cache:
            cache[clave] = self.repo.get_or_create_subarea(nombre[:100], area_id, origen_id)
        return cache[clave]

    def _aplicar(self, filas: List[Dict[str, Any]], momento: datetime,
                 errores: List[str], usuario_id: Optional[int],
                 dry_run: bool) -> Dict[str, Any]:
        """Clasifica contra el estado previo, escribe y arma el resumen."""
        previo = self.repo.snapshot_personal()

        creados, actualizados, sin_cambios = [], [], 0
        for f in filas:
            anterior = previo.get(f["rut"])
            if anterior is None:
                creados.append(f["rut"])
            elif self._cambio(anterior, f):
                actualizados.append(f["rut"])
            else:
                sin_cambios += 1

        try:
            self.repo.upsert_personal(filas, momento)
            desactivados = self.repo.desactivar_ausentes([f["rut"] for f in filas], momento)

            if dry_run:
                self.db.rollback()
                logger.info("dry_run=True — cambios revertidos")
            else:
                self.repo.registrar_corrida(
                    filas_ok=len(filas),
                    filas_error=len(errores),
                    detalle="\n".join(errores) if errores else None,
                    usuario_id=usuario_id,
                )
                self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "dry_run": dry_run,
            "fecha": momento,
            "leidos": len(filas) + len(errores),
            "creados": len(creados),
            "actualizados": len(actualizados),
            "sin_cambios": sin_cambios,
            "desactivados": len(desactivados),
            "errores": errores,
            "ruts_creados": creados[:50],
            "ruts_desactivados": desactivados[:50],
        }

    @staticmethod
    def _cambio(anterior: Dict[str, Any], nuevo: Dict[str, Any]) -> bool:
        """True si algún campo de RRHH difiere (o si la persona estaba inactiva)."""
        for campo in CAMPOS_SINCRONIZADOS:
            if campo == "activo":
                if not anterior.get("activo"):
                    return True          # reingreso: estaba inactivo y vuelve
                continue
            if anterior.get(campo) != nuevo.get(campo):
                return True
        return False

    def estado(self) -> Dict[str, Any]:
        """Última sincronización registrada — alimenta el encabezado de Personal."""
        return {"ultima_sincronizacion": self.repo.get_ultima_sincronizacion()}
