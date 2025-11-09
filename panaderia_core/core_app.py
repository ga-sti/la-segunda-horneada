from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from panaderia_core.db.conexion import crear_base_de_datos

app = FastAPI(
    title="API La Segunda Horneada",
    description="Sistema interno de planificaciÃ³n y producciÃ³n para La Segunda Horneada (Artigas).",
    version="0.1.0",
)

# CORS: luego podemos limitar orÃ­genes cuando tengas el front definido
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def al_iniciar():
    """Se ejecuta cuando arranca la API."""
    crear_base_de_datos()


@app.get("/api/salud", tags=["Sistema"])
def comprobar_estado():
    """Endpoint simple para verificar que la API funciona."""
    return {"mensaje": "API de La Segunda Horneada funcionando correctamente âœ…"}
