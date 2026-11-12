from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src import config

# check_same_thread solo aplica a SQLite: FastAPI atiende cada petición en un hilo distinto.
_connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(config.DATABASE_URL, connect_args=_connect_args)

# Fábrica de sesiones: una sesión por petición HTTP.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: abre una sesión por petición y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
