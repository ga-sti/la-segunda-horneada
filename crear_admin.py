# crear_admin.py
from sqlmodel import Session, select

from panaderia_core.db.conexion import engine, init_db
from panaderia_core.db.modelos import Usuario, Role
from panaderia_core.security import get_password_hash


def main():
    init_db()

    email = "admin@lasegundahorneada.com"
    nombre = "Admin"
    # 👉 NUEVA CLAVE:
    password_plano = "admin"

    with Session(engine, expire_on_commit=False) as session:
        existente = session.exec(
            select(Usuario).where(Usuario.email == email)
        ).first()

        if existente:
            # 👉 Si ya existe, solo le cambio la contraseña y me voy
            existente.password_hash = get_password_hash(password_plano)
            existente.rol = Role.admin
            existente.activo = True
            session.add(existente)
            session.commit()
            print(
                f"Contraseña ACTUALIZADA para {email}. "
                f"Nueva clave = {password_plano!r}"
            )
            return

        # Si no existe, lo creo
        user = Usuario(
            email=email,
            nombre=nombre,
            password_hash=get_password_hash(password_plano),
            rol=Role.admin,
            activo=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(
            f"Usuario admin creado: id={user.id}, email={user.email}, "
            f"clave={password_plano!r}"
        )


if __name__ == "__main__":
    main()
