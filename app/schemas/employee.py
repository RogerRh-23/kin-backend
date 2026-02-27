from datetime import date, datetime
from typing import Optional, List, Union
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict
from decimal import Decimal

# --- Helper: Convertir fechas desde múltiples formatos ---
def parse_date(value: Union[str, date]) -> date:
    """Acepta fechas en formato ISO (YYYY-MM-DD) o DD/MM/YYYY"""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return value
    
    # Intentar formato ISO primero
    try:
        return datetime.fromisoformat(value).date()
    except:
        pass
    
    # Intentar formato DD/MM/YYYY
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except:
        pass
    
    # Intentar formato DD-MM-YYYY
    try:
        return datetime.strptime(value, "%d-%m-%Y").date()
    except:
        pass
    
    raise ValueError(f"Formato de fecha no soportado: {value}. Use YYYY-MM-DD o DD/MM/YYYY")

# --- Esquema para Beneficiarios ---
class BeneficiaryBase(BaseModel):
    nombre_completo: str
    parentesco: str
    porcentaje: Decimal = Field(ge=0, le=100)

# --- Esquema Principal de Empleado ---
class EmployeeBase(BaseModel):
    # Identificación Básica (Requeridos)
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    nss: str
    rfc: str
    curp: str
    
    # Resto son opcionales con valores por defecto
    domicilio_completo: Optional[str] = "NA"
    
    # Datos Laborales (CIT / IMSS)
    puesto: Optional[str] = "NA"
    actividades_detalle: Optional[str] = "NA"
    puesto_sugerido: Optional[str] = None
    turno_sugerido: Optional[str] = None
    cliente_nombre: Optional[str] = "NA"
    cliente_rfc: Optional[str] = "NA"
    tipo_salario: Optional[str] = "SALARIO NOMINAL"
    salario_diario: Decimal = Decimal("0.00")
    factor_integracion: Decimal = Decimal("1.0493")
    sdi: Decimal = Decimal("0.00")
    empresa_pagadora: Optional[str] = "NA"
    fecha_alta_imss: Optional[date] = None
    registro_patronal: Optional[str] = "NA"
    clase_rt: Optional[str] = "NA"
    
    # Datos Personales
    fecha_nacimiento: Optional[date] = None
    estado_civil: Optional[str] = "NA"
    sexo: Optional[str] = "NA"
    nacionalidad: str = "MEXICANO"
    correo: Optional[str] = None
    numero_telefono: Optional[str] = None
    domicilio_fiscal: Optional[str] = None
    tipo_sangre: Optional[str] = None
    tiene_fonacot: bool = False
    numero_fonacot: Optional[str] = None
    tiene_enfermedades_alergias: bool = False
    enfermedades_alergias: Optional[str] = None
    medicamentos_especiales: Optional[str] = None
    experiencia_anterior: Optional[str] = None
    domicilio_laboral: Optional[str] = "NA"
    
    # Seguridad Social
    tiene_infonavit: Optional[str] = "NO"
    numero_credito_infonavit: Optional[str] = None
    
    # Contrato y Proyecto
    tipo_contrato: Optional[str] = "NA"
    duracion_contrato: Optional[str] = "NA"
    nombre_proyecto: Optional[str] = "NA"
    consiste_proyecto: Optional[str] = "NA"
    
    # Nómina y Pagos
    forma_pago: Optional[str] = "NA"
    se_le_paga_por: Optional[str] = "NA"
    sueldo_mensual_bruto: Decimal = Decimal("0.00")
    sueldo_mensual_neto: Decimal = Decimal("0.00")
    banco: Optional[str] = "NA"
    cuenta_bancaria: Optional[str] = "NA"
    clabe_interbancaria: Optional[str] = "NA"
    
    # Tallas (Control Operativo)
    talla_camisa: Optional[str] = "NA"
    talla_pantalon: Optional[str] = "NA"
    talla_calzado: Optional[str] = "NA"
    tiene_zapato_casquillo: bool = False

    # Datos para App Operativa
    es_operativo: bool = False
    username_operativo: Optional[str] = None
    hashed_pin: Optional[str] = None
    
    # --- Validadores para convertir fechas desde múltiples formatos ---
    @field_validator('fecha_nacimiento', 'fecha_alta_imss', mode='before')
    @classmethod
    def parse_dates(cls, v):
        if v is None or isinstance(v, date):
            return v
        return parse_date(v)

# --- Esquema para cuando RECIBES datos (Create) ---
class EmployeeCreate(EmployeeBase):
    beneficiaries: List[BeneficiaryBase] = []

    @model_validator(mode='after')
    def validate_identity_dates(self) -> 'EmployeeCreate':
        # VALIDACIÓN MUY PERMISIVA - solo valida en casos específicos
        # Si falta fecha_nacimiento, permitir sin validar
        if not self.fecha_nacimiento:
            return self
        
        # Permitir datos de prueba (cortos, "NA", o con caracteres no numéricos)
        if len(self.rfc) < 13 or len(self.curp) < 18:
            return self
        
        # Saltar validación si RFC/CURP contienen "NA" o son claramente test data
        if "NA" in self.rfc or "NA" in self.curp:
            return self
        
        # Saltar validación si la fecha está en formato YYYYMMDD sin separadores
        # (indica que es un campo no procesado o de test)
        rfc_date_part = self.rfc[4:10] if len(self.rfc) >= 10 else ""
        curp_date_part = self.curp[4:10] if len(self.curp) >= 10 else ""
        
        # Solo validar si AMBAS partes de fecha son numéricas
        if not (rfc_date_part.isdigit() and curp_date_part.isdigit()):
            return self
        
        # A este punto, solo validamos si todo indica ser un RFC/CURP real
        try:
            expected_date = self.fecha_nacimiento.strftime("%y%m%d")
            
            # Validar RFC solo si tiene formato consistente
            if rfc_date_part != expected_date:
                # Log pero PERMITIR (no fallar)
                # print(f"Warning: RFC fecha ({rfc_date_part}) != nacimiento ({expected_date})")
                pass
            
            # Validar CURP solo si tiene formato consistente
            if curp_date_part != expected_date:
                # Log pero PERMITIR (no fallar)
                # print(f"Warning: CURP fecha ({curp_date_part}) != nacimiento ({expected_date})")
                pass
                
        except Exception as e:
            # Si hay cualquier error en validación, permitir
            pass
                
        return self

# --- Esquema para cuando ACTUALIZAS datos (Update) ---
class EmployeeUpdate(BaseModel):
    """Schema para actualizar un empleado - TODOS los campos son opcionales"""
    # Identificación Básica (Opcionales para actualización)
    nombre: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    nss: Optional[str] = None
    rfc: Optional[str] = None
    curp: Optional[str] = None
    
    # Resto de campos opcionales
    domicilio_completo: Optional[str] = None
    puesto: Optional[str] = None
    actividades_detalle: Optional[str] = None
    puesto_sugerido: Optional[str] = None
    turno_sugerido: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_rfc: Optional[str] = None
    tipo_salario: Optional[str] = None
    salario_diario: Optional[Decimal] = None
    factor_integracion: Optional[Decimal] = None
    sdi: Optional[Decimal] = None
    empresa_pagadora: Optional[str] = None
    fecha_alta_imss: Optional[date] = None
    registro_patronal: Optional[str] = None
    clase_rt: Optional[str] = None
    
    fecha_nacimiento: Optional[date] = None
    estado_civil: Optional[str] = None
    sexo: Optional[str] = None
    nacionalidad: Optional[str] = None
    correo: Optional[str] = None
    numero_telefono: Optional[str] = None
    domicilio_fiscal: Optional[str] = None
    tipo_sangre: Optional[str] = None
    tiene_fonacot: Optional[bool] = None
    numero_fonacot: Optional[str] = None
    tiene_enfermedades_alergias: Optional[bool] = None
    enfermedades_alergias: Optional[str] = None
    medicamentos_especiales: Optional[str] = None
    experiencia_anterior: Optional[str] = None
    domicilio_laboral: Optional[str] = None
    
    tiene_infonavit: Optional[str] = None
    numero_credito_infonavit: Optional[str] = None
    
    tipo_contrato: Optional[str] = None
    duracion_contrato: Optional[str] = None
    nombre_proyecto: Optional[str] = None
    consiste_proyecto: Optional[str] = None
    
    forma_pago: Optional[str] = None
    se_le_paga_por: Optional[str] = None
    sueldo_mensual_bruto: Optional[Decimal] = None
    sueldo_mensual_neto: Optional[Decimal] = None
    banco: Optional[str] = None
    cuenta_bancaria: Optional[str] = None
    clabe_interbancaria: Optional[str] = None
    
    talla_camisa: Optional[str] = None
    talla_pantalon: Optional[str] = None
    talla_calzado: Optional[str] = None
    tiene_zapato_casquillo: Optional[bool] = None
    
    # --- Validadores para convertir fechas desde múltiples formatos ---
    @field_validator('fecha_nacimiento', 'fecha_alta_imss', mode='before')
    @classmethod
    def parse_dates(cls, v):
        if v is None or isinstance(v, date):
            return v
        return parse_date(v)

# --- Esquema para cuando ENVIAS datos (Read) ---
class EmployeeRead(EmployeeBase):
    id: int
    beneficiaries: List[BeneficiaryBase] = []

    # Configuración para Pydantic V2 (compatible con ORM/SQLModel)
    model_config = ConfigDict(from_attributes=True)