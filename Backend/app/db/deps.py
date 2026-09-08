from typing import Generator
from sqlalchemy.orm import Session
from app.db.session_mysql import MysqlSessionLocal


def get_mysql_db() -> Generator[Session, None, None]:
    """Dependencia para obtener sesión de BD MySQL en cada petición."""
    db = MysqlSessionLocal()
    try:
        yield db
    finally:
        db.close()