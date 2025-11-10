# panaderia_core/security.py
# Auth helpers (bcrypt + JWT) adaptados a La Segunda Horneada

from datetime import datetime, timedelta
from typing import Optional, Callable
import os

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from panaderia_core.db.modelos import Usuario, Role
from panaderia_core.db.conexion import get_session


SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_SUPER_SECRET")
ALGO = "HS256"
ACCESS_MIN = int(os.getenv("ACCESS_MINUTES", "720"))  # 12h default

pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Importante: ahora apunta a /api/auth/login
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_password_hash(p: str) -> str:
    return pwd.hash(p)


def verify_password(raw: str, hashed: str) -> bool:
    return pwd.verify(raw, hashed)


def create_access_token(subject: str, minutes: int = ACCESS_MIN) -> str:
    to_encode = {
        "sub": subject,
        "exp": datetime.utcnow() + timedelta(minutes=minutes),
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGO)


def get_current_user(
    token: str = Depends(oauth2),
    session: Session = Depends(get_session),
) -> Usuario:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = session.exec(
        select(Usuario).where(Usuario.email == email)
    ).first()
    if not user or not user.activo:
        raise credentials_exc
    return user


def require_role(*roles: Role) -> Callable:
    def dep(user: Usuario = Depends(get_current_user)) -> Usuario:
        if roles and user.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permisos para esta operación",
            )
        return user

    return dep
