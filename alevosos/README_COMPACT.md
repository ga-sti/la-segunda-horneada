# Alevosos Studio – API Compacta (v1)
Arquitectura compacta para desarrollo rápido.

## Archivos
- `app.py` – FastAPI con todas las rutas (auth, clientes, servicios, ventas, gastos, reportes, caja).
- `domain.py` – Enums y modelos SQLModel.
- `data.py` – Engine/Session y `init_db()`.
- `security.py` – Hash de contraseñas y JWT.
- `reset_admin.py` – Crea/actualiza admin por defecto.
- `requirements.txt` – Dependencias.

## Cómo correr
```bash
# 1) Crear entorno (opcional) e instalar deps
pip install -r requirements.txt

# 2) Inicializar DB y crear admin
python reset_admin.py   # Crea admin@alevosos.local / admin123

# 3) Levantar la API
uvicorn app:app --reload --port 8000
```

El frontend debe apuntar a `VITE_API_URL=http://localhost:8000`.

## Notas
- Base de datos: SQLite en `./data.db` (variable `DATABASE_URL` para cambiar).
- Seguridad: personalizar `SECRET_KEY` con una variable de entorno.
- Endpoints principales:
  - `POST /auth/login` (OAuth2PasswordRequestForm)
  - `GET/POST /clientes/`
  - `GET/POST /servicios/`
  - `GET/POST /ventas/`
  - `GET/POST /gastos/`
  - `GET /reportes/resumen?desde=YYYY-MM-DD&hasta=YYYY-MM-DD`
  - `GET /caja/resumen?fecha=YYYY-MM-DD`
  - `POST /caja/abrir` `{fecha, apertura, observaciones?}`
  - `POST /caja/cerrar` `{fecha, cierre, observaciones?}`
  - `GET /caja/verificar_dia?fecha=YYYY-MM-DD&tolerancia=1`
  - `GET /caja/verificar?desde=YYYY-MM-DD&hasta=YYYY-MM-DD&tolerancia=1`
```
