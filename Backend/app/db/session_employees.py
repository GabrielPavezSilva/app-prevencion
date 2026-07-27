"""
Conexión a la base de RRHH (`rh_cramer`, schema `rh`) — fuente del sync de
personal (Fase 4).

Engine SEPARADO del principal y de solo lectura:
  - Si RRHH no responde, la transacción de `db_prevencion` no se ve arrastrada.
  - `postgresql_readonly` a nivel de sesión: aunque una query saliera mal
    escrita, el servidor rechaza cualquier escritura.

El engine se crea de forma perezosa (lazy): la app arranca aunque la base de
RRHH no esté configurada ni alcanzable — solo falla el endpoint de sync.
"""
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging_config import logger

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


class EmployeesNotConfigured(RuntimeError):
    """La base de RRHH no está configurada en el entorno."""


def _build_engine() -> Engine:
    url = settings.get_employees_url()
    if not url:
        raise EmployeesNotConfigured(
            "Falta la configuración de la base de RRHH. Definí EMPLOYEES_DATABASE_URL "
            "o EMPLOYEES_DB_USER/EMPLOYEES_DB_PASSWORD en el .env del backend."
        )
    logger.info("Creando engine de solo lectura hacia la base de RRHH")
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
        pool_recycle=1800,
        connect_args={"connect_timeout": 10},
        execution_options={"postgresql_readonly": True},
    )


def get_employees_session() -> Session:
    """
    Retorna una sesión nueva contra la base de RRHH.

    El llamador es responsable de cerrarla (usar `with closing(...)` o try/finally).
    Lanza EmployeesNotConfigured si falta configuración.
    """
    global _engine, _SessionLocal
    if _SessionLocal is None:
        _engine = _build_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _SessionLocal()
