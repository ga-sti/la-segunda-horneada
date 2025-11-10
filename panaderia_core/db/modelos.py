# panaderia_core/db/modelos.py
from __future__ import annotations

from typing import Optional
from datetime import datetime, date
from enum import Enum

from sqlmodel import SQLModel, Field


# =========================
# Enums base
# =========================

class Role(str, Enum):
    """
    Roles de usuario en el sistema de panadería.
    """
    admin = "admin"
    empleado = "empleado"


class MedioPago(str, Enum):
    """
    Medios de pago usados en la panadería.
    """
    efectivo = "efectivo"
    transferencia = "transferencia"
    handy = "handy"


# =========================
# Usuarios
# =========================

class Usuario(SQLModel, table=True):
    """
    Usuario del sistema (para login y permisos).
    """
    __tablename__ = "usuarios"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    nombre: Optional[str] = Field(
        default=None,
        description="Nombre visible del usuario"
    )
    password_hash: str = Field(description="Hash de la contraseña")
    rol: Role = Field(default=Role.admin)
    activo: bool = Field(default=True)


# =========================
# Ventas e items de venta
# =========================

class Venta(SQLModel, table=True):
    """
    Encabezado de una venta.
    """
    __tablename__ = "ventas"

    id: Optional[int] = Field(default=None, primary_key=True)
    fecha_hora: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
        description="Momento de la venta"
    )
    medio_pago: MedioPago = Field(
        default=MedioPago.efectivo,
        description="Medio de pago usado"
    )
    total: float = Field(
        ge=0,
        description="Total de la venta (suma de items)"
    )

    # Opcional: quién cargó la venta
    usuario_id: Optional[int] = Field(
        default=None,
        foreign_key="usuarios.id",
        description="Usuario que registró la venta"
    )


class ItemVenta(SQLModel, table=True):
    """
    Detalle de cada producto vendido en una venta.
    """
    __tablename__ = "items_venta"

    id: Optional[int] = Field(default=None, primary_key=True)

    venta_id: int = Field(
        foreign_key="ventas.id",
        index=True,
        description="Venta a la que pertenece este item"
    )
    producto_id: int = Field(
        foreign_key="productos.id",
        index=True,
        description="Producto vendido en este item"
    )

    cantidad: float = Field(
        gt=0,
        description="Cantidad vendida"
    )
    precio_unitario: float = Field(
        gt=0,
        description="Precio unitario aplicado en la venta"
    )
    subtotal: float = Field(
        ge=0,
        description="cantidad * precio_unitario (guardado para histórico)"
    )


# =========================
# Productos
# =========================

class Producto(SQLModel, table=True):
    """
    Catálogo de productos de la panadería.
    """
    __tablename__ = "productos"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)
    categoria: Optional[str] = Field(
        default=None,
        description="Ej: pan, factura, bizcocho, torta, sandwich, etc."
    )
    precio_venta: float = Field(
        gt=0,
        description="Precio de venta al público"
    )
    costo_estimado: Optional[float] = Field(
        default=None,
        description="Costo de producción estimado por unidad"
    )
    unidad_medida: str = Field(
        default="unidad",
        description="unidad / kg / docena / bandeja"
    )
    activo: bool = Field(
        default=True,
        description="Permite dar de baja lógica sin perder histórico"
    )
    produccion_sugerida_base: Optional[float] = Field(
        default=None,
        description="Cantidad base sugerida (útil como semilla para IA)"
    )

    # NOTA:
    # Las relaciones ORM (items_venta, producciones) se pueden agregar más
    # adelante cuando tengamos la versión de SQLModel/SQLAlchemy bien alineada.


# =========================
# Producción diaria y contexto
# =========================

class ContextoDia(SQLModel, table=True):
    """
    Contexto del día en Artigas:
    clima, si es feriado, evento especial, etc.
    Sirve como feature para la IA.
    """
    __tablename__ = "contextos_dia"

    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: date = Field(index=True, unique=True)

    es_feriado: bool = Field(default=False)
    es_fin_de_semana: bool = Field(default=False)

    clima: Optional[str] = Field(
        default=None,
        description="soleado / lluvioso / frío / caluroso / etc."
    )
    evento_especial: Optional[str] = Field(
        default=None,
        description="Ej: partido, fecha patria, turismo, festival, etc."
    )
    comentario: Optional[str] = Field(
        default=None,
        description="Notas libres del día (barrio, flujo de gente, etc.)"
    )


class ProduccionDiaria(SQLModel, table=True):
    """
    Registro de producción, ventas y merma por producto y día.
    Es clave para BARB AI Core (qué se hizo, qué se vendió, qué sobró).
    """
    __tablename__ = "producciones_diarias"

    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: date = Field(index=True)

    producto_id: int = Field(
        foreign_key="productos.id",
        index=True,
        description="Producto al que corresponde este registro"
    )

    cantidad_producida: float = Field(
        ge=0,
        description="Cantidad que se produjo de este producto en el día"
    )
    cantidad_vendida: float = Field(
        ge=0,
        default=0,
        description="Cantidad vendida (puede calcularse o cargarse manualmente)"
    )
    cantidad_merma: float = Field(
        ge=0,
        default=0,
        description="Lo que quedó / se tiró / se endureció"
    )

    # Igual que arriba, relación con Producto se puede definir más adelante.
