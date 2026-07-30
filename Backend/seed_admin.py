"""
Script para insertar el usuario admin en la base de datos PostgreSQL.
Ejecutar una sola vez: python seed_admin.py
"""
import os
import psycopg2
from passlib.context import CryptContext
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

username = "admin"
email = "admin@prevencion.cl"
contrasena = "admin123"
role_name = "admin"

hashed_password = pwd_context.hash(contrasena)

# Soporte DATABASE_URL (Docker) o variables individuales
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
        # Asegurar que existan todos los roles del sistema
        for r in (role_name, "administrador"):
            cursor.execute(
                "INSERT INTO roles (nombre_rol) VALUES (%s) ON CONFLICT (nombre_rol) DO NOTHING",
                (r,)
            )

        cursor.execute(
            "SELECT rol_id FROM roles WHERE nombre_rol = %s", (role_name,)
        )
        rol = cursor.fetchone()
        if not rol:
            raise RuntimeError(f"No se pudo obtener el rol '{role_name}'")
        rol_id = rol[0]

        # Insertar o actualizar el usuario admin
        cursor.execute(
            """
            INSERT INTO usuarios (username, correo, contrasena, rol_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO UPDATE
              SET contrasena = EXCLUDED.contrasena,
                  correo     = EXCLUDED.correo,
                  rol_id     = EXCLUDED.rol_id
            """,
            (username, email, hashed_password, rol_id)
        )

    connection.commit()
    print(f"Usuario '{username}' listo en la base de datos.")
    print(f"  - Username : {username}")
    print(f"  - Password : {contrasena}")
    print(f"  - Rol      : {role_name}")

except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")
finally:
    connection.close()
