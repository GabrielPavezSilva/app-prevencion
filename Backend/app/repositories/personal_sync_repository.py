"""
Escritura del sync de personal (Fase 4): upsert de `personal` y get-or-create
de los catálogos organizacionales (`empresa` / `areas` / `subareas`).

Todo ocurre sobre la sesión de `db_prevencion`; la lectura de RRHH vive en
`employees_repository.py`. Una sola transacción por corrida — el commit lo hace
el service.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging_config import logger

# Campos de `personal` que el sync considera "de RRHH": si alguno difiere, la
# fila cuenta como actualizada. RRHH es la fuente de verdad y los pisa todos.
CAMPOS_SINCRONIZADOS = (
    "nombre_completo", "empresa_id", "cargo", "area_id",
    "subarea_id", "url_picture", "buk_id", "activo",
)


class PersonalSyncRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Catálogos ───────────────────────────────────────────────────────────

    def get_or_create_empresa(self, nombre: str, origen_id: Optional[int]) -> int:
        """
        Resuelve la empresa por `origen_id` (first_level_id) y, si no, por nombre.
        El origen tiene filas con first_level_id NULL, por eso el fallback.
        """
        if origen_id is not None:
            row = self.db.execute(
                text("SELECT empresa_id FROM empresa WHERE origen_id = :o"),
                {"o": origen_id},
            ).fetchone()
            if row:
                return row[0]

        row = self.db.execute(
            text("SELECT empresa_id, origen_id FROM empresa WHERE nombre_empresa = :n"),
            {"n": nombre},
        ).fetchone()
        if row:
            # Fila preexistente (carga manual): le adoptamos el id de origen.
            if origen_id is not None and row[1] is None:
                self.db.execute(
                    text("UPDATE empresa SET origen_id = :o WHERE empresa_id = :id"),
                    {"o": origen_id, "id": row[0]},
                )
            return row[0]

        return self.db.execute(
            text("""
                INSERT INTO empresa (nombre_empresa, origen_id)
                VALUES (:n, :o) RETURNING empresa_id
            """),
            {"n": nombre, "o": origen_id},
        ).scalar_one()

    def get_or_create_area(self, nombre: str, empresa_id: int,
                           origen_id: Optional[int]) -> int:
        """
        El área se identifica por (nombre, empresa_id): el mismo nombre existe en
        varias empresas y `second_level_id` tiene NULLs en el origen.
        """
        row = self.db.execute(
            text("""
                SELECT area_id, origen_id FROM areas
                WHERE nombre_area = :n AND empresa_id = :e
            """),
            {"n": nombre, "e": empresa_id},
        ).fetchone()
        if row:
            if origen_id is not None and row[1] is None:
                self.db.execute(
                    text("UPDATE areas SET origen_id = :o WHERE area_id = :id"),
                    {"o": origen_id, "id": row[0]},
                )
            return row[0]

        return self.db.execute(
            text("""
                INSERT INTO areas (nombre_area, empresa_id, origen_id)
                VALUES (:n, :e, :o) RETURNING area_id
            """),
            {"n": nombre, "e": empresa_id, "o": origen_id},
        ).scalar_one()

    def get_or_create_subarea(self, nombre: str, area_id: int,
                              origen_id: Optional[int]) -> int:
        """
        `origen_id` = `rh.areas.id`, único global — es la identidad estable de la
        unidad organizacional. Un renombre en RRHH actualiza el nombre acá en vez
        de crear una subárea duplicada.
        """
        if origen_id is not None:
            row = self.db.execute(
                text("SELECT subarea_id, nombre_subarea, area_id FROM subareas WHERE origen_id = :o"),
                {"o": origen_id},
            ).fetchone()
            if row:
                if row[1] != nombre or row[2] != area_id:
                    self.db.execute(
                        text("""
                            UPDATE subareas SET nombre_subarea = :n, area_id = :a
                            WHERE subarea_id = :id
                        """),
                        {"n": nombre, "a": area_id, "id": row[0]},
                    )
                return row[0]

        row = self.db.execute(
            text("""
                SELECT subarea_id, origen_id FROM subareas
                WHERE nombre_subarea = :n AND area_id = :a
            """),
            {"n": nombre, "a": area_id},
        ).fetchone()
        if row:
            if origen_id is not None and row[1] is None:
                self.db.execute(
                    text("UPDATE subareas SET origen_id = :o WHERE subarea_id = :id"),
                    {"o": origen_id, "id": row[0]},
                )
            return row[0]

        return self.db.execute(
            text("""
                INSERT INTO subareas (nombre_subarea, area_id, origen_id)
                VALUES (:n, :a, :o) RETURNING subarea_id
            """),
            {"n": nombre, "a": area_id, "o": origen_id},
        ).scalar_one()

    # ── Personal ────────────────────────────────────────────────────────────

    def snapshot_personal(self) -> Dict[str, Dict[str, Any]]:
        """Estado actual de `personal` indexado por RUT, para clasificar la corrida."""
        rows = self.db.execute(text("""
            SELECT rut, nombre_completo, empresa_id, cargo, area_id,
                   subarea_id, url_picture, buk_id, COALESCE(activo, TRUE) AS activo
            FROM personal
        """)).mappings().fetchall()
        return {r["rut"]: dict(r) for r in rows}

    def upsert_personal(self, filas: List[Dict[str, Any]], momento: datetime) -> None:
        """
        Upsert por RUT. RRHH pisa todos los campos sincronizados y siempre marca
        `activo = TRUE`: la fila viene de la nómina activa, así que un reingreso
        reactiva al trabajador conservando su historial de entregas.
        """
        if not filas:
            return
        self.db.execute(
            text("""
                INSERT INTO personal (rut, nombre_completo, empresa_id, cargo,
                                      area_id, subarea_id, url_picture,
                                      buk_id, activo, sync_at)
                VALUES (:rut, :nombre_completo, :empresa_id, :cargo,
                        :area_id, :subarea_id, :url_picture,
                        :buk_id, TRUE, :sync_at)
                ON CONFLICT (rut) DO UPDATE SET
                    nombre_completo = EXCLUDED.nombre_completo,
                    empresa_id      = EXCLUDED.empresa_id,
                    cargo           = EXCLUDED.cargo,
                    area_id         = EXCLUDED.area_id,
                    subarea_id      = EXCLUDED.subarea_id,
                    url_picture     = EXCLUDED.url_picture,
                    buk_id          = EXCLUDED.buk_id,
                    activo          = TRUE,
                    sync_at         = EXCLUDED.sync_at
            """),
            [{**f, "sync_at": momento} for f in filas],
        )

    def desactivar_ausentes(self, ruts_presentes: List[str], momento: datetime) -> List[str]:
        """
        Soft-delete de quienes ya no están en la nómina activa. Nunca DELETE:
        `entregas_epp` referencia `personal.rut` y el historial es el activo del
        sistema. Retorna los RUT desactivados en esta corrida.
        """
        if not ruts_presentes:
            # Una nómina vacía casi seguro es un error de la fuente, no 600 bajas.
            raise ValueError(
                "La nómina llegó vacía — se aborta para no desactivar a todo el personal."
            )
        rows = self.db.execute(
            text("""
                UPDATE personal
                SET activo = FALSE, sync_at = :sync_at
                WHERE COALESCE(activo, TRUE) = TRUE
                  AND rut <> ALL(:ruts)
                RETURNING rut
            """),
            {"ruts": ruts_presentes, "sync_at": momento},
        ).fetchall()
        return [r[0] for r in rows]

    def registrar_corrida(self, filas_ok: int, filas_error: int,
                          detalle: Optional[str], usuario_id: Optional[int]) -> None:
        """
        Deja la corrida en la tabla `importaciones` con template_id='personal_sync'
        (la columna es texto libre, sin FK) — reutiliza el historial que ya muestra
        la página Importaciones sin agregar tablas.
        """
        try:
            self.db.execute(
                text("""
                    INSERT INTO importaciones (template_id, nombre_archivo, filas_ok,
                                               filas_error, detalle_errores, usuario_id)
                    VALUES ('personal_sync', 'rh_cramer.rh.employees',
                            :ok, :err, :detalle, :usuario_id)
                """),
                {"ok": filas_ok, "err": filas_error,
                 "detalle": detalle, "usuario_id": usuario_id},
            )
        except Exception as e:
            # El log de la corrida no debe voltear el sync.
            logger.error(f"No se pudo registrar la corrida de sync: {type(e).__name__}: {e}")

    def get_ultima_sincronizacion(self) -> Optional[datetime]:
        return self.db.execute(text("SELECT MAX(sync_at) FROM personal")).scalar()
