# panaderia_core/servicios/reportes.py
from typing import Optional, Dict, Any, List
from datetime import date, datetime, time

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from panaderia_core.db.conexion import get_session
from panaderia_core.db.modelos import Venta, MedioPago, Role
from panaderia_core.security import require_role

router = APIRouter()


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
