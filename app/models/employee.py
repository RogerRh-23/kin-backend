from datetime import date
from typing import Optional, List
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship
from pydantic import computed_field, model_validator

# --- TABLA DE BENEFICIARIOS ---
class Beneficiary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_completo: str
    parentesco: str 
    porcentaje: Decimal = Field(max_digits=5, decimal_places=2) # Ejemplo: 33.33
    
    # Llave foránea que conecta con el empleado
    employee_id: Optional[int] = Field(default=None, foreign_key="employee.id")
    
    # Relación inversa
    employee: Optional["Employee"] = Relationship(back_populates="beneficiaries")

# --- TABLA DE EMPLEADOS ---
class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # --- BLOQUE 1: IDENTIFICACIÓN (Columnas A-G) ---
    nombre: Optional[str] = Field(default=None)  # Ahora permite None
    apellido_paterno: Optional[str] = Field(default=None)  # Ahora permite None
    apellido_materno: Optional[str] = Field(default=None)  # Ahora permite None
    nss: str = Field(index=True, unique=True)
    rfc: Optional[str] = Field(default=None, unique=True)  # Ahora permite None
    curp: Optional[str] = Field(default=None, unique=True)  # Nullable para datos incompletos
    
    # --- DOMICILIO COMPLETO (Dirección personal - Desglosada) ---
    domicilio_calle: Optional[str] = Field(default=None)  # Ej: "Calle Principal 123"
    domicilio_numero: Optional[str] = Field(default=None)  # Ej: "123"
    domicilio_estado: Optional[str] = Field(default=None)  # Ej: "Jalisco"
    domicilio_municipio: Optional[str] = Field(default=None)  # Ej: "Guadalajara"
    domicilio_colonia: Optional[str] = Field(default=None)  # Ej: "Centro"
    domicilio_codigo_postal: Optional[str] = Field(default=None)  # Ej: "44100"
    domicilio_completo: Optional[str] = Field(default=None) # Campo generado automáticamente
    
    # --- BLOQUE 2: PUESTO Y ACTIVIDADES (Columnas I-J) ---
    puesto: Optional[str] = Field(default=None)
    actividades_detalle: Optional[str] = Field(default=None)
    puesto_sugerido: Optional[str] = None
    turno_sugerido: Optional[str] = None
    
    # --- BLOQUE 3: CLIENTE Y PAGADORA (Columnas K-Q) ---
    cliente_nombre: Optional[str] = Field(default=None)
    cliente_rfc: Optional[str] = Field(default=None)
    tipo_salario: str = "SALARIO NOMINAL"         # Ej: SALARIO NOMINAL
    salario_diario: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2) # S.D. CIT
    factor_integracion: Decimal = Field(default=Decimal("1.0493"), max_digits=6, decimal_places=4)
    sdi: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2) # S.D.I. IMSS
    empresa_pagadora: Optional[str] = Field(default=None)
    
    # --- BLOQUE 4: SEGURIDAD SOCIAL Y RT (Columnas R-V) ---
    fecha_alta_imss: Optional[date] = None
    tiene_infonavit: str = "NO"      # "SI" o "NO"
    numero_credito_infonavit: Optional[str] = None
    registro_patronal: Optional[str] = Field(default=None)
    clase_rt: Optional[str] = Field(default=None)
    
    # --- BLOQUE 5: DATOS PERSONALES (Columnas W-Z) ---
    fecha_nacimiento: Optional[date] = None
    estado_civil: Optional[str] = Field(default=None)
    sexo: Optional[str] = Field(default=None)
    nacionalidad: str = "MEXICANO"
    correo: Optional[str] = None
    numero_telefono: Optional[str] = None
    # --- DOMICILIO FISCAL (Dirección fiscal - Desglosada) ---
    domicilio_fiscal_calle: Optional[str] = Field(default=None)
    domicilio_fiscal_numero: Optional[str] = Field(default=None)
    domicilio_fiscal_estado: Optional[str] = Field(default=None)
    domicilio_fiscal_municipio: Optional[str] = Field(default=None)
    domicilio_fiscal_colonia: Optional[str] = Field(default=None)
    domicilio_fiscal_codigo_postal: Optional[str] = Field(default=None)
    domicilio_fiscal: Optional[str] = None  # Campo generado automáticamente
    tipo_sangre: Optional[str] = None
    tiene_fonacot: bool = False
    numero_fonacot: Optional[str] = None
    tiene_enfermedades_alergias: bool = False
    enfermedades_alergias: Optional[str] = None
    medicamentos_especiales: Optional[str] = None
    experiencia_anterior: Optional[str] = None
    
    # --- DOMICILIO LABORAL (Dirección de trabajo - Desglosada) ---
    domicilio_laboral_calle: Optional[str] = Field(default=None)
    domicilio_laboral_numero: Optional[str] = Field(default=None)
    domicilio_laboral_estado: Optional[str] = Field(default=None)
    domicilio_laboral_municipio: Optional[str] = Field(default=None)
    domicilio_laboral_colonia: Optional[str] = Field(default=None)
    domicilio_laboral_codigo_postal: Optional[str] = Field(default=None)
    domicilio_laboral: Optional[str] = Field(default=None)  # Campo generado automáticamente
    tipo_contrato: Optional[str] = Field(default=None)
    duracion_contrato: Optional[str] = Field(default=None)
    nombre_proyecto: Optional[str] = None
    consiste_proyecto: Optional[str] = None
    
    # --- BLOQUE 7: PAGOS Y BANCO (Columnas AF-AJ) ---
    forma_pago: Optional[str] = Field(default=None)
    se_le_paga_por: Optional[str] = Field(default=None)
    sueldo_mensual_bruto: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    sueldo_mensual_neto: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    banco: Optional[str] = Field(default=None)
    cuenta_bancaria: Optional[str] = Field(default=None)
    clabe_interbancaria: Optional[str] = Field(default=None)
    
    # --- BLOQUE 8: EQUIPO Y TALLAS (Para Control Operativo) ---
    talla_camisa: Optional[str] = Field(default=None)
    talla_pantalon: Optional[str] = Field(default=None)
    talla_calzado: Optional[str] = Field(default=None)
    tiene_zapato_casquillo: bool = False
    
    # --- RELACIONES ---
    beneficiaries: List["Beneficiary"] = Relationship(back_populates="employee")

    # --- CAMPOS AUTOMÁTICOS ---
    @computed_field
    @property
    def edad(self) -> int:
        today = date.today()
        return today.year - self.fecha_nacimiento.year - (
            (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )
    
    is_active: bool = Field(default=True) 
    fecha_baja: Optional[date] = None # Para saber cuándo dejó de estar activo
    history: List["EmploymentHistory"] = Relationship(back_populates="employee")

    # --- CREDENCIALES OPERATIVAS (APP) ---
    # El usuario lo generaremos nosotros (Ej: RHERNANDEZ)
    username_operativo: Optional[str] = Field(default=None, index=True, unique=True)
    
    # El PIN se guarda hasheado (como password) para que nadie con acceso a la BD pueda robarlos
    hashed_pin: Optional[str] = Field(default=None) 
    # Además almacenamos el PIN cifrado (reversible) para revelar cuando sea necesario
    encrypted_pin: Optional[str] = Field(default=None)
    
    # Campo auxiliar para saber si es un Operador con acceso a App
    es_operativo: bool = Field(default=False)