from datetime import datetime, timedelta
from typing import Optional
import os
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from cryptography.fernet import Fernet

# Support argon2 and bcrypt so we can verify existing hashes stored with Argon2
# Argon2 requires the `argon2-cffi` package to be installed in the environment.
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except UnknownHashError:
        # Hashed value isn't recognized by passlib (possibly plaintext or legacy format).
        # Return False to avoid crashing the app; callers will treat as authentication failure.
        return False


def get_password_hash(password: str) -> str:
    """Compatibility alias used by some scripts (e.g. crear_admin.py)."""
    return hash_password(password)


# --- Reversible encryption for PINs (Fernet) ---
PIN_KEY_ENV = "SECRET_PIN_KEY"

def _get_fernet():
    key = os.environ.get(PIN_KEY_ENV)
    if not key:
        # Generate ephemeral key for dev if not set; in prod store in env or KMS
        key = Fernet.generate_key().decode()
        os.environ[PIN_KEY_ENV] = key
        # Note: generating a key here means encrypted values won't be readable across restarts
    return Fernet(key.encode())


def encrypt_pin(plain: str) -> str:
    f = _get_fernet()
    return f.encrypt(plain.encode()).decode()


def decrypt_pin(token: str) -> str:
    f = _get_fernet()
    return f.decrypt(token.encode()).decode()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)