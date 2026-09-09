"""
Seed de recintos: los tres con bodega propia.
Idempotente — seguro ejecutar múltiples veces.

No hay CRUD de recintos en la app: son tres y cambian cada varios años, así
que un cuarto se agrega a la lista de acá y se vuelve a correr el seed.

Ejecutar: python seed_recintos.py
"""
import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

RECINTOS = ["Las Encinas", "Lucerna", "Malloco"]

database_url = os.getenv("DATABASE_URL", "")
if database_url:
    parsed = urlparse(database_url)
    conn_params = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": parsed.username,
        "password": parsed.password,
        "dbname": parsed.path.lstrip("/"),
    }
else:
    conn_params = {
        "host": os.getenv("DB_HOST_PG", "localhost"),
        "port": int(os.getenv("DB_PORT_PG", "5432")),
        "user": os.getenv("DB_USER_PG", ""),
        "password": os.getenv("DB_PASSWORD_PG", ""),
        "dbname": os.getenv("DB_NAME_PG", "db_prevencion"),
    }

connection = psycopg2.connect(**conn_params)

try:
    with connection.cursor() as cursor:
        for nombre in RECINTOS:
            cursor.execute(
                "INSERT INTO recintos (nombre_recinto) VALUES (%s) "
                "ON CONFLICT (nombre_recinto) DO NOTHING",
                (nombre,),
            )
        cursor.execute("SELECT recinto_id, nombre_recinto FROM recintos ORDER BY recinto_id")
        for recinto_id, nombre in cursor.fetchall():
            print(f"  {recinto_id}  {nombre}")

    connection.commit()
    print(f"\nSeed completado: {len(RECINTOS)} recintos procesados.")
    print("Nota: los usuarios se asignan a un recinto desde SuperAdmin; sin recinto "
          "asignado, un usuario sin rol admin no puede mover stock.")

except Exception as e:
    connection.rollback()
    print(f"Error: {type(e).__name__}: {str(e)}")
finally:
    connection.close()
