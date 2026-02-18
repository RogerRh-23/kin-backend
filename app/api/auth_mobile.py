from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.db import get_session
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.models.employee import Employee
from pydantic import BaseModel

router = APIRouter(prefix="/auth/mobile", tags=["Mobile Auth"])

# Esquema simple para recibir los datos
class MobileLoginRequest(BaseModel):
    identifier: str # Puede ser email O username generado
    credential: str # Puede ser password O pin

@router.post("/login")
def mobile_login(data: MobileLoginRequest, session: Session = Depends(get_session)):
    """
    Login Inteligente:
    1. Busca si es Supervisor (Email).
    2. Si no, busca si es Operador (Username).
    """
    
    # --- CASO A: ¿ES SUPERVISOR? (Busca por Email en tabla User) ---
    user = session.exec(select(User).where(User.email == data.identifier)).first()
    
    if user:
        if verify_password(data.credential, user.hashed_password):
            # ¡Es Supervisor!
            return {
                "access_token": create_access_token(subject=user.email, role=user.role),
                "token_type": "bearer",
                "mode": "SUPERVISOR",
                "user_name": user.nombre_completo
            }
            
    # --- CASO B: ¿ES OPERADOR? (Busca por Username en tabla Employee) ---
    # Nota: Asumimos que el PIN también se guarda con hash usando passlib/argon2
    employee = session.exec(select(Employee).where(Employee.username_operativo == data.identifier)).first()
    
    if employee:
        # Verificamos el PIN contra el hash guardado
        if employee.hashed_pin and verify_password(data.credential, employee.hashed_pin):
            # ¡Es Operador!
            return {
                "access_token": create_access_token(subject=str(employee.id), role="operador"),
                "token_type": "bearer",
                "mode": "OPERARIO",
                "user_name": employee.nombre_completo,
                "employee_id": employee.id
            }

    # Si llega aquí, falló todo
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales incorrectas (Usuario o PIN/Pass inválido)",
    )