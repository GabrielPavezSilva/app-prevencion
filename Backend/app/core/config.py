from urllib.parse import quote_plus
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Software Prevencion EPP"

    # URL de base de datos completa (prioridad sobre campos individuales).
    # Formato: postgresql+psycopg2://user:pass@host:port/dbname
    # Los tres compose (prod, dev y staging) arman esta variable a partir de
    # POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB del .env y la inyectan:
    # dentro de Docker los campos DB_*_PG de abajo nunca se usan.
    DATABASE_URL: str = ""

    # Campos individuales de PostgreSQL. Solo aplican cuando DATABASE_URL está
    # vacía, es decir corriendo uvicorn a mano fuera de Docker.
    DB_HOST_PG: str = "localhost"
    DB_PORT_PG: int = 5432
    DB_USER_PG: str = ""
    DB_PASSWORD_PG: str = ""
    DB_NAME_PG: str = "db_prevencion"

    # Configuración JWT para autenticación
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 horas

    # ── Fuente del sync de personal (Fase 4) ────────────────────────────────
    # Base `rh_cramer` (schema `rh`), poblada desde Buk por el ETL de RRHH.
    # Solo lectura. En local se llega por túnel SSH:
    #   ssh -N -L 5434:localhost:5432 <usuario>@192.9.200.12
    # OJO: puerto local 5434, no 5433 — ahí vive el db_prevencion de desarrollo.
    # En producción el software corre en el mismo servidor: conexión directa.
    EMPLOYEES_DATABASE_URL: str = ""

    # Campos individuales (usados si EMPLOYEES_DATABASE_URL no está definida).
    # Preferirlos cuando la contraseña tiene caracteres que rompen una URL.
    EMPLOYEES_DB_HOST: str = "localhost"
    EMPLOYEES_DB_PORT: int = 5434
    EMPLOYEES_DB_USER: str = ""
    EMPLOYEES_DB_PASSWORD: str = ""
    EMPLOYEES_DB_NAME: str = "rh_cramer"

    # Entorno: "development" | "production"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # ignora vars de entorno ajenas (POSTGRES_*, VITE_*) en vez de crashear

    def get_database_url(self) -> str:
        """Retorna la URL de conexión a PostgreSQL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        pw = quote_plus(self.DB_PASSWORD_PG)
        return (
            f"postgresql+psycopg2://{self.DB_USER_PG}:{pw}"
            f"@{self.DB_HOST_PG}:{self.DB_PORT_PG}/{self.DB_NAME_PG}"
        )

    def get_employees_url(self) -> str:
        """
        URL de la base de RRHH (fuente del sync de personal).
        Retorna "" si no está configurada — el sync responde 503 en ese caso.
        """
        if self.EMPLOYEES_DATABASE_URL:
            return self.EMPLOYEES_DATABASE_URL
        if not (self.EMPLOYEES_DB_USER and self.EMPLOYEES_DB_PASSWORD):
            return ""
        pw = quote_plus(self.EMPLOYEES_DB_PASSWORD)
        return (
            f"postgresql+psycopg2://{self.EMPLOYEES_DB_USER}:{pw}"
            f"@{self.EMPLOYEES_DB_HOST}:{self.EMPLOYEES_DB_PORT}/{self.EMPLOYEES_DB_NAME}"
        )

# Instancia global de configuración
settings = Settings()