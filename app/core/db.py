from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

# El argumento check_same_thread es necesario SOLO para SQLite
connect_args = {"check_same_thread": False}

# Creamos el motor usando la URL de tu .env
engine = create_engine(
    settings.DATABASE_URL, 
    echo=True, # echo=True nos muestra las consultas SQL en la terminal (genial para debug)
    connect_args=connect_args
)

def get_session():
    with Session(engine) as session:
        yield session

def init_db():
    # Esta función crea las tablas automáticamente si no existen
    SQLModel.metadata.create_all(engine)