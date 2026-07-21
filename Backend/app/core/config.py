import os
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Software Prevencion EPP"

    # URL de base de datos completa (prioridad sobre campos individuales).
    # Formato: postgresql+psycopg2://user:pass@host:port/dbname
    # En Docker se inyecta esta variable directamente.
    DATABASE_URL: str = ""

    # Campos individuales de PostgreSQL (usados si DATABASE_URL no está definida)
    DB_HOST_PG: str = "localhost"
    DB_PORT_PG: int = 5432
    DB_USER_PG: str = ""
    DB_PASSWORD_PG: str = ""
    DB_NAME_PG: str = "db_prevencion"

    # Configuración JWT para autenticación
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 horas

    # Configuración API BUK - opcionales
    BUK_API_BASE_URL: str = ""
    BUK_API_KEY: str = ""

    # Token de BUK
    BUK_TOKEN: str = ""

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

# Instancia global de configuración
settings = Settings()