from pydantic import BaseModel
from datetime import date
from typing import Optional

class EmployeeCreate(BaseModel):
    first_name: str
    last_name_father: str
    last_name_mother: Optional[str] = None
    rfc: str
    curp: str
    nss: str
    job_title: str
    start_date: date
    daily_salary: Optional[float] = None
    integrated_daily_salary: Optional[float] = None
    monthly_salary_gross: Optional[float] = None
    gender: str
    marital_status: str
    address: str
    work_location: str
    contract_type: str
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    clabe: Optional[str] = None

class EmployeeOut(EmployeeCreate):
    id: int
    is_active: bool

    class Config:
        from_attributes = True