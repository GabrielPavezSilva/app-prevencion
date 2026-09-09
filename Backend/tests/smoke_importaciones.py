"""
Smoke test de las políticas de error de importación — Service → Repository.

Verifica las dos políticas de `_ATOMICOS`:

- `stock_inicial` / `ingreso_stock`: todo o nada. Una fila mala revierte el
  archivo completo, incluidas las filas que ya habían entrado.
- `productos_epp`: parcial. Las filas buenas quedan y las malas se reportan.

En ambos casos la importación se registra: el rastro del intento fallido es
justamente lo que hay que conservar.

Uso:
    # 1. Base desechable
    docker run -d --name pg_smoke -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=db_smoke -p 55432:5432 postgres:16-alpine

    # 2. Correr desde Backend/
    PYTHONIOENCODING=utf-8 PYTHONPATH=. venv/Scripts/python.exe tests/smoke_importaciones.py

    # 3. Limpiar
    docker rm -f pg_smoke

CUIDADO: hace drop_all sobre la base destino. Nunca apuntarlo a una base real.
"""
import io
import os
import sys

os.environ["DATABASE_URL"] = os.getenv(
    "SMOKE_DATABASE_URL",
    "postgresql+psycopg2://postgres:test@localhost:55432/db_smoke",
)

from openpyxl import Workbook                                     # noqa: E402
from sqlalchemy import text                                       # noqa: E402
from app.db.session import Base, SessionLocal, engine             # noqa: E402
import app.models.inventario                                      # noqa: E402,F401
from app.services.importaciones_service import ImportacionesService  # noqa: E402

fallos = []


def check(nombre, condicion, detalle=""):
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}" + (f" — {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


def seccion(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def escalar(db, sql, **p):
    return db.execute(text(sql), p).scalar()


def xlsx(encabezados, filas) -> bytes:
    """Arma un .xlsx en memoria, como el que sube el usuario."""
    wb = Workbook()
    wb.active.append(encabezados)
    for f in filas:
        wb.active.append(list(f))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── Esquema y catálogo mínimo ────────────────────────────────────────────────

seccion("0. Esquema y catálogo")
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
db = SessionLocal()

# Sin IDs explícitos: el service inserta después por estas mismas tablas y, si
# la secuencia no avanzó, el siguiente INSERT choca contra la PK.
# Talla 'M' existe; 'XL' NO — es la que va a hacer fallar las filas.
db.execute(text("INSERT INTO tallas (nombre_talla) VALUES ('M')"))
db.execute(text("INSERT INTO recintos (nombre_recinto) VALUES ('Las Encinas'), ('Lucerna')"))
db.execute(text("INSERT INTO categorias_epp (nombre_categoria) VALUES ('Cabeza')"))
db.execute(text("""INSERT INTO productos_epp (nombre, categoria_id, talla_aplica, activo)
                   SELECT 'Casco', categoria_id, FALSE, TRUE FROM categorias_epp
                   UNION ALL
                   SELECT 'Chaleco', categoria_id, TRUE, TRUE FROM categorias_epp"""))
db.commit()
check("catálogo sembrado", escalar(db, "SELECT COUNT(*) FROM productos_epp") == 2)

svc = ImportacionesService(db)

# ── 1. Stock: todo o nada ────────────────────────────────────────────────────

seccion("1. stock_inicial — una fila mala revierte todo")

COLS_STOCK = ["Recinto", "Producto", "Talla", "Cantidad", "Stock Mínimo"]
r = svc.procesar("stock_inicial", xlsx(COLS_STOCK, [
    ("Las Encinas", "Casco",   None, 10, 2),     # válida
    ("Las Encinas", "Chaleco", "M",  5,  1),     # válida
    ("Las Encinas", "Chaleco", "XL", 7,  1),     # la talla no existe → error
]), "stock.xlsx", usuario_id=None)

check("aplicado = False", r["aplicado"] is False, str(r["aplicado"]))
check("filas_ok reportadas en 0", r["filas_ok"] == 0, str(r["filas_ok"]))
check("1 fila con error", r["filas_error"] == 1, str(r["filas_error"]))
check("total cuenta las 3 filas", r["total"] == 3, str(r["total"]))
check("no quedó stock", escalar(db, "SELECT COUNT(*) FROM stock_epp") == 0)
check("no quedaron movimientos", escalar(db, "SELECT COUNT(*) FROM movimientos_stock") == 0)
check("el intento igual quedó registrado",
      escalar(db, "SELECT COUNT(*) FROM importaciones WHERE template_id='stock_inicial'") == 1)

seccion("2. stock_inicial — archivo sano sí entra")

r = svc.procesar("stock_inicial", xlsx(COLS_STOCK, [
    ("Las Encinas", "Casco",   None, 10, 2),
    ("Las Encinas", "Chaleco", "M",  5,  1),
]), "stock_ok.xlsx", usuario_id=None)

check("aplicado = True", r["aplicado"] is True)
check("2 filas OK", r["filas_ok"] == 2, str(r["filas_ok"]))
check("2 filas de stock", escalar(db, "SELECT COUNT(*) FROM stock_epp") == 2)
check("15 unidades en total", escalar(db, "SELECT SUM(cantidad_actual) FROM stock_epp") == 15)
check("libro mayor cuadra con el stock",
      escalar(db, "SELECT SUM(cantidad_actual) FROM stock_epp")
      == escalar(db, """SELECT SUM(cantidad) FROM movimientos_stock
                        WHERE tipo IN ('INGRESO_IMPORT','ENTREGA','AJUSTE')"""))

seccion("3. El rechazo no arrastra lo ya cargado")

r = svc.procesar("stock_inicial", xlsx(COLS_STOCK, [
    ("Las Encinas", "Casco",   None, 99, 2),     # válida, pero cae con el resto
    ("Las Encinas", "Chaleco", "XL", 7,  1),     # error
]), "stock_mixto.xlsx", usuario_id=None)

check("aplicado = False", r["aplicado"] is False)
check("el stock previo queda intacto en 15 unidades",
      escalar(db, "SELECT SUM(cantidad_actual) FROM stock_epp") == 15,
      str(escalar(db, "SELECT SUM(cantidad_actual) FROM stock_epp")))
check("no se sumó el ingreso de 99",
      escalar(db, "SELECT COUNT(*) FROM movimientos_stock WHERE cantidad = 99") == 0)

seccion("3b. Un recinto inválido revierte todo el archivo")

r = svc.procesar("stock_inicial", xlsx(COLS_STOCK, [
    ("Lucerna",  "Casco", None, 8, 2),     # válida, en el otro recinto
    ("Mallocco", "Casco", None, 8, 2),     # typo → el recinto no existe
]), "stock_recinto_malo.xlsx", usuario_id=None)

check("aplicado = False", r["aplicado"] is False)
check("el error nombra los recintos válidos",
      "Las Encinas" in (r.get("detalle_errores") or "") or
      any("Las Encinas" in e for e in (r.get("errores") or [])),
      str(r.get("detalle_errores") or r.get("errores")))
check("no entró la fila buena del recinto Lucerna",
      escalar(db, """SELECT COUNT(*) FROM stock_epp s JOIN recintos r
                     ON r.recinto_id = s.recinto_id
                     WHERE r.nombre_recinto = 'Lucerna'""") == 0)

seccion("3c. El mismo producto+talla convive en dos recintos")

r = svc.procesar("stock_inicial", xlsx(COLS_STOCK, [
    ("Lucerna", "Chaleco", "M", 4, 1),
]), "stock_lucerna.xlsx", usuario_id=None)

check("aplicado = True", r["aplicado"] is True, str(r.get("detalle_errores")))
check("Chaleco M existe en los dos recintos, sin chocar contra el UNIQUE",
      escalar(db, """SELECT COUNT(*) FROM stock_epp s
                     JOIN productos_epp p ON p.producto_id = s.producto_id
                     JOIN tallas t ON t.talla_id = s.talla_id
                     WHERE p.nombre = 'Chaleco' AND t.nombre_talla = 'M'""") == 2)
check("cada recinto tiene su propia cantidad",
      sorted(x[0] for x in db.execute(text(
          """SELECT s.cantidad_actual FROM stock_epp s
             JOIN productos_epp p ON p.producto_id = s.producto_id
             WHERE p.nombre = 'Chaleco'""")).fetchall()) == [4, 5])

# ── 4. Catálogo: política parcial ────────────────────────────────────────────

seccion("4. productos_epp — sigue siendo parcial")

r = svc.procesar("productos_epp", xlsx(
    ["Nombre", "Categoría", "Aplica Talla", "Certificación"], [
        ("Guantes", "Manos", "SI", "EN 388"),   # válida
        ("Casco",   "Cabeza", "NO", None),      # ya existe → error
        ("Botas",   "Calzado", "SI", None),     # válida
    ]), "productos.xlsx", usuario_id=None)

check("aplicado = True", r["aplicado"] is True)
check("2 filas OK", r["filas_ok"] == 2, str(r["filas_ok"]))
check("1 fila con error", r["filas_error"] == 1, str(r["filas_error"]))
check("las buenas quedaron", escalar(db, "SELECT COUNT(*) FROM productos_epp") == 4,
      str(escalar(db, "SELECT COUNT(*) FROM productos_epp")))

seccion("Resultado")
db.close()
if fallos:
    print(f"\n{len(fallos)} CHECK(S) FALLARON:")
    for f in fallos:
        print(f"  - {f}")
    sys.exit(1)
print("\nTodos los checks pasaron.")
