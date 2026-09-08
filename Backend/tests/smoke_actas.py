"""
Smoke test del acta de entrega y del documento maestro — Service → Repository.

Verifica que la firma quede guardada por acta y que el maestro del trabajador
acumule todas sus entregas firmadas sin perder las anteriores.

Uso:
    docker run -d --name pg_smoke -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=db_smoke -p 55432:5432 postgres:16-alpine
    PYTHONIOENCODING=utf-8 PYTHONPATH=. venv/Scripts/python.exe tests/smoke_actas.py
    docker rm -f pg_smoke

CUIDADO: hace drop_all sobre la base destino. Nunca apuntarlo a una base real.
"""
import base64
import os

os.environ["DATABASE_URL"] = os.getenv(
    "SMOKE_DATABASE_URL",
    "postgresql+psycopg2://postgres:test@localhost:55432/db_smoke",
)

from sqlalchemy import text                                        # noqa: E402
from app.db.session import Base, SessionLocal, engine              # noqa: E402
import app.models.inventario                                       # noqa: E402,F401
from app.services.entregas_service import EntregasService          # noqa: E402

FIRMA = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
PNG = base64.b64decode(FIRMA.split(",", 1)[1])

fallos = []


def check(nombre, condicion, detalle=""):
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}" + (f" — {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
db = SessionLocal()

db.execute(text("INSERT INTO empresa (empresa_id, nombre_empresa) VALUES (1,'Empresa Uno')"))
db.execute(text("INSERT INTO areas (area_id, nombre_area, empresa_id) VALUES (1,'Operaciones',1)"))
db.execute(text("""INSERT INTO personal (rut, nombre_completo, empresa_id, cargo, area_id, activo)
                   VALUES ('11.111.111-1','Ana Pérez',1,'Operaria',1,TRUE)"""))
db.execute(text("INSERT INTO categorias_epp (categoria_id, nombre_categoria) VALUES (1,'Protección cabeza')"))
db.execute(text("""INSERT INTO productos_epp (producto_id, nombre, categoria_id, talla_aplica,
                                              vida_util_meses, activo)
                   VALUES (1,'Casco',1,FALSE,24,TRUE),(2,'Guantes',1,FALSE,NULL,TRUE)"""))
db.execute(text("""INSERT INTO stock_epp (producto_id, talla_id, cantidad_actual, stock_minimo)
                   VALUES (1,NULL,10,0),(2,NULL,10,0)"""))
db.commit()

svc = EntregasService(db)

print("\n1. Primera entrega firmada")
creadas = svc.crear_entregas("11.111.111-1", [{"producto_id": 1, "cantidad": 1, "motivo": "NUEVA"}],
                             usuario_id=None, firma=FIRMA)
acta_id = creadas[0]["acta_id"]
check("acta creada", acta_id is not None)
check("firma guardada en el acta",
      bytes(db.execute(text("SELECT firma FROM actas_entrega WHERE acta_id = :i"), {"i": acta_id}).scalar()) == PNG)
check("PDF del acta generado", bytes(svc.get_acta_pdf(acta_id)["pdf"])[:5] == b"%PDF-")

print("\n2. Documento maestro tras la primera entrega")
maestro_1 = svc.get_acta_maestra_pdf("11.111.111-1")
check("área en el encabezado", maestro_1["trabajador"]["nombre_area"] == "Operaciones",
      str(maestro_1["trabajador"].get("nombre_area")))
check("PDF maestro generado", maestro_1["pdf"][:5] == b"%PDF-")

print("\n3. Segunda entrega: el maestro acumula, no reemplaza")
svc.crear_entregas("11.111.111-1", [{"producto_id": 2, "cantidad": 2, "motivo": "NUEVA"}],
                   usuario_id=None, firma=FIRMA)
filas = svc.repo.get_entregas_firmadas("11.111.111-1")
check("dos filas firmadas en el maestro", len(filas) == 2, f"filas={len(filas)}")
check("cada fila trae su firma", all(bytes(f["firma"]) == PNG for f in filas))
check("categoría y vida útil en la fila",
      filas[0]["nombre_categoria"] == "Protección cabeza" and filas[0]["vida_util_meses"] == 24)
check("producto sin vida útil no inventa recambio", filas[1]["vida_util_meses"] is None)
maestro_2 = svc.get_acta_maestra_pdf("11.111.111-1")
check("maestro crece con la segunda entrega", len(maestro_2["pdf"]) > len(maestro_1["pdf"]))

print("\n4. Trabajador sin entregas firmadas")
db.execute(text("""INSERT INTO personal (rut, nombre_completo, empresa_id, activo)
                   VALUES ('22.222.222-2','Sin Entregas',1,TRUE)"""))
db.commit()
check("maestro vacío no falla", svc.get_acta_maestra_pdf("22.222.222-2")["pdf"][:5] == b"%PDF-")

db.close()
print("\n" + ("FALLAS: " + ", ".join(fallos) if fallos else "TODO OK"))
raise SystemExit(1 if fallos else 0)
