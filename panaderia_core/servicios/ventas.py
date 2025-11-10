# panaderia_core/servicios/ventas.py
from __future__ import annotations

from typing import List, Optional
from datetime import datetime, date, time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from panaderia_core.db.conexion import get_session
from panaderia_core.db.modelos import (
    Producto,
    Venta,
    ItemVenta,
    MedioPago,
    Role,
)
from panaderia_core.security import require_role

router = APIRouter()


# --------- Esquemas de entrada ---------

class VentaItemCreate(BaseModel):
    producto_id: int
    cantidad: float


class VentaCreate(BaseModel):
    items: List[VentaItemCreate]
    medio_pago: MedioPago
    fecha_hora: Optional[datetime] = None
    nota: Optional[str] = None


# --------- Helpers ---------

def _ensure_fecha_hora(fecha_hora: Optional[datetime]) -> datetime:
    if fecha_hora:
        return fecha_hora
    # Por defecto, ahora
    return datetime.utcnow()


def _parse_fecha_param(x: Optional[date | str]) -> Optional[date]:
    if x is None:
        return None
    if isinstance(x, date):
        return x
    try:
        return date.fromisoformat(str(x)[:10])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fecha inválida (usa YYYY-MM-DD)",
        )


# --------- Endpoints ---------

@router.get("/", response_model=List[Venta])
def listar_ventas(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
):
    q = select(Venta)

    fi = _parse_fecha_param(fecha_inicio)
    ff = _parse_fecha_param(fecha_fin)

    if fi:
        dt_ini = datetime.combine(fi, time.min)
        q = q.where(Venta.fecha_hora >= dt_ini)
    if ff:
        dt_fin = datetime.combine(ff, time.max)
        q = q.where(Venta.fecha_hora <= dt_fin)

    q = q.order_by(Venta.fecha_hora.desc(), Venta.id.desc())
    return session.exec(q).all()


@router.get("/{venta_id}", response_model=Venta)
def obtener_venta(
    venta_id: int,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
):
    venta = session.get(Venta, venta_id)
    if not venta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )
    # Gracias a expire_on_commit=False, las relaciones se pueden cargar al serializar
    return venta


@router.post("/", response_model=Venta, status_code=status.HTTP_201_CREATED)
def crear_venta(
    body: VentaCreate,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
):
    if not body.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La venta debe tener al menos un item",
        )

    # Creamos la venta sin total aún
    venta = Venta(
        fecha_hora=_ensure_fecha_hora(body.fecha_hora),
        medio_pago=body.medio_pago,
        total=0.0,
    )
    session.add(venta)
    session.flush()  # para tener venta.id

    total = 0.0

    for item_in in body.items:
        producto = session.get(Producto, item_in.producto_id)
        if not producto or not producto.activo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Producto inválido o inactivo (id={item_in.producto_id})",
            )

        if item_in.cantidad <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad debe ser > 0",
            )

        precio_unitario = producto.precio_venta
        subtotal = precio_unitario * item_in.cantidad
        total += subtotal

        item = ItemVenta(
            venta_id=venta.id,
            producto_id=producto.id,
            cantidad=item_in.cantidad,
            precio_unitario=precio_unitario,
            subtotal=subtotal,
        )
        session.add(item)

    venta.total = total
    session.add(venta)
    session.commit()
    session.refresh(venta)

    # Forzamos carga de items en la respuesta
    return venta
