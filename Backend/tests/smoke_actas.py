"""
Smoke test del acta firmada de entrega — Service → Repository.

Verifica que el carrito genere UN acta por firma, que el PDF quede guardado y
vinculado a todas sus líneas, y que una firma inválida no registre nada.

Uso:
    docker run -d --name pg_smoke -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=db_smoke -p 55432:5432 postgres:16-alpine
    PYTHONIOENCODING=utf-8 PYTHONPATH=. venv/Scripts/python.exe tests/smoke_actas.py
    docker rm -f pg_smoke

CUIDADO: hace drop_all sobre la base destino. Nunca apuntarlo a una base real.
"""
import os
import base64

os.environ["DATABASE_URL"] = os.getenv(
    "SMOKE_DATABASE_URL",
    "postgresql+psycopg2://postgres:test@localhost:55432/db_smoke",
)

from fastapi import HTTPException                                    # noqa: E402
from sqlalchemy import text                                          # noqa: E402
from app.db.session import Base, SessionLocal, engine                # noqa: E402
import app.models.inventario                                         # noqa: E402,F401
from app.repositories.epp_repository import EppRepository            # noqa: E402
from app.services.entregas_service import EntregasService            # noqa: E402

fallos = []


def check(nombre, condicion, detalle=""):
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}" + (f" — {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


def seccion(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def escalar(db, sql, **p):
    return db.execute(text(sql), p).scalar()


def _falla_con(svc, acta_id):
    """Código HTTP con que el service rechaza un acta inexistente."""
    try:
        svc.get_acta_pdf(acta_id)
        return None
    except HTTPException as e:
        return e.status_code


# PNG 1x1 válido — hace de firma; lo que importa acá es el flujo, no el trazo.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
FIRMA = "data:image/png;base64," + base64.b64encode(PNG).decode()

seccion("0. Esquema desde el modelo ORM")
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
db = SessionLocal()
check("tabla actas_entrega creada", escalar(db, """
    SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'actas_entrega'
""") == 1)
check("entregas_epp.acta_id existe", escalar(db, """
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_name = 'entregas_epp' AND column_name = 'acta_id'
""") == 1)

seccion("1. Siembra")
db.execute(text("INSERT INTO empresa (empresa_id, nombre_empresa) VALUES (1,'Empresa Uno')"))
db.execute(text("INSERT INTO tallas (talla_id, nombre_talla) VALUES (1,'M')"))
db.execute(text("INSERT INTO categorias_epp (categoria_id, nombre_categoria) VALUES (1,'Cabeza')"))
db.execute(text("""INSERT INTO productos_epp (producto_id, nombre, categoria_id, talla_aplica, activo)
                   VALUES (1,'Casco',1,FALSE,TRUE),(2,'Botas',1,TRUE,TRUE)"""))
db.execute(text("""INSERT INTO personal (rut, nombre_completo, empresa_id, cargo, activo)
                   VALUES ('1-1','Ana Operaria',1,'Operaria',TRUE)"""))
db.commit()
epp = EppRepository(db)
epp.ajustar_stock(1, None, 20, "carga inicial", None)
epp.ajustar_stock(2, 1, 20, "carga inicial", None)
db.commit()

svc = EntregasService(db)

seccion("2. Carrito firmado -> un acta para las dos líneas")
creadas = svc.crear_entregas("1-1", [
    {"producto_id": 1, "talla_id": None, "cantidad": 1, "motivo": "NUEVA",
     "observacion": None, "uuid": None, "entrega_reemplazada_id": None},
    {"producto_id": 2, "talla_id": 1, "cantidad": 2, "motivo": "NUEVA",
     "observacion": None, "uuid": None, "entrega_reemplazada_id": None},
], usuario_id=None, firma=FIRMA)

check("dos entregas creadas", len(creadas) == 2, f"{len(creadas)}")
actas = {e["acta_id"] for e in creadas}
check("una sola acta para todo el carrito", len(actas) == 1 and None not in actas, f"{actas}")
check("estado_firma = FIRMADA en la respuesta",
      all(e["estado_firma"] == "FIRMADA" for e in creadas))
acta_id = creadas[0]["acta_id"]

check("acta_id persistido en ambas filas",
      escalar(db, "SELECT COUNT(*) FROM entregas_epp WHERE acta_id = :a", a=acta_id) == 2)
check("estado_firma persistido",
      escalar(db, "SELECT COUNT(*) FROM entregas_epp WHERE estado_firma = 'FIRMADA'") == 2)

seccion("3. El PDF quedó guardado y es legible")
acta = svc.get_acta_pdf(acta_id)
pdf = bytes(acta["pdf"])
check("es un PDF", pdf.startswith(b"%PDF-"), pdf[:8].decode("latin-1"))
check("tiene cuerpo", len(pdf) > 800, f"{len(pdf)} bytes")
check("acta denormaliza al trabajador", acta["nombre_completo"] == "Ana Operaria")
check("404 si el acta no existe", _falla_con(svc, 99999) == 404)

seccion("4. Sustitución por daño -> su propia acta")
id_casco = [e for e in creadas if e["producto_id"] == 1][0]["entrega_id"]
sus = svc.crear_sustitucion(
    rut="1-1", entrega_reemplazada_id=id_casco, producto_id=1, talla_id=None,
    cantidad=1, observacion="Casco trizado", usuario_id=None, uuid=None, firma=FIRMA,
)
check("acta propia, distinta de la del carrito",
      sus["acta_id"] is not None and sus["acta_id"] != acta_id, f"{sus['acta_id']} vs {acta_id}")
check("sustitución queda FIRMADA", sus["estado_firma"] == "FIRMADA")
check("PDF de la sustitución guardado",
      bytes(svc.get_acta_pdf(sus["acta_id"])["pdf"]).startswith(b"%PDF-"))
check("la baja por daño se registró",
      escalar(db, "SELECT COUNT(*) FROM movimientos_stock WHERE tipo = 'BAJA_DANO'") == 1)

try:
    svc.crear_sustitucion(rut="1-1", entrega_reemplazada_id=id_casco, producto_id=1,
                          talla_id=None, cantidad=1, observacion="x", usuario_id=None,
                          uuid=None, firma="no-firma")
    check("sustitución rechaza firma inválida", False, "no lanzó")
except HTTPException as e:
    check("sustitución rechaza firma inválida", e.status_code == 400, str(e.detail)[:50])
check("la sustitución fallida no dejó acta",
      escalar(db, "SELECT COUNT(*) FROM actas_entrega") == 2)

seccion("5. Firma inválida -> no se registra nada")
antes_entregas = escalar(db, "SELECT COUNT(*) FROM entregas_epp")
antes_stock = escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = 1")
for firma_mala in ("", "no-soy-una-firma", "data:image/jpeg;base64,AAAA"):
    try:
        svc.crear_entregas("1-1", [{"producto_id": 1, "talla_id": None, "cantidad": 1,
                                    "motivo": "NUEVA", "observacion": None, "uuid": None,
                                    "entrega_reemplazada_id": None}],
                           usuario_id=None, firma=firma_mala)
        check(f"rechaza firma {firma_mala[:20]!r}", False, "no lanzó")
    except HTTPException as e:
        check(f"rechaza firma {firma_mala[:20]!r}", e.status_code == 400, str(e.detail)[:60])
check("no se creó ninguna entrega",
      escalar(db, "SELECT COUNT(*) FROM entregas_epp") == antes_entregas)
check("no se movió el stock",
      escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = 1") == antes_stock)
check("no quedaron actas huérfanas",
      escalar(db, "SELECT COUNT(*) FROM actas_entrega") == 2)

seccion("Resultado")
if fallos:
    print(f"FALLARON {len(fallos)}: " + ", ".join(fallos))
    raise SystemExit(1)
print("Todos los checks pasaron.")
