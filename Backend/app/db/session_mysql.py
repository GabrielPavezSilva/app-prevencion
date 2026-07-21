from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Motor PostgreSQL (pool_pre_ping=True reconecta si la conexión se cae)
engine_mysql = create_engine(settings.get_database_url(), pool_pre_ping=True)

# Usar el método que configuramos para MySQL - transitorio
#engine_mysql = create_engine(settings.get_mysql_url(), pool_pre_ping=True)

# Fábrica de sesiones — nombre mantenido para compatibilidad con importaciones existentes
MysqlSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_mysql)
