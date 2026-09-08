"""
Modelos ORM SQLAlchemy — dominio Prevención de Riesgos / Gestión de EPP.
Las tablas se auto-crean con Base.metadata.create_all (PostgreSQL).

Fase 1: modelo de datos del dominio EPP. Reemplaza el dominio de lavandería
(prendas con RFID) por stock de EPP por cantidades + libro mayor de movimientos.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint,
    LargeBinary
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


# ── Autenticación y permisos (sin cambios) ───────────────────────────────────

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


# ── Catálogos organizacionales (sin cambios) ─────────────────────────────────

class Empresa(Base):
    """
    Catálogo de empresas (multiempresa — D4).

    Fase 4: `origen_id` espeja `rh.areas.first_level_id` de la base `rh_cramer`.
    Los 5 nombres de empresa sí son únicos en el origen, así que `nombre_empresa`
    conserva su UNIQUE.
    """
    __tablename__ = "empresa"

    empresa_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_empresa = Column(String(100), nullable=False, unique=True)
    origen_id = Column(Integer, nullable=True, unique=True)


class Area(Base):
    """
    Catálogo de áreas (2º nivel de la jerarquía de RRHH).

    Fase 4: el nombre de área NO es único a nivel global — "Administración" y
    "Operaciones" existen en varias empresas (5 nombres repartidos en 16 filas
    reales del origen). Por eso el UNIQUE es (nombre_area, empresa_id) y no
    `nombre_area` solo: con el UNIQUE viejo las áreas de empresas distintas se
    fusionaban y el reporte por área sumaba empresas.

    `empresa_id` es nullable solo para no romper filas legacy anteriores al
    sync; toda fila creada por el sync la trae.
    """
    __tablename__ = "areas"
    __table_args__ = (
        UniqueConstraint("nombre_area", "empresa_id", name="uq_areas_nombre_empresa"),
    )

    area_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_area = Column(String(100), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.empresa_id"), nullable=True)
    origen_id = Column(Integer, nullable=True)   # rh.areas.second_level_id (tiene NULLs en origen)


class SubArea(Base):
    """
    Catálogo de subáreas (3er nivel — la unidad organizacional real).

    Fase 4: 71 nombres distintos sobre 163 unidades reales en el origen; el mismo
    nombre se repite incluso dentro de una misma empresa bajo áreas distintas.
    La identidad estable es `origen_id` = `rh.areas.id`, que sí es único global.
    """
    __tablename__ = "subareas"
    __table_args__ = (
        UniqueConstraint("nombre_subarea", "area_id", name="uq_subareas_nombre_area"),
    )

    subarea_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_subarea = Column(String(100), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.area_id"), nullable=True)
    origen_id = Column(Integer, nullable=True, unique=True)   # rh.areas.id


# ── Personal (adaptada — D1/D2) ──────────────────────────────────────────────

class Personal(Base):
    """
    Empleados / personal operativo.

    Adaptada en Fase 1:
      - empresa_id FK→empresa (se corrige el drift: el ORM anterior tenía un
        string, pero la BD y todos los repositories usan empresa_id).
      - area_id / subarea_id ahora NULL (el sync desde la base `employees`
        puede no traerlos para todos).
      - buk_id / sync_at nuevos (trazabilidad de sincronización, Fase 4).
      - SE ELIMINA huella_digital (poda biométrica) y talla_id (D2: la talla
        se elige manual en cada entrega, no se preserva en el trabajador).

    Fase 4: `cargo` pasa de VARCHAR(50) a VARCHAR(100) — `rh.employees.name_role`
    llega a 59 caracteres. `buk_id` guarda `rh.employees.person_id` (no `id`):
    el id de contrato cambia si alguien reingresa, el de persona no.
    """
    __tablename__ = "personal"

    rut = Column(String(20), primary_key=True)
    nombre_completo = Column(String(100), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.empresa_id"), nullable=False)
    cargo = Column(String(100), nullable=True)
    area_id = Column(Integer, ForeignKey("areas.area_id"), nullable=True)
    subarea_id = Column(Integer, ForeignKey("subareas.subarea_id"), nullable=True)
    url_picture = Column(String(500), nullable=True)
    activo = Column(Boolean, default=True)
    buk_id = Column(Integer, nullable=True)
    sync_at = Column(DateTime, nullable=True)

    entregas = relationship("EntregaEpp", back_populates="persona")


# ── Catálogo de tallas (se conserva) ─────────────────────────────────────────

class Talla(Base):
    """Catálogo de tallas (ampliable a tallas numéricas de calzado)."""
    __tablename__ = "tallas"

    TallaID = Column("talla_id", Integer, primary_key=True, autoincrement=True)
    nombreTalla = Column("nombre_talla", String(50), nullable=False, unique=True)


# ── Dominio EPP (nuevo) ──────────────────────────────────────────────────────

class CategoriaEpp(Base):
    """Categorías de EPP (ej: protección auditiva, calzado, protección cabeza)."""
    __tablename__ = "categorias_epp"

    categoria_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_categoria = Column(String(100), nullable=False, unique=True)

    productos = relationship("ProductoEpp", back_populates="categoria")


class ProductoEpp(Base):
    """Catálogo de productos EPP (una fila por tipo de EPP, no por unidad física)."""
    __tablename__ = "productos_epp"

    producto_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    categoria_id = Column(Integer, ForeignKey("categorias_epp.categoria_id"), nullable=True)
    talla_aplica = Column(Boolean, nullable=False, default=False)
    certificacion = Column(String(100), nullable=True)
    descripcion = Column(Text, nullable=True)
    # Vida util en meses: alimenta la "fecha probable de recambio" del acta.
    # NULL = el producto no tiene recambio programado.
    vida_util_meses = Column(Integer, nullable=True)
    activo = Column(Boolean, default=True)

    categoria = relationship("CategoriaEpp", back_populates="productos")


class StockEpp(Base):
    """
    Stock disponible por producto+talla. Stock GLOBAL (D4): un solo bodegón,
    sin segregación por empresa.

    Regla de oro: cantidad_actual NUNCA se edita directo desde la app; siempre
    cambia a través de un MovimientoStock (transacción atómica).
    """
    __tablename__ = "stock_epp"

    stock_id = Column(Integer, primary_key=True, autoincrement=True)
    producto_id = Column(Integer, ForeignKey("productos_epp.producto_id"), nullable=False)
    talla_id = Column(Integer, ForeignKey("tallas.talla_id"), nullable=True)
    cantidad_actual = Column(Integer, nullable=False, default=0)
    stock_minimo = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("producto_id", "talla_id", name="uq_stock_producto_talla"),
    )


class MovimientoStock(Base):
    """
    Libro mayor del stock: cada cambio de cantidad_actual deja un movimiento.
    El stock siempre es auditable reconstruyéndolo desde aquí.
    """
    __tablename__ = "movimientos_stock"

    movimiento_id = Column(Integer, primary_key=True, autoincrement=True)
    producto_id = Column(Integer, ForeignKey("productos_epp.producto_id"), nullable=False)
    talla_id = Column(Integer, ForeignKey("tallas.talla_id"), nullable=True)
    tipo = Column(String(20), nullable=False)   # INGRESO_IMPORT | ENTREGA | BAJA_DANO | AJUSTE
    cantidad = Column(Integer, nullable=False)  # positivo (ingreso) o negativo (salida)
    referencia_id = Column(Integer, nullable=True)  # entrega_id o importacion_id según tipo
    usuario_id = Column(Integer, ForeignKey("usuarios.user_id"), nullable=True)
    observacion = Column(Text, nullable=True)
    fecha = Column(DateTime, server_default=func.now())


class EntregaEpp(Base):
    """
    Entrega de EPP a un trabajador. Reemplaza a la antigua tabla `asignaciones`.

    empresa_id se denormaliza desde el trabajador al momento de la entrega
    (patrón de asignaciones) para habilitar reportes por empresa/área sin
    recalcular. La sustitución por daño (D5) usa entrega_reemplazada_id + un
    MovimientoStock tipo BAJA_DANO del ítem devuelto.
    """
    __tablename__ = "entregas_epp"

    entrega_id = Column(Integer, primary_key=True, autoincrement=True)
    rut = Column(String(20), ForeignKey("personal.rut"), nullable=False)
    nombre_completo = Column(String(100), nullable=False)   # denormalizado
    empresa_id = Column(Integer, ForeignKey("empresa.empresa_id"), nullable=True)  # denormalizado
    producto_id = Column(Integer, ForeignKey("productos_epp.producto_id"), nullable=False)
    talla_id = Column(Integer, ForeignKey("tallas.talla_id"), nullable=True)
    cantidad = Column(Integer, nullable=False, default=1)
    motivo = Column(String(20), nullable=False)   # NUEVA | PERDIDA | DANO
    entrega_reemplazada_id = Column(Integer, ForeignKey("entregas_epp.entrega_id"), nullable=True)
    estado_firma = Column(String(20), default="PENDIENTE")  # PENDIENTE | FIRMADA
    # Acta firmada que respalda esta entrega. Es NULL en las entregas cargadas
    # por importación histórica y en las anteriores a la firma en pantalla.
    acta_id = Column(Integer, ForeignKey("actas_entrega.acta_id"), nullable=True)
    usuario_entrega = Column(Integer, ForeignKey("usuarios.user_id"), nullable=True)
    observacion = Column(Text, nullable=True)
    fecha_entrega = Column(DateTime, server_default=func.now())
    # UUID generado por el cliente — idempotencia en sincronización offline (D3)
    uuid = Column(String(36), unique=True, nullable=True)

    persona = relationship("Personal", back_populates="entregas")


class ActaEntrega(Base):
    """
    Acta firmada de una entrega. Es **una por carrito**, no por línea: el
    trabajador firma un documento con todos los EPP que recibe en el acto, y
    las N filas de `entregas_epp` apuntan a ella con `acta_id`.

    El PDF se guarda en la base y no en disco a propósito: entra en el backup
    de la base sin volumen extra que montar, y un acta pesa ~10 KB.
    """
    __tablename__ = "actas_entrega"

    acta_id = Column(Integer, primary_key=True, autoincrement=True)
    rut = Column(String(20), ForeignKey("personal.rut"), nullable=False)
    nombre_completo = Column(String(100), nullable=False)   # denormalizado
    empresa_id = Column(Integer, ForeignKey("empresa.empresa_id"), nullable=True)
    pdf = Column(LargeBinary, nullable=False)
    # PNG de la firma, aparte del PDF: el documento maestro del trabajador se
    # regenera desde la base y necesita la firma de cada acta por separado.
    firma = Column(LargeBinary, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.user_id"), nullable=True)
    fecha_creacion = Column(DateTime, server_default=func.now())


class Importacion(Base):
    """Registro de cada carga masiva vía Excel (importadores)."""
    __tablename__ = "importaciones"

    importacion_id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(50), nullable=True)
    nombre_archivo = Column(String(255), nullable=True)
    filas_ok = Column(Integer, default=0)
    filas_error = Column(Integer, default=0)
    detalle_errores = Column(Text, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.user_id"), nullable=True)
    fecha = Column(DateTime, server_default=func.now())


class AuditoriaEpp(Base):
    """
    Auditoría genérica de ediciones/eliminaciones del dominio EPP.
    Reemplaza a `auditoria_prendas`; forma genérica (entidad + referencia)
    reutilizable para productos, entregas, stock o categorías.
    """
    __tablename__ = "auditoria_epp"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entidad = Column(String(20), nullable=False)        # PRODUCTO | ENTREGA | STOCK | CATEGORIA
    referencia = Column(String(100), nullable=False, index=True)  # id de la entidad afectada
    accion = Column(String(20), nullable=False)         # CREACION | EDICION | ELIMINACION | AJUSTE
    usuario_id = Column(Integer, nullable=True)
    usuario_nombre = Column(String(100), nullable=True)
    detalle = Column(Text, nullable=True)               # JSON con diff o snapshot
    fecha = Column(DateTime, server_default=func.now(), nullable=False)


# ── Sesión / seguridad (sin cambios) ─────────────────────────────────────────

class TokenBlacklist(Base):
    """JTIs de tokens invalidados por logout explícito."""
    __tablename__ = "token_blacklist"

    jti = Column(String(36), primary_key=True)           # UUID del token
    expires_at = Column(DateTime, nullable=False)         # Para limpieza periódica
