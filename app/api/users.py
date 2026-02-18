from sqlmodel import Session, select
from typing import List
from app.api.auth import get_current_user
from app.api.deps import get_current_dev_user
from app.core.db import get_session
from app.models.user import User
from app.schemas.user import UserCreate, UserRead
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import hash_password

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/register", response_model=UserRead)
def register_user(
    user_data: UserCreate, 
    session: Session = Depends(get_session),
):
    # 1. Validar que el email no exista
    existing_user = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="El correo electrónico ya está registrado."
        )
    
    # 2. Encriptar contraseña
    hashed_pwd = hash_password(user_data.password)

    # 3. Crear usuario
    new_user = User(
        email=user_data.email,
        nombre_completo=user_data.nombre_completo,
        hashed_password=hashed_pwd,
        role=user_data.role,
        is_active=True
    )

    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear usuario: {str(e)}")
    

@router.get("/me", response_model=UserRead)
def get_current_user_data(current_user: User = Depends(get_current_user)):
    """
    Endpoint para que el Frontend recupere los datos del usuario logueado
    usando su Token.
    """
    return current_user

# --- 1. LISTAR TODOS LOS USUARIOS ---
@router.get("/", response_model=List[UserRead])
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_dev_user) # Candado DEV
):
    """Ver lista completa de usuarios (Solo DEV)"""
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return users

# --- 2. EDITAR ROL DE USUARIO ---
@router.put("/{user_id}/role")
def update_user_role(
    user_id: int, 
    new_role: str, # "admin", "reclutador", etc.
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_dev_user)
):
    """Cambiar el rol de un usuario (Ascender/Degradar)"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.role = new_role
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"mensaje": f"Rol actualizado a {new_role}", "usuario": user.email}

# --- 3. TOGGLE ACTIVO/INACTIVO (En lugar de borrar) ---
@router.put("/{user_id}/toggle-status")
def toggle_user_status(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_dev_user)
):
    """Activar o Desactivar acceso al sistema (Banear)"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Si estaba True pasa a False, y viceversa
    user.is_active = not user.is_active
    
    session.add(user)
    session.commit()
    
    estado = "Activado" if user.is_active else "Desactivado"
    return {"mensaje": f"Usuario {estado} exitosamente"}