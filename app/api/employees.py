from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from app.core.db import get_session
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeOut

router = APIRouter()

@router.post("/", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(data: EmployeeCreate, session: Session = Depends(get_session)):
    # Verificar si el RFC ya existe para no duplicar
    existing = session.exec(select(Employee).where(Employee.rfc == data.rfc)).first()
    if existing:
        raise HTTPException(status_code=400, detail="El RFC ya está registrado")
    
    # Convertir esquema a modelo de base de datos
    db_employee = Employee.model_validate(data)
    session.add(db_employee)
    session.commit()
    session.refresh(db_employee)
    return db_employee

@router.get("/", response_model=List[EmployeeOut])
def list_employees(session: Session = Depends(get_session)):
    employees = session.exec(select(Employee)).all()
    return employees