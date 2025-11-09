# reset_admin.py
from sqlmodel import select
from data import get_session, init_db
from domain import User, Role
from security import get_password_hash

def ensure_admin(email: str = "admin@alevosos.local", password: str = "admin123") -> str:
    init_db()
    for session in get_session():
        u = session.exec(select(User).where(User.email == email)).first()
        if not u:
            u = User(email=email, full_name="Admin", hashed_password=get_password_hash(password), role=Role.admin)
            session.add(u)
        else:
            u.hashed_password = get_password_hash(password)
            u.role = Role.admin
        session.commit()
        # aseguramos que los campos estén cargados y devolvemos un valor primitivo
        session.refresh(u)
        return u.email  # <- devolvemos string, no el objeto

if __name__ == "__main__":
    email = ensure_admin()
    print("Admin listo:", email)
