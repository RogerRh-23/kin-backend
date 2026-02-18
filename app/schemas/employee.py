from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator, ConfigDict
from decimal import Decimal

# --- Esquema para Beneficiarios ---
class BeneficiaryBase(BaseModel):
    nombre_completo: str
    parentesco: str
    porcentaje: Decimal = Field(ge=0, le=100)

# --- Esquema Principal de Empleado ---
class EmployeeBase(BaseModel):
    # Identificación Básica
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    nss: str
    rfc: str
    curp: str
    domicilio_completo: str
    
    # Datos Laborales (CIT / IMSS)
    puesto: str
    actividades_detalle: str
    cliente_nombre: str
    cliente_rfc: str
    tipo_salario: str
    salario_diario: Decimal
    factor_integracion: Decimal = Decimal("1.0493")
    sdi: Decimal
    empresa_pagadora: str
    fecha_alta_imss: date
    registro_patronal: str
    clase_rt: str
    
    # Datos Personales
    fecha_nacimiento: date
    estado_civil: str
    sexo: str
    nacionalidad: str = "MEXICANO"
    domicilio_laboral: str
    
    # Seguridad Social
    tiene_infonavit: str 
    numero_credito_infonavit: Optional[str] = None
    
    # Contrato y Proyecto
    tipo_contrato: str
    duracion_contrato: str
    nombre_proyecto: Optional[str] = "NA"
    consiste_proyecto: Optional[str] = "NA"
    
    # Nómina y Pagos
    forma_pago: str 
    se_le_paga_por: str
    sueldo_mensual_bruto: Decimal
    sueldo_mensual_neto: Decimal
    banco: Optional[str] = "NA"
    cuenta_bancaria: Optional[str] = "NA"
    clabe_interbancaria: Optional[str] = "NA"
    
    # Tallas (Control Operativo)
    talla_camisa: Optional[str] = "NA"
    talla_pantalon: Optional[str] = "NA"
    talla_calzado: Optional[str] = "NA"

    # Datos para App Operativa
    es_operativo: bool = False
    username_operativo: Optional[str] = None
    hashed_pin: Optional[str] = None

# --- Esquema para cuando RECIBES datos (Create) ---
class EmployeeCreate(EmployeeBase):
    beneficiaries: List[BeneficiaryBase] = []

    @model_validator(mode='after')
    def validate_identity_dates(self) -> 'EmployeeCreate':
        expected_date = self.fecha_nacimiento.strftime("%y%m%d")
        
        # 1. Validar RFC (Longitud mínima 10 para evitar error de índice)
        if len(self.rfc) >= 10:
            rfc_date = self.rfc[4:10]
            if rfc_date != expected_date:
                raise ValueError(f"El RFC ({rfc_date}) no coincide con nacimiento ({expected_date})")
        
        # 2. Validar CURP (Igual lógica)
        if len(self.curp) >= 10:
            curp_date = self.curp[4:10]
            if curp_date != expected_date:
                raise ValueError(f"La CURP ({curp_date}) no coincide con nacimiento ({expected_date})")
                
        return self

# --- Esquema para cuando ENVIAS datos (Read) ---
class EmployeeRead(EmployeeBase):
    id: int
    edad: int # Dato calculado
    beneficiaries: List[BeneficiaryBase] = []

    # Configuración para Pydantic V2 (compatible con ORM/SQLModel)
    model_config = ConfigDict(from_attributes=True)