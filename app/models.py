from sqlalchemy import Column, Integer, String, Boolean, Float, Date, DateTime
from sqlalchemy.sql import func
from .database import Base


class Empleado(Base):
    __tablename__ = "empleados"

    id = Column(Integer, primary_key=True, index=True)

    # Campos provenientes del CSV (según schemas.py)
    registro_patronal = Column(String, index=True, nullable=False)
    nss = Column(String, unique=True, index=True, nullable=False)
    nombre_completo = Column(String, nullable=False)
    sbc = Column(Float, nullable=False)
    clave_trabajador = Column(String, nullable=True)
    tipo_trabajador = Column(Integer, nullable=False)
    fecha_ingreso = Column(Date, nullable=False)
    tipo_movimiento = Column(Integer, nullable=False)
    guia = Column(String, nullable=True)
    curp = Column(String, unique=True, nullable=False)
    tipo_salario = Column(Integer, nullable=False)
    jornada = Column(Integer, nullable=False)

    # Campos opcionales adicionales
    rfc = Column(String, unique=True, nullable=True)
    email = Column(String, unique=True, nullable=True)
    telefono = Column(String, nullable=True)
    puesto = Column(String, nullable=True)
    departamento = Column(String, nullable=True)
    salario_diario = Column(Float, nullable=True)

    # Campos para compatibilidad con estructura anterior
    nombre = Column(String, nullable=True)
    apellido_paterno = Column(String, nullable=True)
    apellido_materno = Column(String, nullable=True)

    # Sistema
    is_active = Column(Boolean, default=True)
    fecha_registro = Column(Date, default=func.current_date())

    def __repr__(self):
        return f"<Empleado id={self.id} nombre_completo={self.nombre_completo} nss={self.nss}>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<User id={self.id} username={self.username} email={self.email}>"