from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from .. import models, schemas
from ..database import get_db
import hashlib, os, binascii
from datetime import datetime, timedelta
import jwt
import os as _os

router = APIRouter()

# JWT settings
SECRET_KEY = _os.environ.get("SECRET_KEY", "change-this-secret-for-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day by default


class AuthRequest:
    from pydantic import BaseModel
    class Model(BaseModel):
        username: str
        password: str


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return binascii.hexlify(salt).decode() + ":" + binascii.hexlify(dk).decode()


def _verify_password(stored: str, password: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split(":")
    except Exception:
        return False
    salt = binascii.unhexlify(salt_hex)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return binascii.hexlify(dk).decode() == dk_hex


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = {"sub": subject}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter((models.User.username == user.username) | (models.User.email == user.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with that username or email already exists")
    hashed = _hash_password(user.password)
    db_user = models.User(username=user.username, email=user.email, hashed_password=hashed, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login")
def login(payload: AuthRequest.Model, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not _verify_password(user.hashed_password, payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(subject=user.username)
    return {"access_token": access_token, "token_type": "bearer"}
