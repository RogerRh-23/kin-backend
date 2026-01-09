from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.db import init_db
from app.models.user import User 
from app.api import auth, users

# --- CONFIGURACIÓN DE ARRANQUE (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Esto se ejecuta ANTES de que el servidor acepte peticiones
    print("🔄 Inicializando base de datos...")
    init_db()
    print("🟢 Base de datos lista y tablas creadas (si no existían).")
    yield
    # Esto se ejecutaría cuando apagues el servidor (limpieza)
    print("🔴 Servidor apagándose...")

# --- CREACIÓN DE LA APP ---
app = FastAPI(
    title="Kin ERP API",
    description="Backend para gestión de Nómina, RH y SUA",
    version="1.0.0",
    lifespan=lifespan # <--- Aquí conectamos la lógica de arranque
)

# --- CONFIGURACIÓN DE CORS ---
origins = [
    "http://localhost:3000",  # Next.js / Web
    "http://localhost:8081",  # Expo Web
    "*",                      # Móviles y emuladores
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
app.include_router(users.router, prefix="/users", tags=["Usuarios"])

# --- RUTAS DE PRUEBA ---
@app.get("/")
def read_root():
    return {
        "sistema": "Kin ERP", 
        "estado": "Operativo 🟢", 
        "bd": "Conectada"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}