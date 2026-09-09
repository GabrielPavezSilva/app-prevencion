"""
Smoke test del stock segregado por recinto — Service → Repository.

Cubre las cinco cosas que se pueden romper y que la UI no muestra:

1. El mismo producto+talla convive en varios recintos (UNIQUE de tres columnas).
2. Una entrega descuenta solo el stock de su recinto.
3. Un usuario de un recinto no puede mover el de otro (403).
4. Un rol de acceso total sin recinto propio tiene que elegirlo (400).
5. La BAJA_DANO de una sustitución se imputa al recinto de la entrega original.

Diseño: docs/plans/2026-09-09-stock-por-recinto-design.md

Uso:
    # 1. Base desechable
    docker run -d --name pg_smoke -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=db_smoke -p 55432:5432 postgres:16-alpine

    # 2. Correr desde Backend/
    PYTHONIOENCODING=utf-8 PYTHONPATH=. venv/Scripts/python.exe tests/smoke_recintos.py

    # 3. Limpiar
    docker rm -f pg_smoke

CUIDADO: hace drop_all sobre la base destino. Nunca apuntarlo a una base real.
"""
import base64
import os
import sys

os.environ["DATABASE_URL"] = os.getenv(
    "SMOKE_DATABASE_URL",
    "postgresql+psycopg2://postgres:test@localhost:55432/db_smoke",
)

from fastapi import HTTPException                          # noqa: E402
from sqlalchemy import text                                # noqa: E402
from app.db.session import Base, SessionLocal, engine      # noqa: E402
import app.models.inventario                               # noqa: E402,F401
from app.services.epp_service import EppService            # noqa: E402
from app.services.entregas_service import EntregasService  # noqa: E402

# PNG 1x1: el endpoint exige firma y el service la valida antes de tocar la base.
FIRMA = "data:image/png;base64," + base64.b64encode(base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)).decode()

fallos = []


def check(nombre, condicion, detalle=""):
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}" + (f" — {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


def seccion(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def escalar(db, sql, **p):
    return db.execute(text(sql), p).scalar()


def status_de(fn):
    """Corre `fn` y devuelve el status HTTP si levantó, o None si pasó."""
    try:
        fn()
    except HTTPException as e:
        return e.status_code
    return None


# ── 0. Esquema y datos base ──────────────────────────────────────────────────

seccion("0. Esquema y datos base")
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
db = SessionLocal()

# Sin IDs explícitos: el código bajo prueba inserta después por estas mismas
# tablas y, si la secuencia no avanzó, choca contra la PK por un motivo que no
# tiene nada que ver con lo que se está probando.
db.execute(text("INSERT INTO recintos (nombre_recinto) VALUES ('Las Encinas'), ('Lucerna')"))
db.execute(text("INSERT INTO tallas (nombre_talla) VALUES ('M')"))
db.execute(text("INSERT INTO categorias_epp (nombre_categoria) VALUES ('Cabeza')"))
db.execute(text("""INSERT INTO productos_epp (nombre, categoria_id, talla_aplica, activo)
                   SELECT 'Casco', categoria_id, FALSE, TRUE FROM categorias_epp"""))
db.execute(text("INSERT INTO empresa (nombre_empresa) VALUES ('Cramer')"))
db.execute(text("""INSERT INTO personal (rut, nombre_completo, empresa_id, cargo, activo)
                   SELECT '11111111-1', 'Ana Perez', empresa_id, 'Operaria', TRUE FROM empresa"""))
db.commit()

ENCINAS = escalar(db, "SELECT recinto_id FROM recintos WHERE nombre_recinto = 'Las Encinas'")
LUCERNA = escalar(db, "SELECT recinto_id FROM recintos WHERE nombre_recinto = 'Lucerna'")
CASCO = escalar(db, "SELECT producto_id FROM productos_epp WHERE nombre = 'Casco'")
check("datos base sembrados", all([ENCINAS, LUCERNA, CASCO]))

# Los tres perfiles de usuario de la tabla de permisos del diseño.
U_ENCINAS = {"userId": None, "role": "bodeguero", "recinto_id": ENCINAS}
U_LUCERNA = {"userId": None, "role": "bodeguero", "recinto_id": LUCERNA}
U_ADMIN = {"userId": None, "role": "admin", "recinto_id": None}

epp = EppService(db)
entregas = EntregasService(db)


# ── 1. El mismo producto convive en dos recintos ─────────────────────────────

seccion("1. El mismo producto convive en dos recintos")

epp.ajustar_stock(CASCO, None, 10, "carga inicial", None, U_ENCINAS)
epp.ajustar_stock(CASCO, None, 3, "carga inicial", None, U_LUCERNA)

check("dos filas de stock para el mismo producto sin talla",
      escalar(db, "SELECT COUNT(*) FROM stock_epp WHERE producto_id = :p", p=CASCO) == 2,
      "el UNIQUE de tres columnas no las separó")
check("Las Encinas quedó en 10",
      escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = :p AND recinto_id = :r",
              p=CASCO, r=ENCINAS) == 10)
check("Lucerna quedó en 3",
      escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = :p AND recinto_id = :r",
              p=CASCO, r=LUCERNA) == 3)
check("el listado sin filtro trae los dos recintos",
      len(epp.listar_stock()) == 2)
check("el listado filtrado trae solo uno",
      len(epp.listar_stock(recinto_id=LUCERNA)) == 1)


# ── 2. Permisos de escritura ─────────────────────────────────────────────────

seccion("2. Cada uno mueve solo su recinto")

check("un usuario de Lucerna no puede ajustar Las Encinas",
      status_de(lambda: epp.ajustar_stock(CASCO, None, 99, "intento", None,
                                          U_LUCERNA, recinto_id=ENCINAS)) == 403)
check("Las Encinas sigue en 10 después del intento",
      escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = :p AND recinto_id = :r",
              p=CASCO, r=ENCINAS) == 10)
check("un admin sin recinto propio tiene que elegirlo",
      status_de(lambda: epp.ajustar_stock(CASCO, None, 99, "intento", None, U_ADMIN)) == 400)
check("un usuario sin recinto asignado no puede mover nada",
      status_de(lambda: epp.ajustar_stock(
          CASCO, None, 99, "intento", None,
          {"userId": None, "role": "bodeguero", "recinto_id": None})) == 403)

# El admin sí puede, eligiendo.
epp.ajustar_stock(CASCO, None, 12, "ajuste del admin", None, U_ADMIN, recinto_id=ENCINAS)
check("el admin ajusta el recinto que eligió",
      escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = :p AND recinto_id = :r",
              p=CASCO, r=ENCINAS) == 12)
check("y no tocó el otro",
      escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = :p AND recinto_id = :r",
              p=CASCO, r=LUCERNA) == 3)


# ── 3. La entrega descuenta solo su recinto ──────────────────────────────────

seccion("3. La entrega descuenta solo su recinto")

creadas = entregas.crear_entregas(
    "11111111-1", [{"producto_id": CASCO, "talla_id": None, "cantidad": 2,
                    "motivo": "NUEVA", "observacion": None, "uuid": None,
                    "entrega_reemplazada_id": None}],
    usuario_id=None, firma=FIRMA, current_user=U_LUCERNA)

check("la entrega se creó", len(creadas) == 1)
check("la entrega quedó imputada a Lucerna",
      creadas[0]["recinto_id"] == LUCERNA, str(creadas[0].get("recinto_id")))
check("Lucerna bajó de 3 a 1",
      escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = :p AND recinto_id = :r",
              p=CASCO, r=LUCERNA) == 1)
check("Las Encinas quedó intacto en 12",
      escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = :p AND recinto_id = :r",
              p=CASCO, r=ENCINAS) == 12)
check("el movimiento ENTREGA lleva el recinto",
      escalar(db, """SELECT recinto_id FROM movimientos_stock
                     WHERE tipo = 'ENTREGA' ORDER BY movimiento_id DESC LIMIT 1""") == LUCERNA)

seccion("3b. El stock de otro recinto no alcanza para entregar")

# Lucerna tiene 1; pedir 5 no debe "prestarse" los 12 de Las Encinas.
check("pedir más de lo que hay en el recinto propio falla",
      status_de(lambda: entregas.crear_entregas(
          "11111111-1", [{"producto_id": CASCO, "talla_id": None, "cantidad": 5,
                          "motivo": "NUEVA", "observacion": None, "uuid": None,
                          "entrega_reemplazada_id": None}],
          usuario_id=None, firma=FIRMA, current_user=U_LUCERNA)) == 400)
check("y no descontó de ningún recinto",
      escalar(db, "SELECT SUM(cantidad_actual) FROM stock_epp WHERE producto_id = :p",
              p=CASCO) == 13)


# ── 4. El libro mayor cuadra por recinto ─────────────────────────────────────

seccion("4. El libro mayor cuadra recinto por recinto")

for nombre, rid in (("Las Encinas", ENCINAS), ("Lucerna", LUCERNA)):
    stock = escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = :p AND recinto_id = :r",
                    p=CASCO, r=rid)
    mayor = escalar(db, """SELECT COALESCE(SUM(cantidad), 0) FROM movimientos_stock
                           WHERE producto_id = :p AND recinto_id = :r
                             AND tipo IN ('INGRESO_IMPORT','ENTREGA','AJUSTE')""",
                    p=CASCO, r=rid)
    check(f"{nombre}: stock == suma de movimientos", stock == mayor, f"{stock} vs {mayor}")


# ── 5. La baja por daño va al recinto de la entrega original ──────────────────

seccion("5. La BAJA_DANO se imputa al recinto de la entrega original")

entrega_lucerna = creadas[0]["entrega_id"]
# Reponemos Lucerna para que la sustitución tenga de dónde salir.
epp.ajustar_stock(CASCO, None, 5, "reposición", None, U_LUCERNA)

# El admin registra la sustitución eligiendo Las Encinas: el reemplazo sale de
# ahí, pero la baja del ítem dañado pertenece a Lucerna, que fue quien entregó.
entregas.crear_sustitucion(
    rut="11111111-1", entrega_reemplazada_id=entrega_lucerna, producto_id=CASCO,
    talla_id=None, cantidad=1, observacion="casco partido", usuario_id=None,
    uuid=None, firma=FIRMA, current_user=U_ADMIN, recinto_id=ENCINAS)

check("la BAJA_DANO quedó en el recinto de la entrega original (Lucerna)",
      escalar(db, """SELECT recinto_id FROM movimientos_stock
                     WHERE tipo = 'BAJA_DANO' ORDER BY movimiento_id DESC LIMIT 1""") == LUCERNA)
check("el reemplazo descontó del recinto elegido (Las Encinas)",
      escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = :p AND recinto_id = :r",
              p=CASCO, r=ENCINAS) == 11)
check("BAJA_DANO no descontó stock de Lucerna",
      escalar(db, "SELECT cantidad_actual FROM stock_epp WHERE producto_id = :p AND recinto_id = :r",
              p=CASCO, r=LUCERNA) == 5)


# ── 6. El reporte de stock separa por recinto ────────────────────────────────

seccion("6. El reporte de stock separa por recinto")

from app.services.reportes_service import ReportesService  # noqa: E402

filas = ReportesService(db).stock()
check("el reporte trae una fila por recinto", len(filas) == 2, str(len(filas)))
check("cada fila nombra su recinto",
      sorted(f["recinto"] for f in filas) == ["Las Encinas", "Lucerna"],
      str([f.get("recinto") for f in filas]))
check("el consumo no se mezcla entre recintos",
      {f["recinto"]: f["consumo"] for f in filas}["Las Encinas"] == 1,
      str({f["recinto"]: f["consumo"] for f in filas}))


seccion("Resultado")
db.close()
if fallos:
    print(f"\n{len(fallos)} CHECK(S) FALLARON:")
    for f in fallos:
        print(f"  - {f}")
    sys.exit(1)
print("\nTodos los checks pasaron.")
