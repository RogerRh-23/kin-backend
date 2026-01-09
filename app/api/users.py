from fastapi import APIRouter, Depends
from app.models.user import User
from app.core.security import settings, jwt
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated

router = APIRouter()

# Esto le dice a FastAPI dónde buscar el token (en la URL /auth/token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Dependencia: Verifica si el token es real y devuelve el usuario
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    # Aquí decodificaríamos el token real, por ahora simulamos
    # En la fase siguiente implementaremos la validación real contra DB
    return {"token_recibido": token, "user": "admin_validado"}

@router.get("/me")
def read_users_me(current_user: Annotated[dict, Depends(get_current_user)]):
    return current_user