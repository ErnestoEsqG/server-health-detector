from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Ruta de base de datos local SQLite (archivo: telemetry.db en la raiz)
DATABASE_URL = "sqlite:///./telemetry.db"

# Engine: El nucleo que gestiona las conexiones físicas a la base de datos
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} # Requerido especificamente para SQLite en FastAPI
)

# SessionLocal: Fabrica para instanciar sesiones de base de datos por cada peticion HTTP
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base: Clase declarativa base de la que heredarán nuestros modelos ORM
Base = declarative_base()

def get_db():
    """
    Generador de dependencia (Dependency Injection) para FastAPI.
    Abre una sesion por peticion y la cierra automaticamente al terminar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()