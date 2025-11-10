# panaderia_core/db/conexion.py
from typing import Generator
import os

from sqlmodel import SQLModel, Session, create_engine

# URL de la base de datos de la panadería.
# Puedes sobreescribirla con la variable de entorno PANADERIA_DB_URL
DB_URL = os.getenv("PANADERIA_DB_URL", "sqlite:///./datos_panaderia.db")

# Necesario para SQLite en modo multi-hilo (como en tu data.py original)
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}

engine = create_engine(DB_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    """
    Crea todas las tablas definidas en db.modelos si no existen.
    Similar a data.init_db(), pero apuntando a datos_panaderia.db
    """
    # Import tardío para registrar los modelos antes de create_all
    from panaderia_core.db import modelos  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """
    Devuelve una sesión de SQLModel para usar con Depends() en FastAPI.
    Usa expire_on_commit=False como en tu proyecto original.
    """
    with Session(engine, expire_on_commit=False) as session:
        yield session
