# crear_estructura_panaderia.ps1
# Ejecutar este script desde la raíz del repo (C:\Proyectos\la-segunda-horneada)

$root = Get-Location

Write-Host "Creando carpetas de la aplicación..." -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path "$root\panaderia_core"        | Out-Null
New-Item -ItemType Directory -Force -Path "$root\panaderia_core\db"     | Out-Null
New-Item -ItemType Directory -Force -Path "$root\panaderia_core\servicios" | Out-Null
New-Item -ItemType Directory -Force -Path "$root\docs"                  | Out-Null

Write-Host "Creando .gitignore y requirements.txt..." -ForegroundColor Cyan

@'
__pycache__/
*.pyc
*.db
.env
.vscode/
.idea/
*.log
.vs/
node_modules/
'@ | Set-Content -Encoding utf8 "$root\.gitignore"

@'
fastapi
uvicorn
sqlmodel
'@ | Set-Content -Encoding utf8 "$root\requirements.txt"

Write-Host "Creando archivos de panaderia_core..." -ForegroundColor Cyan

# __init__.py vacío
New-Item -ItemType File -Force -Path "$root\panaderia_core\__init__.py" | Out-Null

# core_app.py
@'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from panaderia_core.db.conexion import crear_base_de_datos

app = FastAPI(
    title="API La Segunda Horneada",
    description="Sistema interno de planificación y producción para La Segunda Horneada (Artigas).",
    version="0.1.0",
)

# CORS: luego podemos limitar orígenes cuando tengas el front definido
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
    return {"mensaje": "API de La Segunda Horneada funcionando correctamente ✅"}
'@ | Set-Content -Encoding utf8 "$root\panaderia_core\core_app.py"

# conexion.py
@'
from sqlmodel import SQLModel, create_engine, Session

# Más adelante podemos mover esta URL a variables de entorno
DATABASE_URL = "sqlite:///./datos_panaderia.db"

motor = create_engine(DATABASE_URL, echo=False)


def crear_base_de_datos() -> None:
    """Crea las tablas en la base de datos si no existen."""
    SQLModel.metadata.create_all(motor)


def obtener_sesion():
    """Dependencia para FastAPI: genera una sesión de base de datos."""
    with Session(motor) as sesion:
        yield sesion
'@ | Set-Content -Encoding utf8 "$root\panaderia_core\db\conexion.py"

# modelos.py
@'
from typing import Optional
from sqlmodel import SQLModel, Field


class Producto(SQLModel, table=True):
    """
    Producto de panadería: pan, factura, torta, etc.
    Este es solo un modelo inicial para probar la estructura.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    categoria: str
    precio: float
    activo: bool = Field(default=True)
'@ | Set-Content -Encoding utf8 "$root\panaderia_core\db\modelos.py"

Write-Host "Creando módulos de servicios vacíos..." -ForegroundColor Cyan

$servicios = @(
    "autenticacion.py",
    "productos.py",
    "ventas.py",
    "registros_diarios.py",
    "reportes.py",
    "ia.py"
)

foreach ($svc in $servicios) {
    $ruta = Join-Path "$root\panaderia_core\servicios" $svc
    if (-Not (Test-Path $ruta)) {
        @("# Módulo de servicio: $svc`n# Aquí implementaremos la lógica correspondiente.") |
            Set-Content -Encoding utf8 $ruta
    }
}

Write-Host "Estructura creada correctamente ✅" -ForegroundColor Green
Write-Host "Recordá hacer commit y push desde GitHub Desktop." -ForegroundColor Yellow
