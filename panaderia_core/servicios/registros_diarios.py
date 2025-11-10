# panaderia_core/servicios/registros_diarios.py

from __future__ import annotations

from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from panaderia_core.db.conexion import get_session
from panaderia_core.db.modelos import (
    Producto,
    ProduccionDiaria,
    ContextoDia,
    Role,
)
from panaderia_core.security import require_role

router = APIRouter()


# =========================
# Esquemas de entrada
# =========================

class ProduccionCreate(BaseModel):
    fecha: date
    producto_id: int
    cantidad_producida: float
    cantidad_vendida: Optional[float] = 0
    cantidad_merma: Optional[float] = 0


class ContextoDiaCreate(BaseModel):
    fecha: date
    es_feriado: bool = False
    # Si viene None, lo calculamos según la fecha (sábado/domingo)
    es_fin_de_semana: Optional[bool] = None
    clima: Optional[str] = None
    evento_especial: Optional[str] = None
    comentario: Optional[str] = None


# =========================
# PRODUCCIÓN DIARIA
# =========================

@router.post(
    "/produccion",
    response_model=ProduccionDiaria,
    status_code=status.HTTP_201_CREATED,
)
def registrar_produccion(
    body: ProduccionCreate,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
):
    """
    Registra o actualiza la producción de un producto en una fecha dada.
    Clave lógica: (fecha, producto_id).
    """

    # 1) Validar que el producto exista y esté activo
    producto = session.get(Producto, body.producto_id)
    if not producto or not producto.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Producto inválido o inactivo (id={body.producto_id})",
        )

    # 2) Buscar si ya existe registro para (fecha, producto)
    stmt = select(ProduccionDiaria).where(
        ProduccionDiaria.fecha == body.fecha,
        ProduccionDiaria.producto_id == body.producto_id,
    )
    existente = session.exec(stmt).first()

    if existente:
        existente.cantidad_producida = body.cantidad_producida
        existente.cantidad_vendida = body.cantidad_vendida or 0
        existente.cantidad_merma = body.cantidad_merma or 0
        session.add(existente)
        prod = existente
    else:
        prod = ProduccionDiaria(
            fecha=body.fecha,
            producto_id=body.producto_id,
            cantidad_producida=body.cantidad_producida,
            cantidad_vendida=body.cantidad_vendida or 0,
            cantidad_merma=body.cantidad_merma or 0,
        )
        session.add(prod)

    session.commit()
    session.refresh(prod)
    return prod


@router.get(
    "/produccion",
    response_model=List[ProduccionDiaria],
)
def listar_produccion(
    fecha: Optional[date] = None,
    producto_id: Optional[int] = None,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
):
    """
    Lista registros de producción.
    - Sin filtros: devuelve todo.
    - Con fecha: filtra por fecha.
    - Con producto_id: filtra por producto.
    - Con ambos: filtra por ambos.
    """
    stmt = select(ProduccionDiaria)

    if fecha is not None:
        stmt = stmt.where(ProduccionDiaria.fecha == fecha)
    if producto_id is not None:
        stmt = stmt.where(ProduccionDiaria.producto_id == producto_id)

    resultados = session.exec(stmt.order_by(
        ProduccionDiaria.fecha.desc(),
        ProduccionDiaria.id.desc(),
    )).all()
    return resultados


# =========================
# CONTEXTO DEL DÍA
# =========================

@router.post(
    "/contexto-dia",
    response_model=ContextoDia,
    status_code=status.HTTP_201_CREATED,
)
def registrar_contexto_dia(
    body: ContextoDiaCreate,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
):
    """
    Registra o actualiza el contexto de un día.
    Si es_fin_de_semana no viene, se calcula a partir de la fecha.
    """
    # auto-detect fin de semana si no vino
    es_fin_de_semana = body.es_fin_de_semana
    if es_fin_de_semana is None:
        # weekday(): 0=Lunes ... 5=Sábado, 6=Domingo
        es_fin_de_semana = body.fecha.weekday() >= 5

    stmt = select(ContextoDia).where(ContextoDia.fecha == body.fecha)
    existente = session.exec(stmt).first()

    if existente:
        existente.es_feriado = body.es_feriado
        existente.es_fin_de_semana = es_fin_de_semana
        existente.clima = body.clima
        existente.evento_especial = body.evento_especial
        existente.comentario = body.comentario
        session.add(existente)
        ctx = existente
    else:
        ctx = ContextoDia(
            fecha=body.fecha,
            es_feriado=body.es_feriado,
            es_fin_de_semana=es_fin_de_semana,
            clima=body.clima,
            evento_especial=body.evento_especial,
            comentario=body.comentario,
        )
        session.add(ctx)

    session.commit()
    session.refresh(ctx)
    return ctx



@router.get(
    "/contexto-dia/{fecha}",
    response_model=ContextoDia,
)
def obtener_contexto_dia(
    fecha: date,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
):
    """
    Devuelve el contexto de un día por fecha.
    Como la PK es id, buscamos por fecha con un select.
    """
    stmt = select(ContextoDia).where(ContextoDia.fecha == fecha)
    ctx = session.exec(stmt).first()

    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay contexto registrado para la fecha {fecha}",
        )

    return ctx
