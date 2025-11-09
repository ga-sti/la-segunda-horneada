from sqlmodel import SQLModel, create_engine, Session

# MÃ¡s adelante podemos mover esta URL a variables de entorno
DATABASE_URL = "sqlite:///./datos_panaderia.db"

motor = create_engine(DATABASE_URL, echo=False)


def crear_base_de_datos() -> None:
    """Crea las tablas en la base de datos si no existen."""
    SQLModel.metadata.create_all(motor)


def obtener_sesion():
    """Dependencia para FastAPI: genera una sesiÃ³n de base de datos."""
    with Session(motor) as sesion:
        yield sesion
