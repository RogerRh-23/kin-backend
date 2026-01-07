# main.py - FastAPI con CORS y autenticación funcional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
from typing import Optional

# Importa tus modelos existentes
try:
    from . import models, schemas
    from .database import engine, get_db
    models.Base.metadata.create_all(bind=engine)
except ImportError:
    # Si no tienes los módulos, comenta estas líneas
    print("Warning: No se encontraron módulos de DB. Usando modo de prueba.")
    def get_db():
        return None

app = FastAPI(title="Kin ERP API", version="1.0.0")

# CORS configurado correctamente - SIN "*" cuando allow_credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",      # Expo web
        "http://127.0.0.1:8081", 
        "http://localhost:19006",     # Expo web alternativo
        "http://127.0.0.1:19006",
        "http://localhost:3000",      # React dev server
        "http://127.0.0.1:3000",
        "http://localhost:19000",     # Expo dev tools
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Schemas para autenticación
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: Optional[int] = None
    email: Optional[str] = None

class User(BaseModel):
    id: int
    email: str
    nombre: Optional[str] = None

# Secret key para JWT (en producción usar variable de entorno)
SECRET_KEY = "tu-secret-key-super-secreto"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security scheme
security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# === RUTAS PRINCIPALES ===

@app.get("/")
def read_root():
    return {
        "Sistema": "Kin ERP", 
        "Estado": "Conectado y operativo!",
        "timestamp": datetime.utcnow().isoformat(),
        "cors_enabled": True
    }

# Include auth router from app.auth
from .auth import login as auth_router
from .auth.security import get_current_user
app.include_router(auth_router.router, prefix="/auth")

# === RUTAS DE EMPLEADOS (tus rutas existentes) ===

@app.post("/empleados/")
def create_empleado(empleado: dict, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Crear empleado - adaptado para funcionar sin schemas específicos
    """
    print(f"📝 Creating empleado: {empleado}")
    # Aquí irá tu lógica de DB cuando esté configurada
    return {"message": "Empleado creado", "data": empleado, "id": 123}

@app.get("/empleados/")
def read_empleados(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Listar empleados
    """
    print(f"📋 Fetching empleados (skip={skip}, limit={limit})")
    # Datos de prueba mientras configuras la DB
    empleados = [
        {"id": 1, "nombre": "Juan Pérez", "email": "juan@empresa.com", "activo": True},
        {"id": 2, "nombre": "María López", "email": "maria@empresa.com", "activo": True},
    ]
    return empleados[skip:skip + limit]

# Note: CORS preflight is handled by CORSMiddleware

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Kin ERP API...")
    print("📋 Available endpoints:")
    print("  GET  /                 - API status")
    print("  POST /auth/login       - Login (email/password)")
    print("  GET  /auth/me          - Current user info")
    print("  GET  /empleados/       - List employees")
    print("  POST /empleados/       - Create employee")
    print("\n🔧 Test credentials:")
    print("  Email: admin@empresa.com")
    print("  Password: admin123")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)