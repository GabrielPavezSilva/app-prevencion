"""
Siembra datos de demostración para probar los reportes y el dashboard (Fase 5).

SOLO PARA DESARROLLO. Genera entregas repartidas en los últimos 12 meses sobre
el personal ya sincronizado, para que el dashboard y los tres reportes tengan
algo que mostrar. Sin esto la base de desarrollo tiene un par de entregas y todo
se ve vacío.

Todo lo que crea queda marcado con observación 'SEED_DEMO' y se puede borrar con
`--limpiar` sin tocar los datos reales.

Uso (desde Backend/, con la base de desarrollo levantada):
    PYTHONIOENCODING=utf-8 PYTHONPATH=. venv/Scripts/python.exe tests/seed_demo_reportes.py
    PYTHONIOENCODING=utf-8 PYTHONPATH=. venv/Scripts/python.exe tests/seed_demo_reportes.py --limpiar
"""
import random
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text                                       # noqa: E402
from app.db.session import SessionLocal                           # noqa: E402
import app.models.inventario                                      # noqa: E402,F401
from app.repositories.entregas_repository import EntregasRepository  # noqa: E402
from app.repositories.epp_repository import EppRepository         # noqa: E402

MARCA = "SEED_DEMO"

# (categoría, producto, aplica talla, stock inicial, stock mínimo)
CATALOGO = [
    ("Protección cabeza",  "Casco de seguridad",     False, 120, 20),
    ("Protección auditiva", "Protector auditivo",    False, 300, 50),
    ("Protección visual",  "Antiparras",             False, 200, 40),
    ("Calzado",            "Zapato de seguridad",    True,   80, 25),
    ("Manos",              "Guante de nitrilo",      True,  400, 80),
    ("Manos",              "Guante anticorte",       True,   60, 30),
    ("Vestuario",          "Buzo de trabajo",        True,   90, 20),
    ("Protección respiratoria", "Mascarilla media cara", False, 45, 40),
]

TALLAS = ["S", "M", "L", "XL"]


def limpiar(db):
    """Borra solo lo sembrado por este script."""
    n_ent = db.execute(text(
        f"DELETE FROM entregas_epp WHERE observacion LIKE '{MARCA}%' RETURNING entrega_id"
    )).rowcount
    n_mov = db.execute(text(
        f"DELETE FROM movimientos_stock WHERE observacion LIKE '{MARCA}%' RETURNING movimiento_id"
    )).rowcount
    db.commit()
    print(f"Eliminadas {n_ent} entregas y {n_mov} movimientos marcados '{MARCA}'.")
    print("Los productos, categorías y stock NO se borran (pueden tener datos reales encima).")


def sembrar(db):
    epp = EppRepository(db)
    entregas = EntregasRepository(db)
    random.seed(42)   # reproducible: dos corridas generan el mismo reparto

    # ── Catálogo y stock ────────────────────────────────────────────────────
    tallas_id = {}
    for nombre in TALLAS:
        fila = db.execute(text("SELECT talla_id FROM tallas WHERE nombre_talla = :n"),
                          {"n": nombre}).fetchone()
        if fila:
            tallas_id[nombre] = fila[0]
        else:
            tallas_id[nombre] = db.execute(text(
                "INSERT INTO tallas (nombre_talla) VALUES (:n) RETURNING talla_id"
            ), {"n": nombre}).scalar()
    db.commit()

    productos = []
    for categoria, nombre, aplica_talla, cantidad, minimo in CATALOGO:
        cat_id = db.execute(text(
            "SELECT categoria_id FROM categorias_epp WHERE LOWER(nombre_categoria) = LOWER(:n)"
        ), {"n": categoria}).scalar()
        if not cat_id:
            cat_id = db.execute(text(
                "INSERT INTO categorias_epp (nombre_categoria) VALUES (:n) RETURNING categoria_id"
            ), {"n": categoria}).scalar()

        prod = epp.get_producto_by_nombre(nombre)
        if prod:
            prod_id = prod["producto_id"]
        else:
            prod_id = db.execute(text("""
                INSERT INTO productos_epp (nombre, categoria_id, talla_aplica, activo)
                VALUES (:n, :c, :t, TRUE) RETURNING producto_id
            """), {"n": nombre, "c": cat_id, "t": aplica_talla}).scalar()
        db.commit()

        destinos = [tallas_id[t] for t in TALLAS] if aplica_talla else [None]
        for talla_id in destinos:
            epp.ajustar_stock(prod_id, talla_id, cantidad, f"{MARCA} carga inicial", None)
            db.execute(text("""
                UPDATE stock_epp SET stock_minimo = :m
                WHERE producto_id = :p AND talla_id IS NOT DISTINCT FROM :t
            """), {"m": minimo, "p": prod_id, "t": talla_id})
        productos.append({"id": prod_id, "nombre": nombre, "talla_aplica": aplica_talla})
    db.commit()
    print(f"Catálogo: {len(productos)} productos con stock.")

    # ── Entregas repartidas en 12 meses ─────────────────────────────────────
    ruts = [r[0] for r in db.execute(text(
        "SELECT rut FROM personal WHERE COALESCE(activo, TRUE) ORDER BY rut"
    )).fetchall()]
    if not ruts:
        print("No hay personal activo. Corré primero el sync desde RRHH.")
        return

    # ~55% de la dotación recibe EPP; el resto queda sin nada a propósito, para
    # que el reporte de cobertura y el KPI 'sin EPP' tengan algo que mostrar.
    con_epp = random.sample(ruts, k=int(len(ruts) * 0.55))
    print(f"Personal activo: {len(ruts)} · reciben EPP: {len(con_epp)}")

    ahora = datetime.now()
    creadas, entregas_por_rut = 0, {}

    for rut in con_epp:
        trabajador = entregas.get_trabajador(rut)
        if not trabajador:
            continue
        for _ in range(random.randint(1, 3)):
            prod = random.choice(productos)
            talla_id = random.choice(list(tallas_id.values())) if prod["talla_aplica"] else None
            dias_atras = random.randint(0, 360)
            try:
                res = entregas.crear_entregas(trabajador, [{
                    "producto_id": prod["id"], "talla_id": talla_id,
                    "cantidad": 1, "motivo": "NUEVA",
                    "observacion": f"{MARCA} entrega inicial",
                }], None)
            except ValueError:
                continue   # sin stock: se ignora esa línea
            eid = res[0]["entrega_id"]
            # Se retrodata para poblar la serie mensual de los últimos 12 meses.
            db.execute(text("UPDATE entregas_epp SET fecha_entrega = :f WHERE entrega_id = :i"),
                       {"f": ahora - timedelta(days=dias_atras), "i": eid})
            entregas_por_rut.setdefault(rut, []).append((eid, prod, talla_id, dias_atras))
            creadas += 1
    db.commit()
    print(f"Entregas NUEVA: {creadas}")

    # ── Pérdidas y daños sobre entregas existentes ──────────────────────────
    perdidas = danos = 0
    candidatos = [r for r in entregas_por_rut if entregas_por_rut[r]]

    for rut in random.sample(candidatos, k=min(len(candidatos) // 6, len(candidatos))):
        eid, prod, talla_id, dias_atras = random.choice(entregas_por_rut[rut])
        trabajador = entregas.get_trabajador(rut)
        try:
            res = entregas.crear_entregas(trabajador, [{
                "producto_id": prod["id"], "talla_id": talla_id, "cantidad": 1,
                "motivo": "PERDIDA", "entrega_reemplazada_id": eid,
                "observacion": f"{MARCA} reposición por pérdida",
            }], None)
        except ValueError:
            continue
        db.execute(text("UPDATE entregas_epp SET fecha_entrega = :f WHERE entrega_id = :i"),
                   {"f": ahora - timedelta(days=max(dias_atras - random.randint(5, 60), 0)),
                    "i": res[0]["entrega_id"]})
        entregas_por_rut[rut] = [x for x in entregas_por_rut[rut] if x[0] != eid]
        perdidas += 1

    candidatos = [r for r in entregas_por_rut if entregas_por_rut[r]]
    for rut in random.sample(candidatos, k=min(len(candidatos) // 8, len(candidatos))):
        eid, prod, talla_id, dias_atras = random.choice(entregas_por_rut[rut])
        trabajador = entregas.get_trabajador(rut)
        try:
            res = entregas.crear_sustitucion(
                trabajador, eid, prod["id"], talla_id, 1,
                f"{MARCA} sustitución por daño", None, None)
        except ValueError:
            continue
        db.execute(text("UPDATE entregas_epp SET fecha_entrega = :f WHERE entrega_id = :i"),
                   {"f": ahora - timedelta(days=max(dias_atras - random.randint(5, 60), 0)),
                    "i": res["entrega_id"]})
        entregas_por_rut[rut] = [x for x in entregas_por_rut[rut] if x[0] != eid]
        danos += 1
    db.commit()
    print(f"Reposiciones por pérdida: {perdidas} · Sustituciones por daño: {danos}")

    # Un par de quiebres para que las alertas de stock no salgan vacías.
    for nombre in ("Mascarilla media cara", "Guante anticorte"):
        prod = epp.get_producto_by_nombre(nombre)
        if not prod:
            continue
        filas = db.execute(text("SELECT talla_id FROM stock_epp WHERE producto_id = :p"),
                           {"p": prod["producto_id"]}).fetchall()
        for (talla_id,) in filas[:2]:
            epp.ajustar_stock(prod["producto_id"], talla_id, 0, f"{MARCA} quiebre simulado", None)
    db.commit()
    print("Quiebres de stock simulados: 2 productos.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        destino = db.execute(text("SELECT current_database()")).scalar()
        print(f"Base destino: {destino}\n")
        if "--limpiar" in sys.argv:
            limpiar(db)
        else:
            sembrar(db)
            resumen = db.execute(text("""
                SELECT motivo, COUNT(*) lineas, SUM(cantidad) unidades
                FROM entregas_epp GROUP BY motivo ORDER BY motivo
            """)).fetchall()
            print("\nResumen de entregas en la base:")
            for motivo, lineas, unidades in resumen:
                print(f"  {motivo:8} {lineas:5} líneas  {unidades:5} unidades")
    finally:
        db.close()
