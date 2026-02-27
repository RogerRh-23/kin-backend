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
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    nss: str = Field(index=True, unique=True)
    rfc: str = Field(unique=True)
    curp: str = Field(unique=True)
    domicilio_completo: str # Incluye Calle, Num, Col, Alcaldía, CP
    
    # --- BLOQUE 2: PUESTO Y ACTIVIDADES (Columnas I-J) ---
    puesto: str
    actividades_detalle: str # "Inspeccionar material para corroborar..."
    puesto_sugerido: Optional[str] = None
    turno_sugerido: Optional[str] = None
    
    # --- BLOQUE 3: CLIENTE Y PAGADORA (Columnas K-Q) ---
    cliente_nombre: str       # Ej: ASPEL MOLDING
    cliente_rfc: str          # Ej: AMM040126UI1
    tipo_salario: str         # Ej: SALARIO NOMINAL
    salario_diario: Decimal = Field(max_digits=10, decimal_places=2) # S.D. CIT
    factor_integracion: Decimal = Field(default=1.0493, max_digits=6, decimal_places=4)
    sdi: Decimal = Field(max_digits=10, decimal_places=2) # S.D.I. IMSS
    empresa_pagadora: str     # Ej: LACS A.C.
    
    # --- BLOQUE 4: SEGURIDAD SOCIAL Y RT (Columnas R-V) ---
    fecha_alta_imss: Optional[date] = None
    tiene_infonavit: str = "NO"      # "SI" o "NO"
    numero_credito_infonavit: Optional[str] = None
    registro_patronal: str = "NA"    # Ej: Y-5451-0271-05
    clase_rt: str = "NA"             # Ej: III
    
    # --- BLOQUE 5: DATOS PERSONALES (Columnas W-Z) ---
    fecha_nacimiento: Optional[date] = None
    estado_civil: str = "NA"         # SOLTERO / CASADO
    sexo: str = "NA"                 # HOMBRE / MUJER
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
    
    # --- BLOQUE 6: CONTRATO Y LOGÍSTICA (Columnas AA-AE) ---
    domicilio_laboral: str = "NA"
    tipo_contrato: str = "NA"        # DETERMINADO, INDETERMINADO, PRUEBA
    duracion_contrato: str = "NA"    # Ej: 6 MESES
    nombre_proyecto: Optional[str] = None
    consiste_proyecto: Optional[str] = None
    
    # --- BLOQUE 7: PAGOS Y BANCO (Columnas AF-AJ) ---
    forma_pago: str = "NA"           # SEMANAL / QUINCENAL
    se_le_paga_por: str = "NA"       # Ej: SERVICIOS DE CALIDAD
    sueldo_mensual_bruto: Decimal = Field(max_digits=10, decimal_places=2)
    sueldo_mensual_neto: Decimal = Field(max_digits=10, decimal_places=2)
    banco: Optional[str] = None
    cuenta_bancaria: Optional[str] = None
    clabe_interbancaria: Optional[str] = None
    
    # --- BLOQUE 8: EQUIPO Y TALLAS (Para Control Operativo) ---
    talla_camisa: Optional[str] = None
    talla_pantalon: Optional[str] = None
    talla_calzado: Optional[str] = None
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