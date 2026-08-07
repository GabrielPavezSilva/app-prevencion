from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Motor PostgreSQL (pool_pre_ping=True reconecta si la conexión se cae).
#
# `timezone=UTC` en la conexión NO es cosmético: las columnas de fecha son
# TIMESTAMP WITHOUT TIME ZONE con `server_default=now()`, y al guardar un
# timestamptz en una columna naive PostgreSQL lo convierte según la zona de
# la sesión. Sin fijarla, el mismo instante se guarda distinto según cómo esté
# configurado el servidor: el contenedor de desarrollo corre en UTC y el
# compose de producción arranca Postgres con timezone=America/Santiago, así
# que los reportes salían corridos 4 horas en producción.
#
# Fijándola acá, el almacenamiento es SIEMPRE UTC en todos los entornos y la
# conversión a hora de Chile ocurre en un solo lugar: la constante FECHA_LOCAL
# de app/repositories/reportes_repository.py.
engine_mysql = create_engine(
    settings.get_database_url(),
    pool_pre_ping=True,
    connect_args={"options": "-c timezone=UTC"},
)

# Usar el método que configuramos para MySQL - transitorio
#engine_mysql = create_engine(settings.get_mysql_url(), pool_pre_ping=True)

# Fábrica de sesiones — nombre mantenido para compatibilidad con importaciones existentes
MysqlSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_mysql)
