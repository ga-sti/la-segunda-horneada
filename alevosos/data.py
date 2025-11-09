# data.py - DB engine and session
from typing import Generator
from sqlmodel import SQLModel, Session, create_engine
import os

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, echo=False, connect_args=connect_args)

def init_db() -> None:
    import domain  # importa el módulo para registrar los modelos
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    # clave: expire_on_commit=False para evitar DetachedInstanceError
    with Session(engine, expire_on_commit=False) as session:
        yield session
