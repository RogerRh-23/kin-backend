from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.db import create_db_and_tables
from app.models.user import User 
from app.models.employee import Employee
from app.api import auth, users, employees
from app.api.auth_mobile import MobileLoginRequest
from app.api import users, auth, employees, auth_mobile

# --- 1. CONFIGURACIÓN DE ARRANQUE (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Esto ocurre cuando el servidor se enciende
    print("🔄 Inicializando base de datos...")
    create_db_and_tables()
    print("🟢 Base de datos lista y tablas verificadas.")
    
    yield # Aquí el servidor queda activo
    
    # Esto ocurre cuando el servidor se apaga
    print("🔴 Servidor apagándose...")

# --- 2. CREACIÓN DE LA APP (UNA SOLA VEZ) ---
app = FastAPI(
    title="Kin ERP API",
    description="Backend para gestión de Nómina, RH y SUA",
    version="1.0.0",
    lifespan=lifespan
)

# --- 3. CONFIGURACIÓN DE CORS ---
origins = [
    "http://localhost:3000",
    "http://localhost:8081",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4. REGISTRO DE RUTAS ---
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(employees.router)
app.include_router(auth_mobile.router)

# --- 5. ENDPOINTS DE PRUEBA ---
@app.get("/")
def read_root():
    return {
        "sistema": "Kin ERP", 
        "estado": "Operativo 🟢", 
        "bd": "PostgreSQL Conectado 🐘"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}