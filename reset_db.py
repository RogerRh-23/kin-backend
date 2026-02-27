from sqlmodel import SQLModel
from app.core.db import engine

from app.models.employee import Employee, Beneficiary
from app.models.history import EmploymentHistory
from app.models.operations import Attendance, Incident

def reset_database():
    print("------------------------------------------------")
    print("[1] DELETINDO TABLAS ANTIGUAS...")
    try:
        SQLModel.metadata.drop_all(engine)
        print("   -> Tablas eliminadas correctamente.")
    except Exception as e:
        print(f"   -> Advertencia al borrar: {e}")

    print("\n[2] CREANDO TABLAS NUEVAS...")
    try:
        # Esto lee los modelos importados arriba y crea las tablas
        SQLModel.metadata.create_all(engine)
        print("   -> Tablas creadas.")
        print("   -> Tabla 'user' debe tener: email, hashed_password, nombre_completo, role")
    except Exception as e:
        print(f"   -> ERROR AL CREAR: {e}")
        
    print("------------------------------------------------")
    print("[OK] BASE DE DATOS ACTUALIZADA!")

if __name__ == "__main__":
    reset_database()