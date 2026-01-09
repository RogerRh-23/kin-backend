from pydantic import BaseModel, EmailStr

# Lo que recibimos al registrar un usuario
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

# Lo que devolvemos al frontend (¡NUNCA devolvemos el password!)
class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    role: str

# Lo que devolvemos al hacer Login
class Token(BaseModel):
    access_token: str
    token_type: str