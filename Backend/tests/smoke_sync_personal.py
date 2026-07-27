"""
Smoke test del sync de personal (Fase 4) — Service → Repository.

Levanta el esquema desde el ORM en una base PostgreSQL desechable y ejercita el
sync contra la nómina REAL de RRHH (solo lectura). No usa TestClient por el
choque de versión de httpx del proyecto.

Uso:
    # 1. Base desechable
    docker run -d --name pg_smoke -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=db_smoke -p 55432:5432 postgres:16-alpine

    # 2. Túnel a RRHH (ver docs/runbook-sync-personal.md)
    ssh -N -L 5434:localhost:5432 <usuario>@192.9.200.12

    # 3. Correr desde Backend/
    PYTHONPATH=. venv/Scripts/python.exe tests/smoke_sync_personal.py

    # 4. Limpiar
    docker rm -f pg_smoke

Variables opcionales:
    SMOKE_DATABASE_URL   destino de prueba (default: localhost:55432/db_smoke)

CUIDADO: hace drop_all sobre la base destino. Nunca apuntarlo a una base real.
"""
import os
import sys
from datetime import datetime

os.environ["DATABASE_URL"] = os.getenv(
    "SMOKE_DATABASE_URL",
    "postgresql+psycopg2://postgres:test@localhost:55432/db_smoke",
)

from sqlalchemy import text                                     # noqa: E402
from app.db.session import Base, SessionLocal, engine           # noqa: E402
import app.models.inventario                                    # noqa: E402,F401
from app.repositories.personal_repository import PersonalRepository          # noqa: E402
from app.repositories.personal_sync_repository import PersonalSyncRepository  # noqa: E402
from app.services.personal_sync_service import (                # noqa: E402
    PersonalSyncService, normalizar_rut,
)

fallos = []


def check(nombre, condicion, detalle=""):
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}" + (f" — {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


def seccion(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def escalar(db, sql, **p):
    return db.execute(text(sql), p).scalar()


seccion("0. Esquema desde el modelo ORM")
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
db = SessionLocal()
check("personal.cargo es VARCHAR(100)",
      escalar(db, """SELECT character_maximum_length FROM information_schema.columns
                     WHERE table_name='personal' AND column_name='cargo'""") == 100)
check("areas sin UNIQUE solo sobre el nombre",
      escalar(db, "SELECT COUNT(*) FROM pg_constraint WHERE conname='areas_nombre_area_key'") == 0)
check("UNIQUE (nombre_area, empresa_id) presente",
      escalar(db, "SELECT COUNT(*) FROM pg_constraint WHERE conname='uq_areas_nombre_empresa'") == 1)

seccion("1. normalizar_rut")
check("DV a mayúscula", normalizar_rut("12.345.678-k") == "12.345.678-K")
check("recorta espacios", normalizar_rut("  9.876.543-2 ") == "9.876.543-2")
check("tolera None", normalizar_rut(None) == "")

seccion("2. dry_run no escribe")
r_dry = PersonalSyncService(db).sincronizar(dry_run=True)
check("leyó la nómina", r_dry["leidos"] > 500, f"leidos={r_dry['leidos']}")
check("no escribió", escalar(db, "SELECT COUNT(*) FROM personal") == 0)

seccion("3. Primera corrida real")
r1 = PersonalSyncService(db).sincronizar()
total = escalar(db, "SELECT COUNT(*) FROM personal")
print(f"  creados={r1['creados']} errores={len(r1['errores'])}")
for e in r1["errores"][:5]:
    print(f"    ! {e}")
check("insertó la nómina completa", total == r1["creados"], f"{total} filas")
check("sin errores por fila", len(r1["errores"]) == 0)
check("todos con sync_at", escalar(db, "SELECT COUNT(*) FROM personal WHERE sync_at IS NULL") == 0)
check("todos con buk_id", escalar(db, "SELECT COUNT(*) FROM personal WHERE buk_id IS NULL") == 0)
check("DV siempre en mayúscula", escalar(db, "SELECT COUNT(*) FROM personal WHERE rut ~ 'k$'") == 0)
check("empresa PRUEBA excluida",
      escalar(db, "SELECT COUNT(*) FROM empresa WHERE nombre_empresa='PRUEBA'") == 0)

seccion("4. Catálogos jerárquicos (no se fusionan por nombre)")
n_area = escalar(db, "SELECT COUNT(*) FROM areas")
n_sub = escalar(db, "SELECT COUNT(*) FROM subareas")
check("más filas de área que nombres distintos",
      n_area > escalar(db, "SELECT COUNT(DISTINCT nombre_area) FROM areas"))
check("más filas de subárea que nombres distintos",
      n_sub > escalar(db, "SELECT COUNT(DISTINCT nombre_subarea) FROM subareas"))
check("toda área con empresa", escalar(db, "SELECT COUNT(*) FROM areas WHERE empresa_id IS NULL") == 0)
check("toda subárea con origen_id",
      escalar(db, "SELECT COUNT(*) FROM subareas WHERE origen_id IS NULL") == 0)

seccion("5. Idempotencia")
r2 = PersonalSyncService(db).sincronizar()
check("no crea", r2["creados"] == 0)
check("no actualiza", r2["actualizados"] == 0)
check("todo sin cambios", r2["sin_cambios"] == total)
check("no duplica catálogos", escalar(db, "SELECT COUNT(*) FROM areas") == n_area)

seccion("6. Desvinculación conservando historial")
emp_id = escalar(db, "SELECT empresa_id FROM empresa LIMIT 1")
db.execute(text("""INSERT INTO personal (rut, nombre_completo, empresa_id, activo, sync_at)
                   VALUES ('1.111.111-1','Trabajador Desvinculado',:e,TRUE,:f)"""),
           {"e": emp_id, "f": datetime.now()})
db.execute(text("INSERT INTO categorias_epp (nombre_categoria) VALUES ('Test')"))
cat_id = escalar(db, "SELECT categoria_id FROM categorias_epp LIMIT 1")
db.execute(text("""INSERT INTO productos_epp (categoria_id, nombre, talla_aplica)
                   VALUES (:c,'Casco de prueba',FALSE)"""), {"c": cat_id})
prod_id = escalar(db, "SELECT producto_id FROM productos_epp LIMIT 1")
db.execute(text("""INSERT INTO entregas_epp (rut, nombre_completo, empresa_id, producto_id,
                                             cantidad, motivo, estado_firma)
                   VALUES ('1.111.111-1','Trabajador Desvinculado',:e,:p,1,'NUEVA','PENDIENTE')"""),
           {"e": emp_id, "p": prod_id})
db.commit()

r3 = PersonalSyncService(db).sincronizar()
check("desactivó al ausente", r3["desactivados"] == 1)
check("inactivo, no borrado",
      escalar(db, "SELECT activo FROM personal WHERE rut='1.111.111-1'") is False)
check("conservó su entrega",
      escalar(db, "SELECT COUNT(*) FROM entregas_epp WHERE rut='1.111.111-1'") == 1)

seccion("7. Reingreso")
rut_real = escalar(db, "SELECT rut FROM personal WHERE activo ORDER BY rut LIMIT 1")
db.execute(text("UPDATE personal SET activo=FALSE WHERE rut=:r"), {"r": rut_real})
db.commit()
r4 = PersonalSyncService(db).sincronizar()
check("reactivado", escalar(db, "SELECT activo FROM personal WHERE rut=:r", r=rut_real) is True)
check("cuenta como actualizado", r4["actualizados"] == 1 and r4["creados"] == 0)

seccion("8. RRHH pisa la edición local")
db.execute(text("UPDATE personal SET cargo='CARGO EDITADO' WHERE rut=:r"), {"r": rut_real})
db.commit()
r5 = PersonalSyncService(db).sincronizar()
check("detectó el cambio", r5["actualizados"] == 1)
check("restauró el valor de RRHH",
      escalar(db, "SELECT cargo FROM personal WHERE rut=:r", r=rut_real) != "CARGO EDITADO")

seccion("9. Guardarraíl: nómina vacía no desactiva a todos")
try:
    PersonalSyncRepository(db).desactivar_ausentes([], datetime.now())
    check("aborta con nómina vacía", False, "no lanzó excepción")
except ValueError:
    check("aborta con nómina vacía", True)
db.rollback()

seccion("10. Registro de corridas en `importaciones`")
check("cada corrida real registrada",
      escalar(db, "SELECT COUNT(*) FROM importaciones WHERE template_id='personal_sync'") == 5)

seccion("11. PersonalRepository (lo que consume la página)")
repo = PersonalRepository(db)
activos = repo.get_personal()
check("lista solo activos", len(activos) == total, f"{len(activos)} de {total}")
check("trae área y subárea", any(p.get("nombre_area") and p.get("nombre_subarea") for p in activos))
check("trae conteo de EPP vigentes", all("epp_vigentes" in p for p in activos))
check("incluir_inactivos suma al desvinculado",
      len(repo.get_personal(incluir_inactivos=True)) == total + 1)
uno = activos[0]
check("get_by_rut funciona", repo.get_by_rut(uno["rut"]) is not None)
check("búsqueda por RUT con puntos", len(repo.get_personal(search=uno["rut"])) == 1)
check("el desvinculado sigue consultable", repo.get_by_rut("1.111.111-1") is not None)
check("y conserva su EPP vigente", repo.get_by_rut("1.111.111-1")["epp_vigentes"] == 1)

db.close()

print(f"\n{'=' * 70}")
if fallos:
    print(f"FALLARON {len(fallos)} comprobaciones:")
    for f in fallos:
        print(f"  - {f}")
    sys.exit(1)
print("TODAS LAS COMPROBACIONES PASARON")
