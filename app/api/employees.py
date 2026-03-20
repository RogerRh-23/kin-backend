import secrets
import json
import pandas as pd
from io import StringIO
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from sqlmodel import Session, select
from sqlalchemy import func
from pydantic import BaseModel
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import json
import logging
from app.core.db import get_session  
from app.models.employee import Employee, Beneficiary
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.models.history import EmploymentHistory
from app.schemas.history import TerminationRequest, HistoryRead
from app.core.security import hash_password, encrypt_pin, decrypt_pin
from app.core.utils import generate_username 
from app.api.auth import require_role

router = APIRouter(prefix="/employees", tags=["Employees"])

_CP_CACHE: Dict[str, Dict[str, Any]] = {}

# ==========================================
#  ESQUEMA DE RESPUESTA ESPECIAL (Solo para creación)
# ==========================================
class EmployeeCreateResponse(BaseModel):
    employee: EmployeeRead # Usamos tu schema Read para que serialice bien
    generated_credentials: dict # Aquí va el PIN visible

# ==========================================
#  FUNCIONES AUXILIARES (Limpieza de Excel)
# ==========================================

def clean_money(val):
    if pd.isna(val) or str(val).strip().upper() in ["NA", "N/A", "", "nan"]:
        return Decimal("0.00")
    clean_str = str(val).replace('$', '').replace(',', '').strip()
    try:
        return Decimal(clean_str)
    except InvalidOperation:
        return Decimal("0.00")

def clean_date(val):
    if pd.isna(val) or str(val).strip().upper() in ["NA", "N/A", "", "nan"]:
        return None
    try:
        return pd.to_datetime(val, dayfirst=True).date()
    except:
        return None

def clean_str(val):
    if pd.isna(val) or str(val).strip().upper() in ["NA", "N/A", "", "nan"]:
        return "NA"
    return str(val).strip()


def normalize_cp(cp: str) -> str:
    digits = "".join(ch for ch in str(cp) if ch.isdigit())
    if len(digits) != 5:
        raise HTTPException(status_code=422, detail="El código postal debe tener 5 dígitos")
    return digits


def fetch_cp_from_copomex(cp: str) -> Optional[Dict[str, Any]]:
    url = f"https://api.copomex.com/query/info_cp/{cp}?token=pruebas&type=simplified"
    print(f"[COPOMEX] Consultando: {url}")
    try:
        with urlopen(url, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
        print(f"[COPOMEX_RESPONSE] {payload}")
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"[COPOMEX_ERROR] {type(e).__name__}: {str(e)}")
        return None

    data = payload.get("response")
    if not isinstance(data, dict):
        print(f"[COPOMEX_ERROR] Response no es dict: {data}")
        return None

    colonias = data.get("asentamiento") or []
    if isinstance(colonias, str):
        colonias = [colonias]

    result = {
        "codigo_postal": cp,
        "estado": (data.get("estado") or "").strip() or None,
        "municipio": (data.get("municipio") or "").strip() or None,
        "colonias": sorted({str(c).strip() for c in colonias if str(c).strip()}),
        "fuente": "copomex"
    }
    print(f"[COPOMEX_RESULT] {result}")
    return result


def fetch_cp_from_sepomex(cp: str) -> Optional[Dict[str, Any]]:
    url = f"https://sepomex.icalialabs.com/api/v1/zip_codes?zip_code={cp}"
    print(f"[SEPOMEX] Consultando: {url}")
    try:
        with urlopen(url, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
        print(f"[SEPOMEX_RESPONSE] {payload}")
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"[SEPOMEX_ERROR] {type(e).__name__}: {str(e)}")
        return None

    zip_codes = payload.get("zip_codes") or []
    if not isinstance(zip_codes, list) or not zip_codes:
        print(f"[SEPOMEX_ERROR] zip_codes vacío o inválido: {zip_codes}")
        return None

    first = zip_codes[0]
    colonias = sorted({
        str(item.get("d_asenta", "")).strip()
        for item in zip_codes
        if str(item.get("d_asenta", "")).strip()
    })

    result = {
        "codigo_postal": cp,
        "estado": str(first.get("d_estado", "")).strip() or None,
        "municipio": str(first.get("d_mnpio", "")).strip() or None,
        "colonias": colonias,
        "fuente": "sepomex"
    }
    print(f"[SEPOMEX_RESULT] {result}")
    return result


def resolve_cp_data(cp: str) -> Optional[Dict[str, Any]]:
    if cp in _CP_CACHE:
        return _CP_CACHE[cp]

    result = fetch_cp_from_copomex(cp) or fetch_cp_from_sepomex(cp)
    if result:
        _CP_CACHE[cp] = result
    return result


# ==========================================
#  NOMBRE COMPLETO (Helper)
# ==========================================
def build_full_name(nombre, apellido_paterno, apellido_materno):
    """Construye `nombre_completo` a partir de partes, limpiando valores "NA" y espacios.
    Devuelve cadena vacía si no hay datos.
    """
    parts = []
    for part in (nombre, apellido_paterno, apellido_materno):
        if part is None:
            continue
        p = str(part).strip()
        if not p or p.upper() in ("NA", "N/A"):
            continue
        parts.append(p)
    full = " ".join(parts).strip()
    return full if full else ""

# ==========================================
#  ENDPOINTS DE LA API
# ==========================================

# 1. LISTAR TODOS LOS EMPLEADOS (GET)
@router.get("/", response_model=List[EmployeeRead])
def get_employees(session: Session = Depends(get_session)):
    employees = session.exec(select(Employee)).all()
    return employees


# 1.1 AUTOCOMPLETAR DIRECCIÓN POR CÓDIGO POSTAL (GET)
@router.get("/postal-code/{cp}")
def get_postal_code_data(cp: str):
    """
    Retorna estado, municipio y colonias sugeridas para autocompletar domicilios.
    Frontend envía SOLO el CP, backend devuelve los datos para autocompletar.
    """
    print(f"\n[POSTAL_CODE_REQUEST] CP recibido: {cp}")
    
    try:
        normalized_cp = normalize_cp(cp)
        print(f"[POSTAL_CODE] CP normalizado: {normalized_cp}")
    except HTTPException as e:
        print(f"[POSTAL_CODE_ERROR] Error al normalizar CP: {e.detail}")
        raise
    
    cp_data = resolve_cp_data(normalized_cp)
    
    if not cp_data:
        print(f"[POSTAL_CODE_ERROR] No se encontró información para CP: {normalized_cp}")
        raise HTTPException(status_code=404, detail="No se encontró información para ese código postal")
    
    print(f"[POSTAL_CODE_SUCCESS] Datos retornados: {cp_data}")
    return cp_data

# --- ENDPOINT: WIDGET DE ALERTA (GET) ---
@router.get("/missing-credentials-count")
def count_missing_credentials(session: Session = Depends(get_session)):
    """
    Retorna la cantidad de empleados operativos sin credenciales.
    Uso: Widget de notificaciones en el Dashboard.
    """
    # Cuenta filas donde es_operativo es True Y hashed_pin es NULL
    statement = select(func.count()).where(
        Employee.es_operativo == True,
        Employee.hashed_pin == None
    )
    count = session.exec(statement).one()
    
    return {
        "faltantes": count, 
        "alerta": count > 0,
        "mensaje": f"Hay {count} empleados sin credenciales de App."
    }

# 2. OBTENER UN EMPLEADO POR ID (GET)
@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(employee_id: int, session: Session = Depends(get_session)):
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return employee

# 2.5 ACTUALIZAR UN EMPLEADO (PUT)
@router.put("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int, 
    payload: EmployeeUpdate, 
    session: Session = Depends(get_session)
):
    """
    Actualiza la información de un empleado existente.
    Solo actualiza los campos que se envíen (los otros mantienen su valor).
    """
    # Obtener el empleado
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    # Validar que no se intente cambiar a NSS/RFC/CURP ya existentes
    update_data = payload.model_dump(exclude_unset=True)
    
    if "nss" in update_data or "rfc" in update_data or "curp" in update_data:
        # Verificar duplicados (excluyendo el empleado actual)
        filters = []
        if "nss" in update_data:
            filters.append((Employee.nss == update_data["nss"]) & (Employee.id != employee_id))
        if "rfc" in update_data:
            filters.append((Employee.rfc == update_data["rfc"]) & (Employee.id != employee_id))
        if "curp" in update_data:
            filters.append((Employee.curp == update_data["curp"]) & (Employee.id != employee_id))
        
        if filters:
            # Combine filters with OR
            from sqlalchemy import or_
            existing = session.exec(select(Employee).where(or_(*filters))).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="El NSS, RFC o CURP ya existen en otro empleado."
                )
    
    # Actualizar solo los campos proporcionados
    for field, value in update_data.items():
        if value is not None:
            setattr(employee, field, value)
    
    # Guardar cambios
    try:
        session.add(employee)
        session.commit()
        session.refresh(employee)
        return employee
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar: {str(e)}")

# 4. CREAR EMPLEADO MANUAL (POST) - *** MODIFICADO CON GENERACIÓN DE CREDENCIALES ***
@router.post("/", response_model=EmployeeCreateResponse, status_code=status.HTTP_201_CREATED)
def create_employee(body: dict = Body(...), session: Session = Depends(get_session)):
    """
    Crea un nuevo empleado. Acepta datos en dos formatos:
    1. Directo: { "nombre": "...", "nss": "...", ... }
    2. Envuelto: { "datos": { "nombre": "...", "nss": "...", ... } }
    """
    
    # Extraer datos - permitir ambos formatos
    if "datos" in body and isinstance(body["datos"], dict):
        # Formato envuelto del frontend
        employee_data = body["datos"]
    else:
        # Formato directo
        employee_data = body
    
    # Asegurar que beneficiaries está presente
    if "beneficiaries" not in employee_data:
        employee_data["beneficiaries"] = []
    
    # Convertir a EmployeeCreate para validación
    try:
        payload = EmployeeCreate(**employee_data)
    except Exception as e:
        import traceback
        error_detail = str(e)
        if hasattr(e, 'errors'):
            # Pydantic ValidationError - extraer detalles
            error_detail = str(e.errors())
        print(f"[VALIDATION_ERROR] {error_detail}")
        print(f"[TRACEBACK] {traceback.format_exc()}")
        raise HTTPException(
            status_code=422, 
            detail=f"Error de validación: {error_detail[:500]}"
        )
    
    # A) Validar Duplicados (Tu lógica original)
    existing = session.exec(
        select(Employee).where(
            (Employee.nss == payload.nss) | 
            (Employee.rfc == payload.rfc) | 
            (Employee.curp == payload.curp)
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="El NSS, RFC o CURP ya existen en la base de datos."
        )

    # B) Separar Beneficiarios (Tu lógica original)
    employee_dict = payload.model_dump(exclude={"beneficiaries"})

    # --- MODIFICACIÓN: Forzamos que sea operativo ---
    employee_dict["es_operativo"] = True
    
    db_employee = Employee(**employee_dict)
    
    # C) Vincular Beneficiarios (Tu lógica original)
    if payload.beneficiaries:
        for b_data in payload.beneficiaries:
            db_beneficiary = Beneficiary(**b_data.model_dump())
            db_employee.beneficiaries.append(db_beneficiary)

    # D) Guardar y Generar Credenciales
    try:
        # 1. Guardamos primero (flush) para que la DB le asigne un ID
        # Necesitamos el ID para crear el usuario (Ej: JUAN-5)
        
        session.add(db_employee)
        session.flush() 
        session.refresh(db_employee) # Obtenemos el ID recién creado

        # 2. GENERACIÓN AUTOMÁTICA DE CREDENCIALES
        # Construir nombre completo a partir de partes individuales
        full_name = build_full_name(db_employee.nombre, db_employee.apellido_paterno, db_employee.apellido_materno)
        username = generate_username(full_name, db_employee.id)
        plain_pin = "".join([str(secrets.randbelow(10)) for _ in range(4)]) # PIN "1234"

        # 3. Actualizamos el objeto con las credenciales: hashed + encrypted
        db_employee.username_operativo = username
        db_employee.hashed_pin = hash_password(plain_pin)
        db_employee.encrypted_pin = encrypt_pin(plain_pin)

        # 4. Commit final
        session.add(db_employee)
        session.commit()
        session.refresh(db_employee)

        # 5. Retornamos la estructura especial con el PIN visible
        return {
            "employee": db_employee,
            "generated_credentials": {
                "username": username,
                "pin_inicial": plain_pin, # SE MUESTRA SOLO AQUÍ
                "mensaje": "Atencion! Entrega este PIN al empleado. No se podra ver despues."
            }
        }

    except Exception as e:
        session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR_DETALLE] {str(e)}")
        print(f"[TRACEBACK]\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Error al guardar: {str(e)[:200]}")


# 5. CARGA MASIVA DESDE CSV/EXCEL (POST) - (INTACTO)
@router.post("/upload-csv/")
async def upload_employees_csv(
    file: UploadFile = File(...), 
    session: Session = Depends(get_session)
):
    # Validar extensión
    if not file.filename.endswith(('.csv', '.txt')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV.")

    content = await file.read()
    s_content = content.decode('utf-8')

    # A) Detección Inteligente de Cabeceras
    try:
        temp_df = pd.read_csv(StringIO(s_content), header=None, nrows=15)
        header_row_index = 0
        found_header = False
        
        for i, row in temp_df.iterrows():
            row_str = row.to_string().upper()
            if "NSS" in row_str and "R.F.C." in row_str:
                header_row_index = i
                found_header = True
                break
        
        if not found_header:
            header_row_index = 0

        df = pd.read_csv(StringIO(s_content), skiprows=header_row_index)
        df.columns = df.columns.str.strip().str.upper()

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el formato del archivo: {str(e)}")

    created_count = 0
    errors = []

    # B) Iterar filas
    for index, row in df.iterrows():
        real_line = index + header_row_index + 2
        
        try:
            employee_dict = {
                # Identidad
                "nombre": clean_str(row.get("NOMBRE (S)")),
                "apellido_paterno": clean_str(row.get("APELLIDO PATERNO")),
                "apellido_materno": clean_str(row.get("APELLIDO MATERNO")),
                "nombre_completo": build_full_name(
                    clean_str(row.get("NOMBRE (S)")),
                    clean_str(row.get("APELLIDO PATERNO")),
                    clean_str(row.get("APELLIDO MATERNO")),
                ),
                "nss": clean_str(row.get("NSS")),
                "rfc": clean_str(row.get("R.F.C.")),
                "curp": clean_str(row.get("CURP")),
                "domicilio_completo": clean_str(row.get("DOMICILIO COMPLETO (CALLE, NUM EXT E INT, COLONIA, ALCALDIA O MUNICIPIO, ESTADO, C.P.)")),
                
                # Laboral
                "puesto": clean_str(row.get("PUESTO O CATEGORIA")),
                "actividades_detalle": clean_str(row.get("ACTIVIDADES QUE REALIZARA EL TRABAJADOR")),
                "cliente_nombre": clean_str(row.get("NOMBRE DE LA EMPRESA DEL CLIENTE")),
                "cliente_rfc": clean_str(row.get("RFC DE LA EMPRESA DEL CLIENTE")),
                
                # Finanzas
                "tipo_salario": clean_str(row.get("TIPO DE SALARIO")),
                "salario_diario": clean_money(row.get("S.D. (PARA EFECTOS DE CIT)")),
                "factor_integracion": clean_money(row.get("FACTOR INTEGRACION")),
                "sdi": clean_money(row.get("S.D. I. (PARA EFECTOS DE IMSS)")),
                "empresa_pagadora": clean_str(row.get("EMPRESA PAGADORA")),
                
                # IMSS
                "fecha_alta_imss": clean_date(row.get("FECHA CON LA QUE ESTA DADO DE ALTA ANTE EL IMSS")),
                "tiene_infonavit": clean_str(row.get("CREDITO INFONAVIT")),
                "numero_credito_infonavit": clean_str(row.get("NÚMERO")),
                "registro_patronal": clean_str(row.get("REGISTRO PATRONAL")),
                "clase_rt": clean_str(row.get("CLASE R.T.")),
                
                # Personales
                "fecha_nacimiento": clean_date(row.get("FECHA NACIMIENTO")),
                "estado_civil": clean_str(row.get("ESTADO CIVIL (SOLTERO O CASADO)")),
                "sexo": clean_str(row.get("SEXO (HOMBRE O MUJER)")),
                "nacionalidad": clean_str(row.get("NACIONALIDAD")),
                
                # Contrato
                "domicilio_laboral": clean_str(row.get("DOMICILIO DONDE LABORA")),
                "tipo_contrato": clean_str(row.get("TIPO DE CONTRATO (DETERMINADO, OBRA DETERMINADA, INDETERMINADO O PERIODO DE PRUEBA)")),
                "duracion_contrato": clean_str(row.get("TIEMPO DE DURACION (SI ES DETERMINADO), NOMBRE DE PROYECTO SI ES POR OBRA.")),
                "consiste_proyecto": clean_str(row.get("EN QUE CONSISTE EL PROYECTO (OBRA DETERMINADA)")),
                
                # Pagos
                "forma_pago": clean_str(row.get("FORMA DE PAGO (QUINCENAL O SEMANAL ASÍ COMO LOS DIAS EN LOS QUE SE CUBRIRÁN LOS SALARIOS VENCIDOS)")),
                "se_le_paga_por": clean_str(row.get("SE LE PAGA POR")),
                "sueldo_mensual_bruto": clean_money(row.get("SUELDO MENSUAL BRUTO")),
                "sueldo_mensual_neto": clean_money(row.get("SUELDO MENSUAL NETO")),
                
                # Banco y Tallas
                "banco": clean_str(row.get("BANCO")),
                "cuenta_bancaria": clean_str(row.get("CUENTA")),
                "clabe_interbancaria": clean_str(row.get("CLABE")),
                "talla_camisa": clean_str(row.get("TALLA CAMISA")),
                "talla_pantalon": clean_str(row.get("TALLA PANTALON")),
                "talla_calzado": clean_str(row.get("TALLA CALZADO")),
                
                # --- NUEVO: Credenciales para carga masiva ---
                # NOTA: En carga masiva NO generamos PIN automáticamente para no alentar el proceso
                # Se pueden generar después o asumir que la carga masiva no activa app móvil inmediatamente
                "es_operativo": True 
            }

            if employee_dict["nss"] == "NA" or not employee_dict["nss"]:
                 continue

            new_emp = Employee(**employee_dict)
            
            # NOTA: Aquí podríamos generar usuario/pin también, pero 
            # haría la carga masiva más lenta. Sugerencia: Dejarlo así y 
            # generar credenciales bajo demanda o en un segundo paso.
            
            session.add(new_emp)
            session.flush() 
            created_count += 1

        except Exception as e:
            session.rollback()
            errors.append(f"Fila {real_line}: {str(e)}")
            continue

    session.commit()

    return {
        "mensaje": "Proceso de carga finalizado",
        "empleados_creados": created_count,
        "errores": errors
    }

# --- ENDPOINT: DAR DE BAJA (INTACTO) ---
@router.post("/{employee_id}/terminate", response_model=dict)
def terminate_employee(
    employee_id: int, 
    payload: TerminationRequest, 
    session: Session = Depends(get_session)
):
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
        
    if not employee.is_active:
        raise HTTPException(status_code=400, detail="El empleado ya está dado de baja")

    history_record = EmploymentHistory(
        employee_id=employee.id,
        tipo_movimiento="BAJA",
        motivo=payload.motivo,
        comentarios=payload.comentarios,
        recontratable=payload.recontratable,
        fecha_movimiento=date.today()
    )
    
    employee.is_active = False
    
    try:
        session.add(history_record)
        session.add(employee)
        session.commit()
        return {
            "mensaje": "Baja procesada exitosamente", 
            "status_final": "INACTIVO",
            "semáforo": "VERDE" if payload.recontratable else "ROJO"
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar la baja: {str(e)}")

# --- ENDPOINT: CONSULTAR HISTORIAL (INTACTO) ---
@router.get("/{employee_id}/history", response_model=List[HistoryRead])
def get_employee_history(employee_id: int, session: Session = Depends(get_session)):
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    statement = select(EmploymentHistory).where(
        EmploymentHistory.employee_id == employee_id
    ).order_by(EmploymentHistory.fecha_movimiento.desc())
    
    history = session.exec(statement).all()
    return history

# --- ENDPOINT: RECONTRATAR (INTACTO) ---
@router.post("/{employee_id}/rehire") 
def rehire_employee(
    employee_id: int, 
    payload: dict = Body(default=None), 
    session: Session = Depends(get_session)
):
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    if employee.is_active:
        raise HTTPException(status_code=400, detail="El empleado ya está activo, no se puede recontratar.")
    
    employee.is_active = True
    employee.fecha_baja = None 
    
    comentarios_historial = ""
    if payload:
        comentarios_historial = payload.get("comentarios", "")
        for key, value in payload.items():
            if key not in ["id", "comentarios"] and hasattr(employee, key):
                setattr(employee, key, value)
    
    history_record = EmploymentHistory(
        employee_id=employee_id,
        tipo_movimiento="RECONTRATACION", 
        motivo="Recontratación",
        comentarios=comentarios_historial,
        recontratable=True, 
        fecha_movimiento=date.today()
    )
    
    try:
        session.add(history_record)
        session.add(employee)
        session.commit()
        session.refresh(employee)
        
        return {
            "mensaje": "Empleado recontratado exitosamente", 
            "id": employee.id,
            "estatus": "ACTIVO"
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al recontratar: {str(e)}")
    
# --- ENDPOINT: GENERAR CREDENCIALES MASIVAS (POST-CSV) ---
@router.post("/generate-missing-credentials")
def generate_missing_credentials(session: Session = Depends(get_session)):
    """
    Busca empleados operativos SIN credenciales (hashed_pin es Null).
    Genera usuario y PIN, y devuelve la lista visible.
    """
    
    # 1. Buscar empleados 'huérfanos' de credenciales
    statement = select(Employee).where(
        Employee.es_operativo == True,
        Employee.hashed_pin == None
    )
    employees = session.exec(statement).all()
    
    if not employees:
        return {"mensaje": "Todos los empleados operativos ya tienen credenciales. Nada que hacer."}
    
    generated_report = []
    errores = [] 
    
    for emp in employees:
        try:
            # 2. Determinar nombre para generar credenciales: usar nombre_completo si existe,
            #    si no, construirlo a partir de partes (nombre/apellido_paterno/apellido_materno),
            #    y si sigue vacío, usar "EMP-<id>" como fallback.
            nombre_base = getattr(emp, "nombre_completo", None)
            if not nombre_base:
                nombre_base = build_full_name(
                    getattr(emp, "nombre", None),
                    getattr(emp, "apellido_paterno", None),
                    getattr(emp, "apellido_materno", None),
                )
            if not nombre_base:
                nombre_base = f"EMP-{emp.id}"
            
            # 3. Generar Credenciales
            username = generate_username(nombre_base, emp.id)
            plain_pin = "".join([str(secrets.randbelow(10)) for _ in range(4)]) # PIN 4 dígitos
            
            # 4. Guardar en BD (Encriptado)
            emp.username_operativo = username
            emp.hashed_pin = hash_password(plain_pin)
            emp.encrypted_pin = encrypt_pin(plain_pin)
            session.add(emp)
            
            # 5. Guardar en el reporte de salida (Visible)
            generated_report.append({
                "id": emp.id,
                "nombre": nombre_base,
                "usuario_app": username,
                "pin_inicial": plain_pin # <--- Única vez que se ve
            })
            
        except Exception as e:
            # Si falla uno (ej. nombre con caracteres raros), lo registramos y seguimos
            print(f"Error con empleado ID {emp.id}: {str(e)}")
            errores.append(f"ID {emp.id}: {str(e)}")
            continue
    
    # 6. Guardar cambios masivos
    session.commit()
    
    # 7. Retornar la lista
    return {
        "mensaje": f"Se generaron credenciales para {len(generated_report)} empleados.",
        "advertencia": f"Hubo {len(errores)} errores." if errores else None,
        "credenciales": generated_report,
        "errores_detalle": errores
    }

# --- ENDPOINT: GENERAR/RESETEAR CREDENCIALES INDIVIDUALES ---
@router.post("/{employee_id}/reset-credentials")
def reset_employee_credentials(
    employee_id: int, 
    session: Session = Depends(get_session)
):
    """
    Genera un nuevo PIN para un empleado específico.
    Sirve tanto para la primera vez (Generar) como para olvidos (Resetear).
    """
    # 1. Buscar empleado
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
        
    # 2. Asegurar que tenga usuario (Si no tiene, se lo creamos)
    if not employee.username_operativo:
        nombre_for_username = getattr(employee, "nombre_completo", None)
        if not nombre_for_username:
            nombre_for_username = build_full_name(
                getattr(employee, "nombre", None),
                getattr(employee, "apellido_paterno", None),
                getattr(employee, "apellido_materno", None),
            )
        if not nombre_for_username:
            nombre_for_username = f"EMP-{employee.id}"
        employee.username_operativo = generate_username(nombre_for_username, employee.id)
    
    # 3. Generar NUEVO PIN
    plain_pin = "".join([str(secrets.randbelow(10)) for _ in range(4)])
    
    # 4. Guardar hash + encriptado
    employee.hashed_pin = hash_password(plain_pin)
    employee.encrypted_pin = encrypt_pin(plain_pin)
    employee.es_operativo = True # Aseguramos que quede activo para app
    
    session.add(employee)
    session.commit()
    session.refresh(employee)
    
    # 5. Retornar las credenciales (¡Única vez que se verán!)
    nombre_display = getattr(employee, "nombre_completo", None)
    if not nombre_display:
        nombre_display = build_full_name(
            getattr(employee, "nombre", None),
            getattr(employee, "apellido_paterno", None),
            getattr(employee, "apellido_materno", None),
        )
    if not nombre_display:
        nombre_display = f"EMP-{employee.id}"

    return {
        "mensaje": "Credenciales actualizadas correctamente",
        "credenciales": {
            "id": employee.id,
            "nombre": nombre_display,
            "usuario_app": employee.username_operativo,
            "nuevo_pin": plain_pin
        }
    }


# --- ENDPOINT: REVELAR PIN (SOLO ADMIN) ---
@router.get("/{employee_id}/reveal-pin", response_model=dict)
def reveal_pin(employee_id: int, session: Session = Depends(get_session), _admin = Depends(require_role("admin"))):
    """Revela el PIN original para un empleado (solo admins). Registra acceso en logs."""
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    encrypted = getattr(employee, "encrypted_pin", None)
    if not encrypted:
        raise HTTPException(status_code=404, detail="No hay PIN registrado para este empleado")

    try:
        plain = decrypt_pin(encrypted)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo desencriptar el PIN: {str(e)}")

    # Auditoría mínima: imprimir en logs (se recomienda almacenar en tabla de auditoría)
    print(f"AUDIT: PIN revelado para empleado {employee_id} por admin")

    nombre_display = build_full_name(employee.nombre, employee.apellido_paterno, employee.apellido_materno) or f"EMP-{employee.id}"
    return {"id": employee.id, "nombre": nombre_display, "pin": plain}