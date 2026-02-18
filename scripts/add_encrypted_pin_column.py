from sqlalchemy import text
from app.core.db import engine

def column_exists(conn):
    q = text("""
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'employee' AND column_name = 'encrypted_pin'
    """)
    res = conn.execute(q).first()
    return bool(res)

def main():
    with engine.connect() as conn:
        if column_exists(conn):
            print("La columna 'encrypted_pin' ya existe en la tabla 'employee'. Nada que hacer.")
            return

        print("Agregando columna 'encrypted_pin' a la tabla 'employee'...")
        conn.execute(text("ALTER TABLE \"employee\" ADD COLUMN encrypted_pin TEXT"))
        conn.commit()
        print("Columna agregada correctamente.")

if __name__ == '__main__':
    main()
