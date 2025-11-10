# panaderia_core/servicios/productos.py
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from panaderia_core.db.conexion import get_session
from panaderia_core.db.modelos import Producto, Role
from panaderia_core.security import require_role

router = APIRouter()


@router.get("/", response_model=List[Producto])
def listar_productos(
    incluir_inactivos: bool = False,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
):
    q = select(Producto)
    if not incluir_inactivos:
        q = q.where(Producto.activo == True)  # noqa: E712
    return session.exec(q.order_by(Producto.nombre.asc())).all()


@router.get("/{producto_id}", response_model=Producto)
def obtener_producto(
    producto_id: int,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
):
    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    return producto


@router.post("/", response_model=Producto, status_code=status.HTTP_201_CREATED)
def crear_producto(
    payload: Producto,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin)),
):
    # Usamos Producto como schema de entrada/salida (simple, como en el ejemplo del manual)
    nuevo = Producto(
        nombre=payload.nombre,
        categoria=payload.categoria,
        precio_venta=payload.precio_venta,
        costo_estimado=payload.costo_estimado,
        unidad_medida=payload.unidad_medida or "unidad",
        activo=payload.activo if payload.activo is not None else True,
        produccion_sugerida_base=payload.produccion_sugerida_base,
    )

    session.add(nuevo)
    session.commit()
    session.refresh(nuevo)
    return nuevo


@router.put("/{producto_id}", response_model=Producto)
def actualizar_producto(
    producto_id: int,
    payload: Producto,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin)),
):
    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    update_data = payload.dict(exclude_unset=True)
    for campo, valor in update_data.items():
        if campo == "id":
            continue
        setattr(producto, campo, valor)

    session.add(producto)
    session.commit()
    session.refresh(producto)
    return producto


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(
    producto_id: int,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin)),
):
    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    # Baja lógica para no perder histórico (importante para IA)
    producto.activo = False
    session.add(producto)
    session.commit()
    return
