# panaderia_core/servicios/autenticacion.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from panaderia_core.db.conexion import get_session
from panaderia_core.db.modelos import Usuario, Role
from panaderia_core.security import (
    verify_password,
    create_access_token,
    get_current_user,
    require_role,
)

router = APIRouter()


@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    # Igual que en Alevosos, pero usando Usuario
    user = session.exec(
        select(Usuario).where(Usuario.email == form.username)
    ).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario o contraseña incorrectos",
        )
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def leer_perfil(
    user: Usuario = Depends(get_current_user),
):
    # Endpoint útil para pruebas de auth
    return {
        "id": user.id,
        "email": user.email,
        "nombre": user.nombre,
        "rol": user.rol,
        "activo": user.activo,
    }
