from fastapi import Depends, HTTPException, status
from app.models.user import User, UserRole
from app.api.auth import get_current_user # Importamos la validación básica del token

# --- CANDADO 1: SOLO ADMIN O DEV (Para bajas, nómina, etc.) ---
def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """
    Permite el paso si el usuario es ADMIN o DEV.
    Rechaza a Reclutadores y Operadores.
    """
    if current_user.role not in [UserRole.DEV, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No tienes permisos suficientes (Se requiere Administrador)"
        )
    return current_user

# --- CANDADO 2: SOLO DEV (Para crear usuarios, ver logs, etc.) ---
def get_current_dev_user(current_user: User = Depends(get_current_user)):
    """
    NIVEL DIOS: Solo permite el paso al rol DEV.
    Rechaza incluso a los Administradores.
    """
    if current_user.role != UserRole.DEV:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acceso restringido: Solo para Desarrolladores"
        )
    return current_user