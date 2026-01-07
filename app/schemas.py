from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, datetime

class EmpleadoBase(BaseModel):
    
    # Columna 1: Registro Patronal (Ej. Y6638495105)
    registro_patronal: str 
    
    # Columna 2: NSS (Número de Seguridad Social)
    nss: str 
    
    # Columna 3: Nombre Completo (Como viene en el CSV: APELLIDOS + NOMBRE)
    nombre_completo: str 
    
    # Columna 4: Salario Diario Integrado (Equivale a tu SBC)
    sbc: float 
    
    # Columna 5: Clave del Trabajador (ID interno o nulo)
    clave_trabajador: Optional[str] = None 
    
    # Columna 6: Tipo de Trabajador (Ej. 1 = Permanente)
    tipo_trabajador: int 
    
    # Columna 7: Fecha de Movimiento (Ingreso)
    # Nota: El CSV trae formato dd/mm/yyyy, el backend debe parsearlo antes 
    # o recibirlo como string y convertirlo. Aquí lo dejo como date asumiendo conversión previa.
    fecha_ingreso: date 
    
    # Columna 8: Tipo de Movimiento (Ej. 08 = Reingreso, 07 = Ingreso)
    tipo_movimiento: int 
    
    # Columna 9: Guía (Opcional)
    guia: Optional[str] = None 
    
    # Columna 10: CURP
    curp: str 
    
    # Columna 11: Tipo de Salario (0 = Fijo, 1 = Variable, 2 = Mixto)
    tipo_salario: int 
    
    # Columna 12: Jornada (Ej. 0, 1, etc.)
    jornada: int 

    # --- Datos que NO vienen en el CSV (Ahora deben ser Opcionales) ---
    # Como el archivo no trae estos datos, si son obligatorios tu carga fallará.
    # Los he puesto como Optional para que puedas crear el empleado solo con la info del CSV.
    
    rfc: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    puesto: Optional[str] = None
    departamento: Optional[str] = None
    
    # Si usas el salario_diario (nominal) diferente al integrado, 
    # déjalo opcional porque el CSV solo trae el Integrado.
    salario_diario: Optional[float] = None 

    # Opcional: Separación de nombres si deseas mantener tu estructura anterior
    # pero llenarla después procesando el 'nombre_completo'
    nombre: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None

class EmpleadoCreate(EmpleadoBase):
    # Aquí podrías agregar validaciones extra si es necesario
    pass

class Empleado(EmpleadoBase):
    id: int
    is_active: bool
    fecha_registro: Optional[date] = None

    model_config = {"from_attributes": True}


# --- User schemas ---
class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    role: Optional[str] = "user"


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None