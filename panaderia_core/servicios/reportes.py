from typing import Optional, Dict, Any, List
from datetime import date, datetime, time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from panaderia_core.db.conexion import get_session
from panaderia_core.db.modelos import (
    Venta,
    MedioPago,
    Role,
    ProduccionDiaria,
    Producto,
    ItemVenta,
)
from panaderia_core.security import require_role


router = APIRouter()

class ProduccionVsVentasRow(BaseModel):
    fecha: date
    producto_id: int
    producto_nombre: str
    produccion: float
    vendida: float
    merma: float


def _parse_fecha(x: Optional[date | str]) -> Optional[date]:
    if x is None:
        return None
    if isinstance(x, date):
        return x
    try:
        return date.fromisoformat(str(x)[:10])
    except Exception:
        return None


@router.get("/resumen")
def resumen_ventas(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
) -> Dict[str, Any]:
    fi = _parse_fecha(fecha_inicio)
    ff = _parse_fecha(fecha_fin)

    q = select(Venta)

    if fi:
        dt_ini = datetime.combine(fi, time.min)
        q = q.where(Venta.fecha_hora >= dt_ini)
    if ff:
        dt_fin = datetime.combine(ff, time.max)
        q = q.where(Venta.fecha_hora <= dt_fin)

    ventas: List[Venta] = session.exec(q).all()

    if not fi and ventas:
        fi = min(v.fecha_hora.date() for v in ventas)
    if not ff and ventas:
        ff = max(v.fecha_hora.date() for v in ventas)

    monto_total = sum(v.total for v in ventas)
    cantidad_ventas = len(ventas)

    por_medio: Dict[MedioPago, Dict[str, float | int]] = {}
    for v in ventas:
        mp = v.medio_pago
        if mp not in por_medio:
            por_medio[mp] = {"monto_total": 0.0, "cantidad": 0}
        por_medio[mp]["monto_total"] += v.total
        por_medio[mp]["cantidad"] += 1

    detalle_medios = [
        {
            "medio_pago": mp.value,
            "monto_total": datos["monto_total"],
            "cantidad_ventas": datos["cantidad"],
        }
        for mp, datos in por_medio.items()
    ]

    return {
        "periodo": {
            "inicio": fi.isoformat() if fi else None,
            "fin": ff.isoformat() if ff else None,
        },
        "totales": {
            "monto_total": monto_total,
            "cantidad_ventas": cantidad_ventas,
        },
        "por_medio_pago": detalle_medios,
    }
@router.get("/produccion-vs-ventas", response_model=List[ProduccionVsVentasRow])
def produccion_vs_ventas(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    producto_id: Optional[int] = None,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
) -> List[ProduccionVsVentasRow]:
    """
    Reporte integrado por fecha y producto:
    - produccion (ProduccionDiaria)
    - vendida (ItemVenta + Venta)
    - merma (registro o produccion - vendida)
    """
    # Normalizamos fechas (puede venir str desde Swagger)
    fi = _parse_fecha(fecha_inicio)
    ff = _parse_fecha(fecha_fin)

    # -------- 1) Traer producciones diarias + productos --------
    q_prod = (
        select(ProduccionDiaria, Producto)
        .where(ProduccionDiaria.producto_id == Producto.id)
    )

    if fi:
        q_prod = q_prod.where(ProduccionDiaria.fecha >= fi)
    if ff:
        q_prod = q_prod.where(ProduccionDiaria.fecha <= ff)
    if producto_id:
        q_prod = q_prod.where(ProduccionDiaria.producto_id == producto_id)

    producciones = session.exec(q_prod).all()

    # Estructura: (fecha, producto_id) -> datos base
    data: Dict[tuple[date, int], Dict[str, Any]] = {}

    for prod, prod_producto in producciones:
        key = (prod.fecha, prod.producto_id)
        if key not in data:
            data[key] = {
                "fecha": prod.fecha,
                "producto_id": prod.producto_id,
                "producto_nombre": prod_producto.nombre,
                "produccion": 0.0,
                "vendida_registrada": 0.0,
                "merma_registrada": 0.0,
            }
        data[key]["produccion"] += float(prod.cantidad_producida or 0)
        data[key]["vendida_registrada"] += float(prod.cantidad_vendida or 0)
        data[key]["merma_registrada"] += float(prod.cantidad_merma or 0)

    # -------- 2) Traer ventas agregadas por día + producto --------
    q_ventas = (
        select(ItemVenta, Venta.fecha_hora, Producto)
        .where(ItemVenta.venta_id == Venta.id)
        .where(ItemVenta.producto_id == Producto.id)
    )

    if fi:
        dt_ini = datetime.combine(fi, time.min)
        q_ventas = q_ventas.where(Venta.fecha_hora >= dt_ini)
    if ff:
        dt_fin = datetime.combine(ff, time.max)
        q_ventas = q_ventas.where(Venta.fecha_hora <= dt_fin)
    if producto_id:
        q_ventas = q_ventas.where(ItemVenta.producto_id == producto_id)

    ventas_rows = session.exec(q_ventas).all()

    ventas_por_key: Dict[tuple[date, int], Dict[str, Any]] = {}

    for item, fecha_hora, prod_producto in ventas_rows:
        fecha_dia = fecha_hora.date()
        key = (fecha_dia, item.producto_id)

        if key not in ventas_por_key:
            ventas_por_key[key] = {
                "fecha": fecha_dia,
                "producto_id": item.producto_id,
                "producto_nombre": prod_producto.nombre,
                "vendida_total": 0.0,
            }

        ventas_por_key[key]["vendida_total"] += float(item.cantidad or 0)

    # -------- 3) Combinar todo --------
    # Primero, aseguramos que todos los keys de ventas estén en data
    for key, info_v in ventas_por_key.items():
        if key not in data:
            data[key] = {
                "fecha": info_v["fecha"],
                "producto_id": info_v["producto_id"],
                "producto_nombre": info_v["producto_nombre"],
                "produccion": 0.0,
                "vendida_registrada": 0.0,
                "merma_registrada": 0.0,
            }

    # Ahora armamos las filas finales
    filas: List[ProduccionVsVentasRow] = []

    for (fecha_dia, prod_id), info in sorted(
        data.items(),
        key=lambda kv: (kv[0][0], kv[0][1]),  # orden por fecha, luego producto
        reverse=True,
    ):
        ventas_info = ventas_por_key.get((fecha_dia, prod_id))
        vendida_real = float(ventas_info["vendida_total"]) if ventas_info else 0.0

        produccion = float(info["produccion"])
        vendida_reg = float(info["vendida_registrada"])
        merma_reg = float(info["merma_registrada"])

        # Tomamos prioridad:
        # 1) merma registrada si existe
        # 2) sino calculamos como produccion - vendida_real (nunca negativo)
        if merma_reg > 0:
            merma = merma_reg
        else:
            base_vendida = vendida_real or vendida_reg
            merma = max(produccion - base_vendida, 0.0)

        # Vendida final:
        vendida_final = vendida_real or vendida_reg

        filas.append(
            ProduccionVsVentasRow(
                fecha=fecha_dia,
                producto_id=prod_id,
                producto_nombre=info["producto_nombre"],
                produccion=produccion,
                vendida=vendida_final,
                merma=merma,
            )
        )

    return filas
