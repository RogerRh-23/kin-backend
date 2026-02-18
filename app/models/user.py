from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, AutoString
from pydantic import EmailStr

# 1. Definimos los Roles (Jerarquía)
class UserRole(str, Enum):
    DEV = "dev"             # Desarrollador (Acceso total + Crear Admins)
    ADMIN = "admin"         # Administrador (Acceso total)
    RECLUTADOR = "reclutador" # RH (Solo ver y crear empleados, no borrar historial)
    FINANANZAS = "finanzas"   # Nómina (Ver y editar datos de pago)
    SUPERVISOR = "supervisor"   # Pase de lista y reportes
    EMPLEADO = "empleado"   # Usuario final (Solo ver su propia info)

# 2. La Tabla de Usuarios
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Datos de Login
    email: str = Field(unique=True, index=True, sa_type=AutoString) 
    hashed_password: str # Aquí guardamos "xi8237s..." NO "123456"
    
    # Datos Personales
    nombre_completo: str
    
    # Control de Acceso
    role: UserRole = Field(default=UserRole.SUPERVISOR)
    is_active: bool = Field(default=True)