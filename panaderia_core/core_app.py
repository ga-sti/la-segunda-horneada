# panaderia_core/core_app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from panaderia_core.db.conexion import init_db
from panaderia_core.servicios import (
    autenticacion,
    productos,
    ventas,
    reportes,
    # registros_diarios  # se suma en Etapa 3
)


app = FastAPI(title="La Segunda Horneada API")


# ---------- CORS ----------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # En producción se puede restringir al dominio del front
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Eventos de arranque ----------

@app.on_event("startup")
def on_startup() -> None:
    """
    Inicializa la base de datos de la panadería al arrancar la app.
    """
    init_db()

# Routers principales de Etapa 2
app.include_router(
    autenticacion.router,
    prefix="/api/auth",
    tags=["Autenticacion"],
)
app.include_router(
    productos.router,
    prefix="/api/productos",
    tags=["Productos"],
)
app.include_router(
    ventas.router,
    prefix="/api/ventas",
    tags=["Ventas"],
)
app.include_router(
    reportes.router,
    prefix="/api/reportes",
    tags=["Reportes"],
)


# ---------- Endpoint de salud básico ----------

@app.get("/api/salud")
def check_salud():
    """
    Endpoint de prueba para verificar que la API está corriendo.
    """
    return {
        "estado": "ok",
        "mensaje": "API La Segunda Horneada funcionando",
    }


# En Etapa 2 montaremos los routers:
# app.include_router(autenticacion.router, prefix="/api/auth", tags=["Autenticacion"])
# app.include_router(productos.router, prefix="/api/productos", tags=["Productos"])
# app.include_router(ventas.router, prefix="/api/ventas", tags=["Ventas"])
# app.include_router(registros_diarios.router, prefix="/api", tags=["RegistrosDiarios"])
# app.include_router(reportes.router, prefix="/api/reportes", tags=["Reportes"])
