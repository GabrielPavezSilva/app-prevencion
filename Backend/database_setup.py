import sqlalchemy as db
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, PickleType

# Configuración de la Base de Datos
# Para MySQL en el futuro sería: 'mysql+mysqlconnector://user:pass@host/db_name'
ENGINE = db.create_engine('mysql+mysqlconnector://root:Benja2209.@localhost/db_lavanderia')
Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True)
    nombre_completo = Column(String(100))
    usuario = Column(String(50), unique=True)
    contrasena = Column(String(100)) # En produccion deberia estar hasheada
    rol = Column(String(50)) # Ej: "Almacenista", "Supervisor"
    # Aquí guardamos el vector biométrico (encoding) como bytes
    face_encoding = Column(PickleType) 

def inicializar_bd():
    """Crea las tablas si no existen"""
    Base.metadata.create_all(ENGINE)
    print("Base de datos inicializada correctamente.")

def get_session():
    """Devuelve una sesión para interactuar con la BD"""
    Session = sessionmaker(bind=ENGINE)
    return Session()

if __name__ == "__main__":
    inicializar_bd()