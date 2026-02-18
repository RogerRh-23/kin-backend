from pydantic import BaseModel, EmailStr
from app.models.user import UserRole

# Lo que recibes al crear un usuario
class UserCreate(BaseModel):
    nombre_completo: str
    email: EmailStr
    password: str
    role: UserRole

# Lo que respondes (¡SIN la contraseña!)
class UserRead(BaseModel):
    id: int
    nombre_completo: str
    email: str
    role: UserRole
    is_active: bool