# app.py - FastAPI compact monolith
from __future__ import annotations

from typing import List, Dict, Optional
from datetime import date, datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from data import init_db, get_session
from domain import (
    User, Role, Cliente, Servicio, Producto, Venta, Gasto, Caja,
    Cita, EstadoCita, MedioReserva, MedioPago, CategoriaGasto
)
from security import create_access_token, verify_password, require_role


app = FastAPI(title="Alevosos Studio API (compact)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    init_db()


# ---------------- AUTH ----------------
@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(),
          session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == form.username)).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    return {"access_token": create_access_token(user.email), "token_type": "bearer"}


# ---------------- CLIENTES ----------------
@app.get("/clientes/", response_model=List[Cliente])
def clientes_list(session: Session = Depends(get_session),
                  _=Depends(require_role(Role.admin, Role.barber))):
    return session.exec(select(Cliente).order_by(Cliente.id.desc())).all()

@app.post("/clientes/", response_model=Cliente)
def clientes_create(body: Cliente,
                    session: Session = Depends(get_session),
                    _=Depends(require_role(Role.admin, Role.barber))):
    c = Cliente(
        nombre=body.nombre, apellido=body.apellido, edad=body.edad,
        email=body.email, celular=body.celular
    )
    session.add(c); session.commit(); session.refresh(c)
    return c


# ---------------- SERVICIOS ----------------
@app.get("/servicios/", response_model=List[Servicio])
def servicios_list(session: Session = Depends(get_session),
                   _=Depends(require_role(Role.admin, Role.barber))):
    return session.exec(select(Servicio).where(Servicio.activo == True)).all()  # noqa: E712

@app.post("/servicios/", response_model=Servicio, tags=["servicios"])
def crear_servicio(payload: Dict,
                   session: Session = Depends(get_session),
                   _=Depends(require_role(Role.admin))):
    s = Servicio(
        nombre=payload["nombre"],
        precio_referencial=float(payload.get("precio_referencial")) if payload.get("precio_referencial") not in (None, "") else None,
        activo=bool(payload.get("activo", True)),
        duracion_min=int(payload.get("duracion_min", 30)),
    )
    if s.duracion_min <= 0:
        raise HTTPException(status_code=422, detail="duracion_min debe ser > 0")
    session.add(s); session.commit(); session.refresh(s)
    return s


# ---- helpers tolerantes ----
def _parse_monto(x):
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        raise HTTPException(status_code=422, detail="monto inválido")

def _parse_fecha(x):
    if isinstance(x, date): return x
    s = str(x).strip()
    try:
        return date.fromisoformat(s[:10])          # YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS
    except Exception:
        try:
            return datetime.strptime(s.split("T")[0], "%d/%m/%Y").date()  # DD/MM/YYYY
        except Exception:
            raise HTTPException(status_code=422, detail="fecha inválida (usa YYYY-MM-DD)")


# ---------------- VENTAS ----------------
class VentaIn(BaseModel):
    cliente_id: Optional[int] = None
    servicio_id: int
    monto: float | str
    medio_pago: MedioPago
    fecha: date | str
    nota: Optional[str] = None

@app.get("/ventas/", response_model=List[Venta])
def ventas_list(session: Session = Depends(get_session),
                _=Depends(require_role(Role.admin, Role.barber))):
    return session.exec(select(Venta).order_by(Venta.fecha.desc(), Venta.id.desc()).limit(200)).all()

@app.post("/ventas/", response_model=Venta)
def ventas_create(body: VentaIn,
                  session: Session = Depends(get_session),
                  _=Depends(require_role(Role.admin, Role.barber))):
    v = Venta(
        cliente_id=body.cliente_id,
        servicio_id=body.servicio_id,
        monto=_parse_monto(body.monto),
        medio_pago=body.medio_pago,
        fecha=_parse_fecha(body.fecha),
        nota=body.nota,
    )
    session.add(v); session.commit(); session.refresh(v)
    return v


# ---------------- GASTOS ----------------
@app.get("/gastos/", response_model=List[Gasto])
def gastos_list(session: Session = Depends(get_session),
                _=Depends(require_role(Role.admin))):
    return session.exec(select(Gasto).order_by(Gasto.fecha.desc(), Gasto.id.desc()).limit(200)).all()

@app.post("/gastos/", response_model=Gasto)
def gastos_create(body: Gasto,
                  session: Session = Depends(get_session),
                  _=Depends(require_role(Role.admin))):
    g = Gasto(categoria=body.categoria, descripcion=body.descripcion, monto=body.monto, fecha=body.fecha)
    session.add(g); session.commit(); session.refresh(g)
    return g


# ---------------- REPORTES ----------------
def _sum_ventas(session: Session, desde: date, hasta: date) -> Dict[str, float]:
    ventas = session.exec(select(Venta).where((Venta.fecha >= desde) & (Venta.fecha <= hasta))).all()
    total = sum(v.monto for v in ventas)
    por_medio: Dict[str, float] = {}
    for v in ventas:
        por_medio[v.medio_pago] = por_medio.get(v.medio_pago, 0.0) + v.monto
    return {"total": total, "por_medio": por_medio}

def _sum_gastos(session: Session, desde: date, hasta: date) -> float:
    gastos = session.exec(select(Gasto).where((Gasto.fecha >= desde) & (Gasto.fecha <= hasta))).all()
    return float(sum(g.monto for g in gastos))

@app.get("/reportes/resumen")
def reportes_resumen(desde: date, hasta: date,
                     session: Session = Depends(get_session),
                     _=Depends(require_role(Role.admin, Role.barber))):
    v = _sum_ventas(session, desde, hasta)
    g = _sum_gastos(session, desde, hasta)
    neto = v["total"] - g
    return {"ingresos": v["total"], "gastos": g, "neto": neto, "por_medio": v["por_medio"]}


# ---------------- CAJA ----------------
def _resumen_caja(session: Session, fecha: date) -> Dict:
    c = session.exec(select(Caja).where(Caja.fecha == fecha)).first()
    apertura = c.apertura if c else 0.0
    cierre = c.cierre if c else None

    ventas_dia = session.exec(select(Venta).where(Venta.fecha == fecha)).all()
    ventas_total = float(sum(v.monto for v in ventas_dia))
    ventas_por_medio: Dict[str, float] = {}
    for v in ventas_dia:
        ventas_por_medio[v.medio_pago] = ventas_por_medio.get(v.medio_pago, 0.0) + v.monto

    gastos_total = float(sum(g.monto for g in session.exec(select(Gasto).where(Gasto.fecha == fecha)).all()))

    sistema_efectivo = apertura + ventas_por_medio.get("efectivo", 0.0) - gastos_total
    dif = None if cierre is None else float(round(cierre - sistema_efectivo, 2))

    return {
        "fecha": str(fecha),
        "apertura_efectivo": apertura,
        "ventas_total": ventas_total,
        "ventas_por_medio": ventas_por_medio,
        "gastos_total": gastos_total,
        "sistema_efectivo": float(sistema_efectivo),
        "declarado_efectivo": cierre,
        "diferencia_efectivo": dif,
    }

@app.get("/caja/resumen")
def caja_resumen(fecha: date,
                 session: Session = Depends(get_session),
                 _=Depends(require_role(Role.admin, Role.barber))):
    return _resumen_caja(session, fecha)

@app.post("/caja/abrir")
def caja_abrir(data: Dict,
               session: Session = Depends(get_session),
               _=Depends(require_role(Role.admin))):
    fecha = date.fromisoformat(str(data.get("fecha")))
    apertura = float(data.get("apertura", 0.0))
    obs = data.get("observaciones")
    c = session.exec(select(Caja).where(Caja.fecha == fecha)).first()
    if c:
        raise HTTPException(status_code=400, detail="Ya existe caja para esa fecha")
    c = Caja(fecha=fecha, apertura=apertura, observaciones=obs)
    session.add(c); session.commit()
    return {"ok": True}

@app.post("/caja/cerrar")
def caja_cerrar(data: Dict,
                session: Session = Depends(get_session),
                _=Depends(require_role(Role.admin))):
    fecha = date.fromisoformat(str(data.get("fecha")))
    cierre = float(data.get("cierre", 0.0))
    obs = data.get("observaciones")
    c = session.exec(select(Caja).where(Caja.fecha == fecha)).first()
    if not c:
        raise HTTPException(status_code=404, detail="No existe caja para esa fecha")
    c.cierre = cierre
    if obs:
        c.observaciones = (c.observaciones or "") + (f"\n{obs}" if c.observaciones else obs)
    session.add(c); session.commit()
    return _resumen_caja(session, fecha)

@app.get("/caja/verificar_dia")
def caja_verificar_dia(fecha: date, tolerancia: float = 0.0,
                       session: Session = Depends(get_session),
                       _=Depends(require_role(Role.admin))):
    r = _resumen_caja(session, fecha)
    problemas = []
    if r["apertura_efectivo"] is None or r["apertura_efectivo"] < 0:
        problemas.append("Apertura inválida o no declarada")
    if r["declarado_efectivo"] is None:
        problemas.append("No se declaró cierre/efectivo contado")
    else:
        delta = abs(r["diferencia_efectivo"] or 0.0)
        if delta > tolerancia:
            problemas.append(f"Diferencia supera tolerancia: {delta} > {tolerancia}")
    ok = len(problemas) == 0
    return {"ok": ok, "fecha": r["fecha"], "tolerancia": tolerancia, "problemas": problemas}

@app.get("/caja/verificar")
def caja_verificar(desde: date, hasta: date, tolerancia: float = 0.0,
                   session: Session = Depends(get_session),
                   _=Depends(require_role(Role.admin))):
    cur = desde
    detalles = []
    ok_dias = 0
    con_problemas = 0
    while cur <= hasta:
        rr = _resumen_caja(session, cur)
        problemas = []
        if rr["declarado_efectivo"] is None:
            problemas.append("Sin cierre declarado")
        else:
            delta = abs(rr["diferencia_efectivo"] or 0.0)
            if delta > tolerancia:
                problemas.append(f"Diferencia supera tolerancia: {delta} > {tolerancia}")
        if problemas:
            con_problemas += 1
        else:
            ok_dias += 1
        detalles.append({
            "fecha": rr["fecha"],
            "problemas": problemas,
            "apertura": rr["apertura_efectivo"],
            "esperado_efectivo": rr["sistema_efectivo"],
            "declarado_efectivo": rr["declarado_efectivo"],
            "diferencia_efectivo": rr["diferencia_efectivo"],
        })
        cur = cur + timedelta(days=1)
    return {"ok_dias": ok_dias, "con_problemas": con_problemas, "detalles": detalles}


# ---------------- CITAS / AGENDA ----------------
def _cita_fin(c: Cita) -> datetime:
    return c.inicio + timedelta(minutes=c.duracion_min)

def _hay_conflicto(session: Session, barber_id: int, inicio: datetime, duracion_min: int,
                   excluir_id: Optional[int] = None) -> Optional[Cita]:
    fin = inicio + timedelta(minutes=duracion_min)
    dia_ini = datetime(inicio.year, inicio.month, inicio.day)
    dia_fin = dia_ini + timedelta(days=1)
    q = select(Cita).where(Cita.barber_id == barber_id).where(Cita.inicio >= dia_ini).where(Cita.inicio < dia_fin)
    if excluir_id:
        q = q.where(Cita.id != excluir_id)
    for c in session.exec(q).all():
        if (inicio < _cita_fin(c)) and (fin > c.inicio) and (c.estado not in [EstadoCita.cancelada, EstadoCita.no_show]):
            return c
    return None

@app.get("/citas", tags=["citas"])
def listar_citas(desde: datetime, hasta: datetime,
                 barber_id: Optional[int] = None,
                 estado: Optional[EstadoCita] = None,
                 session: Session = Depends(get_session),
                 user: User = Depends(require_role(Role.admin, Role.barber))):
    q = select(Cita).where(Cita.inicio >= desde).where(Cita.inicio <= hasta)
    if barber_id:
        if user.role == Role.barber and user.id != barber_id:
            raise HTTPException(status_code=403, detail="Solo tus citas")
        q = q.where(Cita.barber_id == barber_id)
    elif user.role == Role.barber:
        q = q.where(Cita.barber_id == user.id)
    if estado:
        q = q.where(Cita.estado == estado)
    return session.exec(q.order_by(Cita.inicio.asc())).all()

@app.post("/citas", response_model=Cita, tags=["citas"])
def crear_cita(payload: Dict,
               session: Session = Depends(get_session),
               user: User = Depends(require_role(Role.admin, Role.barber))):
    raw_inicio = str(payload.get("inicio") or "")
    try:
        inicio = datetime.fromisoformat(raw_inicio[:19])  # YYYY-MM-DDTHH:MM[:SS]
    except Exception:
        raise HTTPException(status_code=400, detail="inicio debe ser ISO 8601: YYYY-MM-DDTHH:MM[:SS]")

    barber_id = int(payload.get("barber_id") or (user.id if user.role == Role.barber else 0))
    if barber_id <= 0:
        raise HTTPException(status_code=400, detail="barber_id requerido")

    # cliente_id requerido (la tabla lo exige NOT NULL)
    if payload.get("cliente_id") in (None, "", "null"):
        raise HTTPException(status_code=422, detail="cliente_id requerido")
    cliente_id = int(payload["cliente_id"])

    # duracion_min: payload > servicio.duracion_min > 30
    duracion_min = payload.get("duracion_min")
    if duracion_min in (None, "", 0):
        duracion_min = 30
        sid = payload.get("servicio_id")
        if sid:
            srv = session.get(Servicio, int(sid))
            if srv and srv.duracion_min:
                duracion_min = int(srv.duracion_min)
    else:
        duracion_min = int(duracion_min)
    if duracion_min <= 0:
        raise HTTPException(status_code=422, detail="duracion_min debe ser > 0")

    conflicto = _hay_conflicto(session, barber_id, inicio, duracion_min)
    if conflicto:
        raise HTTPException(
            status_code=409,
            detail=f"Conflicto con cita #{conflicto.id} desde {conflicto.inicio.isoformat()} hasta {_cita_fin(conflicto).isoformat()}"
        )

    c = Cita(
        cliente_id=cliente_id,
        servicio_id=int(payload["servicio_id"]) if payload.get("servicio_id") else None,
        barber_id=barber_id,
        inicio=inicio,
        duracion_min=duracion_min,
        estado=EstadoCita(payload.get("estado", EstadoCita.agendada)),
        medio_reserva=MedioReserva(payload.get("medio_reserva", MedioReserva.online)),
        precio=float(payload["precio"]) if payload.get("precio") not in (None, "", "null") else None,
        notas=payload.get("notas"),
    )
    session.add(c); session.commit(); session.refresh(c)
    return c

@app.put("/citas/{cita_id}", tags=["citas"])
def actualizar_cita(cita_id: int, payload: Dict,
                    session: Session = Depends(get_session),
                    user: User = Depends(require_role(Role.admin, Role.barber))):
    c = session.get(Cita, cita_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    if user.role == Role.barber and c.barber_id != user.id:
        raise HTTPException(status_code=403, detail="Solo tus citas")

    new_inicio = datetime.fromisoformat(payload.get("inicio", c.inicio.isoformat()))
    new_duracion = int(payload.get("duracion_min", c.duracion_min))
    new_barber = int(payload.get("barber_id", c.barber_id))
    conflicto = _hay_conflicto(session, new_barber, new_inicio, new_duracion, excluir_id=c.id)
    if conflicto:
        raise HTTPException(status_code=409, detail=f"Conflicto con cita #{conflicto.id}")

    for k in ["cliente_id", "servicio_id", "precio", "notas"]:
        if k in payload:
            setattr(c, k, payload[k] if payload[k] != "" else None)
    c.inicio = new_inicio
    c.duracion_min = new_duracion
    c.barber_id = new_barber
    if "estado" in payload:
        c.estado = EstadoCita(payload["estado"])
    if "medio_reserva" in payload:
        c.medio_reserva = MedioReserva(payload["medio_reserva"])
    session.add(c); session.commit(); session.refresh(c)
    return c

@app.delete("/citas/{cita_id}", tags=["citas"])
def borrar_cita(cita_id: int,
                session: Session = Depends(get_session),
                user: User = Depends(require_role(Role.admin, Role.barber))):
    c = session.get(Cita, cita_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    if user.role == Role.barber and c.barber_id != user.id:
        raise HTTPException(status_code=403, detail="Solo tus citas")
    session.delete(c)
    session.commit()
    return {"ok": True, "deleted_id": cita_id}

@app.post("/citas/{cita_id}/estado", tags=["citas"])
def cambiar_estado_cita(cita_id: int, nuevo_estado: EstadoCita,
                        session: Session = Depends(get_session),
                        user: User = Depends(require_role(Role.admin, Role.barber))):
    c = session.get(Cita, cita_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    if user.role == Role.barber and c.barber_id != user.id:
        raise HTTPException(status_code=403, detail="Solo tus citas")
    c.estado = nuevo_estado
    session.add(c); session.commit(); session.refresh(c)
    return c

@app.get("/citas/conflictos", tags=["citas"])
def verificar_conflicto(barber_id: int, inicio: datetime, duracion_min: int = 30,
                        excluir_id: Optional[int] = None,
                        session: Session = Depends(get_session),
                        _user: User = Depends(require_role(Role.admin, Role.barber))):
    c = _hay_conflicto(session, barber_id, inicio, duracion_min, excluir_id=excluir_id)
    if c:
        return {"conflicto": True, "con": {"id": c.id, "inicio": c.inicio, "fin": _cita_fin(c)}}
    return {"conflicto": False}

@app.get("/citas/calendario", tags=["citas"])
def calendario(desde: datetime, hasta: datetime, barber_id: Optional[int] = None,
               session: Session = Depends(get_session),
               user: User = Depends(require_role(Role.admin, Role.barber))):
    q = select(Cita).where(Cita.inicio >= desde).where(Cita.inicio <= hasta)
    if barber_id:
        if user.role == Role.barber and user.id != barber_id:
            raise HTTPException(status_code=403, detail="Solo tus citas")
        q = q.where(Cita.barber_id == barber_id)
    elif user.role == Role.barber:
        q = q.where(Cita.barber_id == user.id)

    citas = session.exec(q.order_by(Cita.inicio.asc())).all()

    # Prefetch nombres
    cliente_ids = sorted({c.cliente_id for c in citas if c.cliente_id})
    clientes = {}
    if cliente_ids:
        cc = session.exec(select(Cliente).where(Cliente.id.in_(cliente_ids))).all()
        clientes = {c.id: f"{c.nombre} {c.apellido or ''}".strip() for c in cc}

    servicio_ids = sorted({c.servicio_id for c in citas if c.servicio_id})
    servicios = {}
    if servicio_ids:
        ss = session.exec(select(Servicio).where(Servicio.id.in_(servicio_ids))).all()
        servicios = {s.id: s.nombre for s in ss}

    barber_ids = sorted({c.barber_id for c in citas})
    barberos = {}
    if barber_ids:
        us = session.exec(select(User).where(User.id.in_(barber_ids))).all()
        barberos = {u.id: (u.email.split("@")[0] if u.email else f"barber_{u.id}") for u in us}

    def fin_de(c: Cita): return c.inicio + timedelta(minutes=c.duracion_min)

    events = []
    for c in citas:
        cli = clientes.get(c.cliente_id, f"Cliente #{c.cliente_id}")
        srv = servicios.get(c.servicio_id, "")
        barb = barberos.get(c.barber_id, f"Barber #{c.barber_id}")
        title = f"{cli}" + (f" · {srv}" if srv else "")
        events.append({
            "id": c.id, "title": title,
            "start": c.inicio.isoformat(), "end": fin_de(c).isoformat(),
            "barber_id": c.barber_id, "barber": barb,
            "cliente_id": c.cliente_id, "servicio_id": c.servicio_id,
            "estado": c.estado, "medio_reserva": c.medio_reserva,
            "notas": c.notas,
        })
    return events


# --------- SLOTS (business hours simples + buffer) ---------
from typing import Tuple

# Horarios por barbero (hora local). Editable rápido sin DB:
BUSINESS_HOURS: dict[int, list[Tuple[str, str]]] = {
    # barber_id: [(desde, hasta), ...]  en formato "HH:MM"
    1: [("08:00", "12:00"), ("14:00", "19:00")],
    2: [("09:00", "13:00"), ("15:00", "20:00")],
}

def _hhmm(dt: date, s: str) -> datetime:
    hh, mm = map(int, s.split(":"))
    return datetime(dt.year, dt.month, dt.day, hh, mm, 0)

def _merge(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    if not intervals: return []
    intervals = sorted(intervals, key=lambda x: x[0])
    res = [intervals[0]]
    for s, e in intervals[1:]:
        ls, le = res[-1]
        if s <= le:
            res[-1] = (ls, max(le, e))
        else:
            res.append((s, e))
    return res

def _subtract(base: list[tuple[datetime, datetime]], busy: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Resta busy de base; devuelve huecos libres."""
    free: list[tuple[datetime, datetime]] = []
    for bs, be in base:
        cur = bs
        for os, oe in (i for i in busy if i[0] < be and i[1] > bs):
            if os > cur:
                free.append((cur, min(os, be)))
            cur = max(cur, oe)
            if cur >= be: break
        if cur < be:
            free.append((cur, be))
    return free

@app.get("/citas/slots", tags=["citas"])
def citas_slots(fecha: date,
                barber_id: int,
                duracion_min: int = 30,
                step: int = 15,
                buffer_min: int = 0,
                session: Session = Depends(get_session),
                _=Depends(require_role(Role.admin, Role.barber))):
    # Business hours para ese barbero; default si no hay config
    bh = BUSINESS_HOURS.get(barber_id, [("09:00", "19:00")])
    base = [(_hhmm(fecha, a), _hhmm(fecha, b)) for a, b in bh]

    # Ocupados (con buffer post-servicio)
    dia_ini = datetime(fecha.year, fecha.month, fecha.day)
    dia_fin = dia_ini + timedelta(days=1)
    citas = session.exec(
        select(Cita)
        .where(Cita.barber_id == barber_id)
        .where(Cita.inicio >= dia_ini)
        .where(Cita.inicio < dia_fin)
        .where(Cita.estado.notin_([EstadoCita.cancelada, EstadoCita.no_show]))
    ).all()
    busy = []
    for c in citas:
        fin = c.inicio + timedelta(minutes=c.duracion_min + buffer_min)
        busy.append((c.inicio, fin))
    busy = _merge(busy)

    # Libres: business hours - busy
    free = _subtract(base, busy)

    # Generar slots deslizantes que "entran" completos
    need = timedelta(minutes=duracion_min)
    step_td = timedelta(minutes=step)
    out = []
    for fs, fe in free:
        cur = fs
        while cur + need <= fe:
            out.append({"start": cur.isoformat(), "end": (cur + need).isoformat()})
            cur += step_td
    return {"fecha": str(fecha), "barber_id": barber_id, "duracion_min": duracion_min, "step": step, "buffer_min": buffer_min, "slots": out}

# ---------------- ROOT & HEALTH ----------------
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")

@app.get("/health", tags=["system"], include_in_schema=False)
def health():
    return {"ok": True}
