from typing import Optional
from datetime import date
from sqlmodel import Field, SQLModel

class Employee(SQLModel, table=True):
    # --- ID INTERNO ---
    id: Optional[int] = Field(default=None, primary_key=True)

    # --- DATOS PERSONALES ---
    first_name: str
    last_name_father: str
    last_name_mother: Optional[str] = None

    birth_date: Optional[date] = None
    birth_place: Optional[str] = None

    gender: str
    marital_status: str
    address: str

    # --- IDENTIFICACIÓN LEGAL ---
    curp: str = Field(unique=True, index=True)
    rfc: str = Field(unique=True)
    nss: str = Field(unique=True)

    # --- DATOS LABORALES ---
    job_title: str
    start_date: date # Fecha de alte del imss
    contract_type: str # 'permanent', 'temporary', 'outsourced', etc.
    work_location: str # Ciudad o sucursal

    # --- DATOS DE NOMINA ---
    bank_name: Optional[str] = None # Nombre del banco
    bank_account: Optional[str] = None # Número de cuenta bancaria
    clabe: Optional[str] = None # CLABE interbancaria

    # --- META ---
    is_active: bool = Field(default=True)
