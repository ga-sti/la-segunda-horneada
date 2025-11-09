from typing import Optional
from sqlmodel import SQLModel, Field


class Producto(SQLModel, table=True):
    """
    Producto de panaderÃ­a: pan, factura, torta, etc.
    Este es solo un modelo inicial para probar la estructura.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    categoria: str
    precio: float
    activo: bool = Field(default=True)
