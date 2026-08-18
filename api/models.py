"""
Pydantic models for the FastAPI layer.
Shapes must exactly match 04_API_CONTRACT.md.
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re
from datetime import datetime

# ---- Requests ----

class ResolveMedicineRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)
    source: str = Field(..., pattern="^(ocr|typed)$")


class TrackedMedicineRequest(BaseModel):
    user_id: int
    medicine_id: int
    profile_label: str = Field(..., min_length=1)


class UserRequest(BaseModel):
    phone: str
    consent_whatsapp: bool

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Valid E.164 Indian number: +91 followed by 10 digits
        if not re.match(r"^\+91\d{10}$", v):
            raise ValueError("Must be a valid E.164 Indian number (e.g. +919999000000)")
        return v

    @field_validator("consent_whatsapp")
    @classmethod
    def validate_consent(cls, v: bool, info) -> bool:
        # Pydantic handles bool coercion, but we want to ensure it's not defaulted blindly.
        # It's required in the schema by not providing a default.
        return v


# ---- Responses ----

class CandidateResponse(BaseModel):
    medicine_id: int
    brand_name: str
    confidence: float


class ResolveMedicineResponse(BaseModel):
    matched: bool
    medicine_id: int | None = None
    brand_name: str | None = None
    confidence: float
    needs_confirmation: bool
    candidates: list[CandidateResponse] | None = None
    
    # Hide candidates if None to strictly match contract JSON
    model_config = ConfigDict(exclude_none=True)


class SourceMedicine(BaseModel):
    medicine_id: int
    brand_name: str
    current_price: float | None


class SubstituteItem(BaseModel):
    medicine_id: int
    brand_name: str
    price: float
    is_jan_aushadhi: bool
    savings_rupees: float
    savings_percent: float


class SubstitutesResponse(BaseModel):
    source_medicine: SourceMedicine
    substitutes: list[SubstituteItem]
    caution_flag: str | None = None


class PriceHistoryPoint(BaseModel):
    price: float
    scraped_at: datetime

class TrackedMedicineItem(BaseModel):
    tracked_id: int
    medicine_id: int
    brand_name: str
    profile_label: str
    latest_price: float | None
    savings_to_date: float = 0.0
    history: list[PriceHistoryPoint] = []
