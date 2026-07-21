"""
Modelos ORM SQLAlchemy.
Mapean las tablas de db_lavanderia (MySQL).
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, LargeBinary, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class Rol(Base):
    """Roles para los distintos usuarios de la aplicación."""
    __tablename__ = "roles"

    rol_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_rol = Column(String(50), nullable=False, unique=True)

    usuarios = relationship("Usuario", back_populates="rol")
    modulos = relationship("RolModulo", back_populates="rol")


class Usuario(Base):
    """Usuarios habilitados de la plataforma (login)."""
    __tablename__ = "usuarios"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    correo = Column(String(100), nullable=False, unique=True)
    contrasena = Column(String(255), nullable=False)
    rol_id = Column(Integer, ForeignKey("roles.rol_id"), nullable=False)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, server_default=func.now())
    ultimo_login = Column(DateTime, server_default=func.now(), onupdate=func.now())

    rol = relationship("Rol", back_populates="usuarios")


class Modulo(Base):
    """Módulos de la aplicación."""
    __tablename__ = "modulos"

    modulo_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_modulo = Column(String(50), nullable=False, unique=True)

    roles = relationship("RolModulo", back_populates="modulo")


class RolModulo(Base):
    """Relación roles-módulos (permisos)."""
    __tablename__ = "roles_modulos"

    rol_id = Column(Integer, ForeignKey("roles.rol_id"), primary_key=True)
    modulo_id = Column(Integer, ForeignKey("modulos.modulo_id"), primary_key=True)

    rol = relationship("Rol", back_populates="modulos")
    modulo = relationship("Modulo", back_populates="roles")


class Area(Base):
    """Catálogo de áreas."""
    __tablename__ = "areas"

    area_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_area = Column(String(100), nullable=False, unique=True)


class SubArea(Base):
    """Catálogo de subáreas."""
    __tablename__ = "subareas"

    subarea_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_subarea = Column(String(100), nullable=False, unique=True)


class Empresa(Base):
    """Catálogo de empresas."""
    __tablename__ = "empresa"

    empresa_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_empresa = Column(String(100), nullable=False, unique=True)

    lecturas = relationship("LecturaRFID", back_populates="empresa_rel")


class Personal(Base):
    """Empleados / personal operativo."""
    __tablename__ = "personal"

    rut = Column(String(20), primary_key=True)
    nombre_completo = Column(String(100), nullable=False)
    empresa = Column(String(100), nullable=False)
    cargo = Column(String(50), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.area_id"), nullable=False)
    subarea_id = Column(Integer, ForeignKey("subareas.subarea_id"), nullable=False)
    talla_id = Column(Integer, ForeignKey("tallas.talla_id"), nullable=False)
    url_picture = Column(String(500), nullable=True)
    huella_digital = Column(LargeBinary, nullable=True)
    activo = Column(Boolean, default=True)

    asignaciones = relationship("Asignacion", back_populates="persona")


class TipoPrenda(Base):
    """Catálogo de tipos de prenda."""
    __tablename__ = "tiposprendas"

    TipoID = Column("tipo_id", Integer, primary_key=True, autoincrement=True)
    nombreTipo = Column("nombre_tipo", String(50), nullable=False, unique=True)

    lecturas = relationship("LecturaRFID", back_populates="tipo")


class Talla(Base):
    """Catálogo de tallas."""
    __tablename__ = "tallas"

    TallaID = Column("talla_id", Integer, primary_key=True, autoincrement=True)
    nombreTalla = Column("nombre_talla", String(50), nullable=False, unique=True)

    lecturas = relationship("LecturaRFID", back_populates="talla")


class Seccion(Base):
    """Catálogo de secciones (ej: cocina, salón, lavandería)."""
    __tablename__ = "secciones"

    SeccionID = Column("seccion_id", Integer, primary_key=True, autoincrement=True)
    nombreSeccion = Column("nombre_seccion", String(50), nullable=False, unique=True)

    lecturas = relationship("LecturaRFID", back_populates="seccion")


class Temporada(Base):
    """Catálogo de temporadas (ej: verano, invierno)."""
    __tablename__ = "temporadas"

    TemporadaID = Column("temporada_id", Integer, primary_key=True, autoincrement=True)
    nombreTemporada = Column("nombre_temporada", String(50), nullable=False, unique=True)

    lecturas = relationship("LecturaRFID", back_populates="temporada")


class LecturaRFID(Base):
    """
    Registro de lecturas RFID / inventario de prendas.
    Cada fila = una prenda física individual, identificada por SKU (UNIQUE).
    """
    __tablename__ = "lecturas_rfid"

    id_lectura = Column(Integer, primary_key=True, autoincrement=True)
    tag_epc = Column(String(50), nullable=False)
    sku = Column(String(100), nullable=False, unique=True)
    tipo_id = Column(Integer, ForeignKey("tiposprendas.tipo_id"), nullable=False)
    talla_id = Column(Integer, ForeignKey("tallas.talla_id"), nullable=False)
    seccion_id = Column(Integer, ForeignKey("secciones.seccion_id"), nullable=False)
    temporada_id = Column(Integer, ForeignKey("temporadas.temporada_id"), nullable=False)
    accion = Column(String(50), nullable=False)
    resultado = Column(String(50), nullable=False)
    estado_disponible = Column(Boolean, default=True)
    empresa_id = Column(Integer, ForeignKey("empresa.empresa_id"), nullable=False)
    hora = Column(DateTime, server_default=func.now())
    # UUID generado por el cliente — garantiza idempotencia en sincronización offline
    uuid = Column(String(36), unique=True, nullable=True)

    tipo = relationship("TipoPrenda", back_populates="lecturas")
    talla = relationship("Talla", back_populates="lecturas")
    seccion = relationship("Seccion", back_populates="lecturas")
    temporada = relationship("Temporada", back_populates="lecturas")
    empresa_rel = relationship("Empresa", back_populates="lecturas")


class Asignacion(Base):
    """Registro de entrega/devolución de prenda a un empleado."""
    __tablename__ = "asignaciones"

    asignacion_id = Column(Integer, primary_key=True, autoincrement=True)
    rut = Column(String(20), ForeignKey("personal.rut"), nullable=False)
    nombre_completo = Column(String(100), nullable=False)
    sku = Column(String(50), nullable=False)
    tag_epc = Column(String(50), nullable=False)
    fecha_entrega = Column(DateTime, server_default=func.now())
    fecha_devolucion = Column(DateTime, nullable=True)
    # UUID generado por el cliente — garantiza idempotencia en sincronización offline
    uuid = Column(String(36), unique=True, nullable=True)

    persona = relationship("Personal", back_populates="asignaciones")


class PrendaPredeterminada(Base):
    """Mapeo de prendas predeterminadas por cargo y empresa."""
    __tablename__ = "prendas_predeterminadas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cargo = Column(String(50), nullable=False)
    empresa = Column(String(100), nullable=False)
    tipo_id = Column(Integer, ForeignKey("tiposprendas.tipo_id"), nullable=False)

    tipo = relationship("TipoPrenda")


class AuditoriaPrenda(Base):
    """Registro de auditoría de ediciones y eliminaciones de prendas."""
    __tablename__ = "auditoria_prendas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(100), nullable=False, index=True)
    accion = Column(String(20), nullable=False)        # EDICION | ELIMINACION
    usuario_id = Column(Integer, nullable=True)
    usuario_nombre = Column(String(100), nullable=True)
    detalle = Column(Text, nullable=True)              # JSON con diff o snapshot
    fecha = Column(DateTime, server_default=func.now(), nullable=False)


class TokenBlacklist(Base):
    """JTIs de tokens invalidados por logout explícito."""
    __tablename__ = "token_blacklist"

    jti = Column(String(36), primary_key=True)          # UUID del token
    expires_at = Column(DateTime, nullable=False)        # Para limpieza periódica