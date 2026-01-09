from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.core.db import get_session
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, Token
from app.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter()

# 1. REGISTRO DE USUARIO
@router.post("/register", response_model=UserRead)
def register(user: UserCreate, session: Session = Depends(get_session)):
    # Validar si el email ya existe
    existing_user = session.exec(select(User).where(User.email == user.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Crear usuario nuevo
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=get_password_hash(user.password),
        role="admin" # El primero siempre será admin por ahora
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

# 2. LOGIN (Generar Token)
@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    # Buscar usuario
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    
    # Validar password
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear Token
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}