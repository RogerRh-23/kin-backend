import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlmodel import Session, select
from app.core.db import get_session
from app.models.user import User
from app.core.security import verify_password

load_dotenv()  # Carga variables de entorno desde un archivo .env

router = APIRouter(tags=["Authentication"])

# --- CONFIGURACIÓN DE SEGURIDAD ---
# EN PRODUCCIÓN: Esto debe ir en variables de entorno (.env)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 horas de sesión

# Esto le dice a FastAPI dónde buscar el token (en la URL /auth/token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# --- FUNCIONES DE TOKEN (JWT) ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    # Aquí metemos el ROL dentro del token para que viaje seguro
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- DEPENDENCIA: OBTENER USUARIO ACTUAL ---
# Esta función servirá para proteger rutas: @router.get("/", deps=[Depends(get_current_user)])
async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise credentials_exception
    return user


def require_role(role: str):
    """Dependency factory that requires the token to include a given role."""
    def _require(token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No se pudieron validar las credenciales")
        token_role = payload.get("role")
        if token_role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        return payload
    return _require

# --- ENDPOINT: LOGIN (Generar Token) ---
@router.post("/login")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    session: Session = Depends(get_session)
):
    # 1. Buscar usuario por email (form_data.username es el email aquí)
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    
    # 2. Verificar contraseña y existencia
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Verificar si está activo
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")

    # 4. Generar Token con el ROL incluido
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email, 
            "role": user.role,       # <--- ¡IMPORTANTE! El rol viaja en el token
            "id": user.id,
            "nombre": user.nombre_completo
        }, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/logout")
def logout():
    """
    Endpoint de Logout.
    Nota: En JWT no se "destruye" el token, pero el frontend puede eliminarlo.
    """
    return {"message": "Logout exitoso. Elimina el token en el cliente."}