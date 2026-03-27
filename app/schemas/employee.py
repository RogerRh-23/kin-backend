from datetime import date, datetime
from typing import Optional, List, Union, Any, Dict
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict
from decimal import Decimal
import json
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

_CP_CACHE: Dict[str, Dict[str, Any]] = {}


# --- Helper: Convertir fechas desde multiples formatos ---
def parse_date(value: Union[str, date]) -> date:
    """Acepta fechas en formato ISO (YYYY-MM-DD) o DD/MM/YYYY"""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return value

    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        pass

    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except Exception:
        pass

    try:
        return datetime.strptime(value, "%d-%m-%Y").date()
    except Exception:
        pass

    raise ValueError(f"Formato de fecha no soportado: {value}. Use YYYY-MM-DD o DD/MM/YYYY")


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned if cleaned else None


def _normalize_cp(value: str) -> str:
    cp = "".join(ch for ch in str(value) if ch.isdigit())
    if len(cp) != 5:
        raise ValueError("El codigo postal debe tener exactamente 5 digitos")
    return cp


def _fetch_cp_from_copomex(cp: str) -> Optional[Dict[str, Any]]:
    url = f"https://api.copomex.com/query/info_cp/{cp}?token=pruebas&type=simplified"
    try:
        with urlopen(url, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    response_data = payload.get("response")
    if not isinstance(response_data, dict):
        return None

    colonias = response_data.get("asentamiento") or []
    if isinstance(colonias, str):
        colonias = [colonias]

    return {
        "estado": _normalize_text(response_data.get("estado")),
        "municipio": _normalize_text(response_data.get("municipio")),
        "colonias": [c for c in (_normalize_text(c) for c in colonias) if c],
    }


def _fetch_cp_from_sepomex(cp: str) -> Optional[Dict[str, Any]]:
    url = f"https://sepomex.icalialabs.com/api/v1/zip_codes?zip_code={cp}"
    try:
        with urlopen(url, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    zip_codes = payload.get("zip_codes") or []
    if not isinstance(zip_codes, list) or not zip_codes:
        return None

    first = zip_codes[0]
    estado = _normalize_text(first.get("d_estado"))
    municipio = _normalize_text(first.get("d_mnpio"))
    colonias = [
        c for c in (_normalize_text(item.get("d_asenta")) for item in zip_codes) if c
    ]

    return {
        "estado": estado,
        "municipio": municipio,
        "colonias": sorted(set(colonias)),
    }


def _resolve_cp_data(cp: str) -> Optional[Dict[str, Any]]:
    if cp in _CP_CACHE:
        return _CP_CACHE[cp]

    cp_data = _fetch_cp_from_copomex(cp) or _fetch_cp_from_sepomex(cp)
    if cp_data:
        _CP_CACHE[cp] = cp_data
    return cp_data


class AddressInput(BaseModel):
    estado: Optional[str] = Field(default=None)
    municipio: Optional[str] = Field(default=None)
    colonia: Optional[str] = Field(default=None)
    calle_numero: str
    codigo_postal: str
    autocompletar_por_cp: bool = True

    @field_validator("codigo_postal", mode="before")
    @classmethod
    def normalize_codigo_postal(cls, v):
        return _normalize_cp(v)


def _format_structured_address(address: AddressInput, field_name: str) -> str:
    cp = _normalize_cp(address.codigo_postal)
    estado = _normalize_text(address.estado)
    municipio = _normalize_text(address.municipio)
    colonia = _normalize_text(address.colonia)
    calle_numero = _normalize_text(address.calle_numero)

    if not calle_numero:
        raise ValueError(f"{field_name}: calle_numero es obligatorio")

    if address.autocompletar_por_cp and (not estado or not municipio or not colonia):
        cp_data = _resolve_cp_data(cp)
        if cp_data:
            estado = estado or cp_data.get("estado")
            municipio = municipio or cp_data.get("municipio")
            colonias = cp_data.get("colonias") or []

            if not colonia and colonias:
                colonia = colonias[0]
            elif colonia and colonias and colonia not in colonias:
                raise ValueError(
                    f"{field_name}: la colonia '{colonia}' no corresponde al codigo postal {cp}"
                )

    if not estado or not municipio or not colonia:
        raise ValueError(
            f"{field_name}: faltan estado/municipio/colonia y no se pudieron autocompletar con el codigo postal {cp}"
        )

    return f"{estado}, {municipio}, {colonia}, {calle_numero}, CP {cp}"


def _from_legacy_address_parts(values: Dict[str, Any], prefix: str) -> Optional[Dict[str, Any]]:
    """Convierte llaves legacy de frontend a estructura AddressInput."""
    estado = _normalize_text(values.get(f"{prefix}_estado"))
    municipio = _normalize_text(values.get(f"{prefix}_ciudad_municipio"))
    colonia = _normalize_text(values.get(f"{prefix}_colonia"))
    calle = _normalize_text(values.get(f"{prefix}_calle"))
    numero = _normalize_text(values.get(f"{prefix}_numero"))
    cp = _normalize_text(values.get(f"{prefix}_cp"))

    if not any([estado, municipio, colonia, calle, numero, cp]):
        return None

    calle_numero = " ".join(p for p in [calle, numero] if p)
    if not calle_numero:
        calle_numero = "SN"

    return {
        "estado": estado,
        "municipio": municipio,
        "colonia": colonia,
        "calle_numero": calle_numero,
        "codigo_postal": cp,
        "autocompletar_por_cp": True,
    }


def _normalize_single_address(
    values: Dict[str, Any],
    target_field: str,
    label: str,
    legacy_prefix: str,
    required: bool,
) -> None:
    raw_value = values.get(target_field)

    # 1) Si viene como objeto (nuevo formato), se normaliza y convierte a string.
    if isinstance(raw_value, dict):
        address = AddressInput(**raw_value)
        values[target_field] = _format_structured_address(address, label)
        return

    # 2) Si viene como string (excel o cliente legado), se acepta tal cual.
    if isinstance(raw_value, str):
        cleaned = raw_value.strip()
        if cleaned:
            values[target_field] = cleaned
            return
        raw_value = None

    # 3) Si no viene en target_field, intentar construir desde llaves legacy.
    legacy_dict = _from_legacy_address_parts(values, legacy_prefix)
    if legacy_dict:
        address = AddressInput(**legacy_dict)
        values[target_field] = _format_structured_address(address, label)
        return

    # 4) Para create, si sigue vacío, dejamos mensaje claro.
    if required:
        raise ValueError(
            f"{label} debe enviarse como string completo o como objeto con: estado, municipio, colonia, calle_numero, codigo_postal"
        )


# --- Esquema para Beneficiarios ---
class BeneficiaryBase(BaseModel):
    nombre_completo: Optional[str] = "NA"
    parentesco: Optional[str] = "NA"
    porcentaje: Decimal = Field(default=Decimal("0"), ge=0, le=100)


# --- Esquema Principal de Empleado ---
class EmployeeBase(BaseModel):
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    nss: str
    rfc: str
    curp: str = "NA"

    domicilio_completo: Optional[str] = "NA"

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

    tiene_infonavit: Optional[str] = "NO"
    numero_credito_infonavit: Optional[str] = None

    tipo_contrato: Optional[str] = "NA"
    duracion_contrato: Optional[str] = "NA"
    nombre_proyecto: Optional[str] = "NA"
    consiste_proyecto: Optional[str] = "NA"

    forma_pago: Optional[str] = "NA"
    se_le_paga_por: Optional[str] = "NA"
    sueldo_mensual_bruto: Decimal = Decimal("0.00")
    sueldo_mensual_neto: Decimal = Decimal("0.00")
    banco: Optional[str] = "NA"
    cuenta_bancaria: Optional[str] = "NA"
    clabe_interbancaria: Optional[str] = "NA"

    talla_camisa: Optional[str] = "NA"
    talla_pantalon: Optional[str] = "NA"
    talla_calzado: Optional[str] = "NA"
    tiene_zapato_casquillo: bool = False

    es_operativo: bool = False
    username_operativo: Optional[str] = None
    hashed_pin: Optional[str] = None

    @field_validator("fecha_nacimiento", "fecha_alta_imss", mode="before")
    @classmethod
    def parse_dates(cls, v):
        if v is None or isinstance(v, date):
            return v
        return parse_date(v)


class EmployeeCreate(EmployeeBase):
    beneficiaries: List[BeneficiaryBase] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_addresses(cls, values):
        if not isinstance(values, dict):
            return values

        _normalize_single_address(
            values,
            target_field="domicilio_completo",
            label="Domicilio personal",
            legacy_prefix="domicilio_personal",
            required=True,
        )
        _normalize_single_address(
            values,
            target_field="domicilio_laboral",
            label="Domicilio laboral",
            legacy_prefix="domicilio_laboral",
            required=True,
        )
        _normalize_single_address(
            values,
            target_field="domicilio_fiscal",
            label="Domicilio fiscal",
            legacy_prefix="domicilio_fiscal",
            required=True,
        )

        return values

    @model_validator(mode="after")
    def validate_identity_dates(self) -> "EmployeeCreate":
        if not self.fecha_nacimiento:
            return self

        if len(self.rfc) < 13 or len(self.curp) < 18:
            return self

        if "NA" in self.rfc or "NA" in self.curp:
            return self

        rfc_date_part = self.rfc[4:10] if len(self.rfc) >= 10 else ""
        curp_date_part = self.curp[4:10] if len(self.curp) >= 10 else ""

        if not (rfc_date_part.isdigit() and curp_date_part.isdigit()):
            return self

        try:
            expected_date = self.fecha_nacimiento.strftime("%y%m%d")
            if rfc_date_part != expected_date:
                pass
            if curp_date_part != expected_date:
                pass
        except Exception:
            pass

        return self


class EmployeeUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    nss: Optional[str] = None
    rfc: Optional[str] = None
    curp: Optional[str] = None

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

    @model_validator(mode="before")
    @classmethod
    def normalize_addresses(cls, values):
        if not isinstance(values, dict):
            return values

        _normalize_single_address(
            values,
            target_field="domicilio_completo",
            label="Domicilio personal",
            legacy_prefix="domicilio_personal",
            required=False,
        )
        _normalize_single_address(
            values,
            target_field="domicilio_laboral",
            label="Domicilio laboral",
            legacy_prefix="domicilio_laboral",
            required=False,
        )
        _normalize_single_address(
            values,
            target_field="domicilio_fiscal",
            label="Domicilio fiscal",
            legacy_prefix="domicilio_fiscal",
            required=False,
        )

        return values

    @field_validator("fecha_nacimiento", "fecha_alta_imss", mode="before")
    @classmethod
    def parse_dates(cls, v):
        if v is None or isinstance(v, date):
            return v
        return parse_date(v)


class EmployeeRead(EmployeeBase):
    id: int
    beneficiaries: List[BeneficiaryBase] = []

    model_config = ConfigDict(from_attributes=True)
