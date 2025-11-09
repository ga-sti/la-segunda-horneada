# domain.py - enums and SQLModel tables
from __future__ import annotations
from typing import Optional
from datetime import date, datetime
from enum import Enum
from sqlmodel import SQLModel, Field


class Role(str, Enum):
    admin = "admin"
    barber = "barber"


class MedioPago(str, Enum):
    efectivo = "efectivo"
    transferencia = "transferencia"
    handy = "handy"


class CategoriaGasto(str, Enum):
    insumos = "insumos"
    alquiler = "alquiler"
    otro = "otro"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    full_name: Optional[str] = None
    hashed_password: str
    role: Role = Field(default=Role.admin)


class Cliente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    apellido: str
    edad: Optional[int] = None
    email: Optional[str] = Field(default=None, index=True)
    celular: Optional[str] = None


class Servicio(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    precio_referencial: Optional[float] = None
    activo: bool = True
    duracion_min: int = Field(default=30, description="Duración típica en minutos")  # NUEVO


class Producto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    precio: float
    stock: int = 0
    activo: bool = Field(default=True)


class Venta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: Optional[int] = Field(default=None, foreign_key="cliente.id")
    servicio_id: int = Field(foreign_key="servicio.id")
    monto: float
    medio_pago: MedioPago
    fecha: date
    nota: Optional[str] = None


class Gasto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    categoria: CategoriaGasto = Field(default=CategoriaGasto.otro)
    descripcion: Optional[str] = None
    monto: float
    fecha: date


class Caja(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: date = Field(index=True, unique=True)
    apertura: float
    cierre: Optional[float] = None
    observaciones: Optional[str] = None


class EstadoCita(str, Enum):
    agendada = "agendada"
    confirmada = "confirmada"
    completada = "completada"
    cancelada = "cancelada"
    no_show = "no_show"


class MedioReserva(str, Enum):
    online = "online"
    telefono = "telefono"
    walkin = "walkin"


class Cita(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(index=True)                # requerido en DB
    servicio_id: Optional[int] = Field(default=None, index=True)
    barber_id: int = Field(index=True)                 # User.id del barbero asignado
    inicio: datetime = Field(index=True)               # inicio (ISO 8601)
    duracion_min: int = Field(default=30)
    estado: EstadoCita = Field(default=EstadoCita.agendada)
    medio_reserva: MedioReserva = Field(default=MedioReserva.online)
    precio: Optional[float] = None
    notas: Optional[str] = None
