from sqlalchemy.orm import declarative_base
from app.db.session_mysql import engine_mysql, MysqlSessionLocal  # noqa: F401

# Base declarativa compartida para todos los modelos ORM
Base = declarative_base()

# Alias canónicos usados por main.py y otros módulos
engine = engine_mysql
SessionLocal = MysqlSessionLocal