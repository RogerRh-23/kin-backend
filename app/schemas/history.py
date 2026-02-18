from pydantic import BaseModel
from typing import Optional
from datetime import date

class TerminationRequest(BaseModel):
    motivo: str
    comentarios: Optional[str] = None
    recontratable: bool # ¿Lo volverías a contratar? Sí/No

class HistoryRead(BaseModel):
    id: int
    fecha_movimiento: date
    tipo_movimiento: str
    motivo: str
    comentarios: Optional[str]
    recontratable: bool