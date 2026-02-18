from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

# --- 1. ASISTENCIA / CHECADA ---
class Attendance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employee.id") # Relación con el empleado
    
    timestamp: datetime = Field(default_factory=datetime.now)
    tipo: str # "ENTRADA", "SALIDA"
    
    # Coordenadas (Para validar que checó en la fábrica y no en su casa)
    latitud: Optional[float]
    longitud: Optional[float]
    
    # Notas opcionales (Ej: "Llegué tarde por tráfico")
    notas: Optional[str] = None

# --- 2. INCIDENCIAS (Placeholder / Pendiente) ---
class Incident(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employee.id")
    fecha: datetime = Field(default_factory=datetime.now)
    
    # TODO: Esperar a la jefa para definir los campos reales
    # Por ahora usamos un campo genérico para no bloquear
    datos_temporales: str = Field(default="Pendiente de definición")