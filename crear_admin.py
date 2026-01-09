from sqlmodel import Session, select, SQLModel # <--- Importamos SQLModel
from app.core.db import engine
from app.models.user import User
from app.core.security import get_password_hash 

def create_first_user():
    # 1. PASO MAGICO: Forzamos la creación de tablas aquí mismo
    # Al importar 'User' arriba, SQLModel ya sabe qué tabla crear.
    print("🔨 Creando tablas en PostgreSQL...")
    SQLModel.metadata.create_all(engine)
    print("✅ Tablas creadas (o verificadas).")

    with Session(engine) as session:
        # 2. Verificar si existe
        user = session.exec(select(User).where(User.email == "admin@kin.com")).first()
        
        if user:
            print("⚠️ El usuario admin ya existe.")
            return

        # 3. Crear usuario
        new_user = User(
            email="admin@kin.com",
            full_name="Administrador Kin",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True
        )
        
        session.add(new_user)
        session.commit()
        print("🎉 Usuario 'admin@kin.com' creado exitosamente en PostgreSQL.")

if __name__ == "__main__":
    create_first_user()