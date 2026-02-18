from datetime import date
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

class EmploymentHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employee.id")
    
    fecha_movimiento: date = Field(default_factory=date.today)
    tipo_movimiento: str # Ej: "BAJA", "REINGRESO", "ACTA_ADMINISTRATIVA"
    
    motivo: str # Ej: "Renuncia voluntaria", "Robo", "Ausentismo"
    comentarios: Optional[str] = None
    
    # EL SEMÁFORO: True (Verde/Recontratable), False (Rojo/Vetado)
    recontratable: bool = Field(default=True) 
    
    # Relación inversa (apunta al empleado)
    employee: "Employee" = Relationship(back_populates="history")