from sqlmodel import Session, select
from app.core.db import engine
from app.models.user import User

def mask(s: str, head: int = 6, tail: int = 4):
    if not s:
        return "<empty>"
    if len(s) <= head + tail:
        return s
    return s[:head] + "..." + s[-tail:]

def analyze_hash(h: str):
    if not h:
        return "MISSING"
    if h.startswith("$2"):
        return "bcrypt"
    if h.startswith("$argon2") or h.startswith("$argon2i"):
        return "argon2"
    if h.startswith("pbkdf2_") or "pbkdf2" in h:
        return "pbkdf2"
    if h.startswith("$"):
        return "unknown_scheme"
    # otherwise probably plaintext or legacy
    if len(h) < 20:
        return "short_plain_or_truncated"
    return "plain_or_unknown"

def main():
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        if not users:
            print("No users found in DB.")
            return
        print(f"Found {len(users)} users:\n")
        for u in users:
            h = getattr(u, "hashed_password", None)
            print(f"id={u.id} email={u.email} active={u.is_active} role={u.role}")
            print(f"  hashed_password mask={mask(h)} type={analyze_hash(h)} len={len(h) if h else 0}")
            print()

if __name__ == '__main__':
    main()
