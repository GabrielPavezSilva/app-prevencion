"""
Seed de módulos y asignaciones de módulos por rol.
Idempotente — seguro ejecutar múltiples veces.

Ejecutar: python seed_modulos.py
"""
import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

MODULOS = [
    "dashboard",
    "inventario",
    "entregas",
    "personal",
    "reportes",
    "configuracion",
    "superadmin",
]

# Módulos asignados a cada rol (admin siempre bypass en código — no se inserta aquí)
ROL_MODULOS = {
    "administrador": ["dashboard", "inventario", "entregas", "personal", "reportes", "configuracion"],
}

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
        "dbname": os.getenv("DB_NAME_PG", "db_lavanderia"),
    }

connection = psycopg2.connect(**conn_params)

try:
    with connection.cursor() as cursor:
        # 1. Insertar módulos
        for nombre in MODULOS:
            cursor.execute(
                "INSERT INTO modulos (nombre_modulo) VALUES (%s) ON CONFLICT (nombre_modulo) DO NOTHING",
                (nombre,)
            )
        print(f"Módulos: {len(MODULOS)} registros procesados.")

        # 2. Asignar módulos a roles worker
        asignaciones = 0
        for nombre_rol, modulos_rol in ROL_MODULOS.items():
            cursor.execute("SELECT rol_id FROM roles WHERE nombre_rol = %s", (nombre_rol,))
            row = cursor.fetchone()
            if not row:
                print(f"  [WARN] Rol '{nombre_rol}' no encontrado — ejecuta seed_admin.py primero.")
                continue
            rol_id = row[0]

            for nombre_modulo in modulos_rol:
                cursor.execute("SELECT modulo_id FROM modulos WHERE nombre_modulo = %s", (nombre_modulo,))
                mod = cursor.fetchone()
                if not mod:
                    print(f"  [WARN] Módulo '{nombre_modulo}' no encontrado.")
                    continue
                modulo_id = mod[0]

                cursor.execute(
                    """
                    INSERT INTO roles_modulos (rol_id, modulo_id)
                    VALUES (%s, %s)
                    ON CONFLICT (rol_id, modulo_id) DO NOTHING
                    """,
                    (rol_id, modulo_id)
                )
                asignaciones += 1

        print(f"Asignaciones rol→módulo: {asignaciones} registros procesados.")

    connection.commit()
    print("\nSeed completado exitosamente.")
    print("Nota: el rol 'admin' NO tiene entradas en roles_modulos — accede a todo por bypass en el código.")

except Exception as e:
    connection.rollback()
    print(f"Error: {type(e).__name__}: {str(e)}")
finally:
    connection.close()
