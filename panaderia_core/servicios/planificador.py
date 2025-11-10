# panaderia_core/servicios/planificador.py

from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from panaderia_core.db.conexion import get_session
from panaderia_core.db.modelos import (
    Producto,
    ContextoDia,
    ProduccionDiaria,
    Role,
)
from panaderia_core.security import require_role

router = APIRouter()


# =========================
# Esquemas de respuesta
# =========================

class PlanProductoOut(BaseModel):
    producto_id: int
    nombre: str
    produccion_base: float
    factor: float
    produccion_sugerida: float


class PlanDiaOut(BaseModel):
    fecha: date
    es_feriado: bool
    es_fin_de_semana: bool
    clima: Optional[str]
    evento_especial: Optional[str]
    productos: List[PlanProductoOut]

class PlanAplicarRequest(BaseModel):
    fecha: date
    # Si viene vacío o null → aplica a todos los productos con produccion_sugerida_base
    producto_ids: Optional[List[int]] = None
    # Si lo mandás, pisa el factor calculado por contexto (ej: forzar 1.0 o 1.5)
    factor_manual: Optional[float] = None


class PlanAplicarProductoOut(BaseModel):
    producto_id: int
    nombre: str
    produccion_base: float
    factor_usado: float
    produccion_sugerida: float
    produccion_anterior: float
    produccion_nueva: float


class PlanAplicarOut(BaseModel):
    fecha: date
    factor_usado: float
    productos: List[PlanAplicarProductoOut]

class ExplicacionPlanOut(BaseModel):
    fecha: date
    producto_id: int
    producto_nombre: str
    produccion_base: float
    factor_calculado: float
    produccion_sugerida: float
    produccion_registrada: float
    texto: str

# =========================
# Helpers de negocio
# =========================

def _calcular_factor(
    es_feriado: bool,
    es_fin_de_semana: bool,
    clima: Optional[str],
    evento_especial: Optional[str],
) -> float:
    """
    Reglas simples:
    - Base: 1.0
    - Feriado: +30%
    - Fin de semana: +20%
    - Clima frío/lluvioso: +10% (más pan, más facturas)
    - Evento especial: +15%
    Si se acumulan, se suman los porcentajes.
    """
    factor = 1.0

    clima_norm = (clima or "").lower()
    evento_norm = (evento_especial or "").lower()

    if es_feriado:
        factor += 0.30
    if es_fin_de_semana:
        factor += 0.20
    if "lluvia" in clima_norm or "lluvioso" in clima_norm or "frío" in clima_norm or "frio" in clima_norm:
        factor += 0.10
    if evento_norm not in ("", "ninguno", "ninguna"):
        factor += 0.15

    # Podés limitar el max si querés, por ahora lo dejamos libre
    return factor


def _obtener_contexto_para_fecha(
    d: date,
    session: Session,
) -> ContextoDia:
    """
    Devuelve un ContextoDia “efectivo”:
    - Si hay registro en la tabla, lo usa.
    - Si no, crea uno virtual (no se guarda) solo para cálculos,
      marcando es_fin_de_semana según la fecha.
    """
    stmt = select(ContextoDia).where(ContextoDia.fecha == d)
    ctx = session.exec(stmt).first()

    if ctx:
        return ctx

    # Contexto virtual (no persistido)
    es_fin_de_semana = d.weekday() >= 5  # 5=Sábado, 6=Domingo
    return ContextoDia(
        fecha=d,
        es_feriado=False,
        es_fin_de_semana=es_fin_de_semana,
        clima=None,
        evento_especial=None,
        comentario=None,
    )


# =========================
# Endpoint principal
# =========================

@router.get("/semana", response_model=List[PlanDiaOut])
def planificar_semana(
    fecha_inicio: Optional[date] = None,
    dias: int = 7,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
) -> List[PlanDiaOut]:
    """
    Plan simple de producción para un rango de días (por defecto, 7).
    Usa:
      - productos activos con produccion_sugerida_base
      - contexto de cada día (si existe) o contexto virtual
    """
    if dias <= 0:
        dias = 1
    if dias > 14:
        dias = 14  # límite sano

    hoy = date.today()
    inicio = fecha_inicio or hoy

    # Productos base
    q_prod = select(Producto).where(
        Producto.activo == True,  # noqa: E712
        Producto.produccion_sugerida_base.is_not(None),
    ).order_by(Producto.nombre.asc())

    productos = session.exec(q_prod).all()

    planes: List[PlanDiaOut] = []

    for i in range(dias):
        dia = inicio + timedelta(days=i)
        ctx = _obtener_contexto_para_fecha(dia, session)

        factor = _calcular_factor(
            es_feriado=ctx.es_feriado,
            es_fin_de_semana=ctx.es_fin_de_semana,
            clima=ctx.clima,
            evento_especial=ctx.evento_especial,
        )

        productos_plan: List[PlanProductoOut] = []

        for p in productos:
            base = float(p.produccion_sugerida_base or 0)
            if base <= 0:
                continue

            sugerida = round(base * factor, 2)

            productos_plan.append(
                PlanProductoOut(
                    producto_id=p.id,
                    nombre=p.nombre,
                    produccion_base=base,
                    factor=round(factor, 2),
                    produccion_sugerida=sugerida,
                )
            )

        planes.append(
            PlanDiaOut(
                fecha=dia,
                es_feriado=ctx.es_feriado,
                es_fin_de_semana=ctx.es_fin_de_semana,
                clima=ctx.clima,
                evento_especial=ctx.evento_especial,
                productos=productos_plan,
            )
        )

    return planes

@router.post("/aplicar-dia", response_model=PlanAplicarOut)
def aplicar_plan_dia(
    body: PlanAplicarRequest,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
) -> PlanAplicarOut:
    """
    Aplica el plan de producción para una fecha:
    - Calcula factor según contexto (o usa factor_manual si viene).
    - Para cada producto con produccion_sugerida_base:
        * crea o actualiza ProduccionDiaria.cantidad_producida
        * no toca cantidad_vendida ni cantidad_merma
    """

    # 1) Contexto real o virtual para la fecha
    ctx = _obtener_contexto_para_fecha(body.fecha, session)

    factor_contexto = _calcular_factor(
        es_feriado=ctx.es_feriado,
        es_fin_de_semana=ctx.es_fin_de_semana,
        clima=ctx.clima,
        evento_especial=ctx.evento_especial,
    )
    factor = body.factor_manual if body.factor_manual is not None else factor_contexto

    # 2) Productos base
    q_prod = select(Producto).where(
        Producto.activo == True,  # noqa: E712
        Producto.produccion_sugerida_base.is_not(None),
    )
    if body.producto_ids:
        q_prod = q_prod.where(Producto.id.in_(body.producto_ids))  # type: ignore

    productos = session.exec(q_prod.order_by(Producto.nombre.asc())).all()

    resultados: List[PlanAplicarProductoOut] = []

    for p in productos:
        base = float(p.produccion_sugerida_base or 0)
        if base <= 0:
            continue

        sugerida = round(base * factor, 2)

        # 3) Buscar produccion existente para (fecha, producto)
        stmt = select(ProduccionDiaria).where(
            ProduccionDiaria.fecha == body.fecha,
            ProduccionDiaria.producto_id == p.id,
        )
        existente = session.exec(stmt).first()

        if existente:
            produccion_anterior = float(existente.cantidad_producida or 0)
            existente.cantidad_producida = sugerida
            session.add(existente)
            produccion_nueva = sugerida
        else:
            produccion_anterior = 0.0
            prod = ProduccionDiaria(
                fecha=body.fecha,
                producto_id=p.id,
                cantidad_producida=sugerida,
                cantidad_vendida=0.0,
                cantidad_merma=0.0,
            )
            session.add(prod)
            produccion_nueva = sugerida

        resultados.append(
            PlanAplicarProductoOut(
                producto_id=p.id,
                nombre=p.nombre,
                produccion_base=base,
                factor_usado=round(factor, 2),
                produccion_sugerida=sugerida,
                produccion_anterior=produccion_anterior,
                produccion_nueva=produccion_nueva,
            )
        )

    session.commit()

    return PlanAplicarOut(
        fecha=body.fecha,
        factor_usado=round(factor, 2),
        productos=resultados,
    )

@router.get("/explicacion", response_model=ExplicacionPlanOut)
def explicar_plan(
    fecha: date,
    producto_id: int,
    session: Session = Depends(get_session),
    _user=Depends(require_role(Role.admin, Role.empleado)),
) -> ExplicacionPlanOut:
    """
    Devuelve una explicación en lenguaje natural de por qué se sugiere
    cierta producción para (fecha, producto).
    Usa:
      - produccion_sugerida_base del producto
      - contexto del día (feriado, finde, clima, evento)
      - producción ya registrada (si existe)
    """
    # Producto
    prod = session.get(Producto, producto_id)
    if not prod or not prod.activo:
        raise ValueError(f"Producto inválido o inactivo (id={producto_id})")

    base = float(prod.produccion_sugerida_base or 0)
    if base <= 0:
        # No tiene base, poca info para sugerir
        return ExplicacionPlanOut(
            fecha=fecha,
            producto_id=producto_id,
            producto_nombre=prod.nombre,
            produccion_base=0.0,
            factor_calculado=1.0,
            produccion_sugerida=0.0,
            produccion_registrada=0.0,
            texto=(
                f"El producto '{prod.nombre}' no tiene una producción base "
                f"configurada (produccion_sugerida_base), por eso no se puede "
                f"generar una sugerencia automática para {fecha}."
            ),
        )

    # Contexto (real o virtual)
    ctx = _obtener_contexto_para_fecha(fecha, session)
    factor = _calcular_factor(
        es_feriado=ctx.es_feriado,
        es_fin_de_semana=ctx.es_fin_de_semana,
        clima=ctx.clima,
        evento_especial=ctx.evento_especial,
    )
    sugerida = round(base * factor, 2)

    # Produccion ya registrada (si existe)
    stmt = select(ProduccionDiaria).where(
        ProduccionDiaria.fecha == fecha,
        ProduccionDiaria.producto_id == producto_id,
    )
    existente = session.exec(stmt).first()
    produccion_reg = float(existente.cantidad_producida) if existente else 0.0

    # ---------- Construir texto explicativo ----------

    partes: list[str] = []

    partes.append(
        f"Para el día {fecha.isoformat()} te sugiero producir aproximadamente "
        f"{sugerida:.0f} unidades de '{prod.nombre}'."
    )
    partes.append(
        f"La base configurada para este producto es de {base:.0f} unidades "
        f"y el factor aplicado es {factor:.2f}."
    )

    # Motivos por contexto
    motivos: list[str] = []
    if ctx.es_feriado:
        motivos.append("es feriado")
    if ctx.es_fin_de_semana:
        motivos.append("es fin de semana")
    if ctx.clima:
        motivos.append(f"el clima se espera {ctx.clima.lower()}")
    if ctx.evento_especial and ctx.evento_especial.lower() not in ("", "ninguno", "ninguna"):
        motivos.append(f"hay un evento especial: {ctx.evento_especial}")

    if motivos:
        partes.append(
            "Se aumentó la sugerencia porque " + ", ".join(motivos) + "."
        )
    else:
        partes.append(
            "No hay feriado, fin de semana ni eventos especiales cargados, "
            "así que se usa la base sin ajustes adicionales."
        )

    # Info de producción ya cargada
    if existente:
        partes.append(
            f"Ya hay una producción registrada para ese día de "
            f"{produccion_reg:.0f} unidades. "
            f"Podés mantener ese valor o actualizarlo con el plan sugerido."
        )
    else:
        partes.append(
            "Actualmente no hay producción registrada para ese día en el sistema; "
            "si aceptás este plan, se crearán los registros de producción correspondientes."
        )

    texto_final = " ".join(partes)

    return ExplicacionPlanOut(
        fecha=fecha,
        producto_id=producto_id,
        producto_nombre=prod.nombre,
        produccion_base=base,
        factor_calculado=round(factor, 2),
        produccion_sugerida=sugerida,
        produccion_registrada=produccion_reg,
        texto=texto_final,
    )
