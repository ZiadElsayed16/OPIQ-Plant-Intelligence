"""
OPIQ Industrial Stoppage Data Models.
Built with Pydantic for strict schema enforcement, data sanitization, and deduplication.
"""
from datetime import datetime, timedelta
import hashlib
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# Standard Machine and Plant Aliases
MACHINE_ALIASES = {
    "cement mill a": "W.CEMENT MILL (A)",
    "w.cement mill (a)": "W.CEMENT MILL (A)",
    "cement mill (a)": "W.CEMENT MILL (A)",
    "mill a": "W.CEMENT MILL (A)",
    "cement mill b": "W.CEMENT MILL (B)",
    "w.cement mill (b)": "W.CEMENT MILL (B)",
    "cement mill (b)": "W.CEMENT MILL (B)",
    "mill b": "W.CEMENT MILL (B)",
    "raw mill": "Raw mill",
    "kiln": "Kiln",
    "sand mill": "Sand mill",
    "coal mill": "Coal mill",
    "crusher": "Crusher",
}

VALID_CLASSES = {"Incidents", "Circumstance", "Schedule"}
VALID_TYPES = {"Mechanical", "Electrical", "Production", "Circumstance", "Schedule"}


class StoppageRecord(BaseModel):
    """Clean, validated, standardized stoppage record ready for DB persistence."""
    plant: str = Field(..., description="Plant name, e.g. Cleopatra Plant or BMIC Plant")
    machine: str = Field(..., description="Standardized equipment/machine name")
    start_time: datetime = Field(..., description="Start timestamp of the stop")
    end_time: datetime = Field(..., description="End timestamp of the stop")
    duration_hours: float = Field(..., gt=0.0, description="Downtime duration in hours, strictly > 0")
    stop_class: str = Field(..., description="High-level category: Incidents, Circumstance, or Schedule")
    stop_type: str = Field(..., description="Detailed type: Mechanical, Electrical, Production, Circumstance, Schedule")
    reason: str = Field(..., description="Root cause or event description")
    affects_kpi: bool = Field(default=True, description="True if stops impact operational reliability KPIs (Incidents & Circumstance)")
    record_hash: str = Field(default="", description="Unique cryptographic hash for duplicate detection")

    @field_validator("plant")
    @classmethod
    def clean_plant(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Plant name cannot be empty")
        # Standardize common plant labels
        s_low = s.lower()
        if "cleopatra" in s_low:
            return "Cleopatra Plant"
        elif "bmic" in s_low:
            return "BMIC Plant"
        return s

    @field_validator("machine")
    @classmethod
    def clean_machine(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Machine name cannot be empty")
        # Look up standard alias
        s_low = s.lower()
        if s_low in MACHINE_ALIASES:
            return MACHINE_ALIASES[s_low]
        # Capitalize nicely if not in alias
        return s

    @field_validator("stop_class")
    @classmethod
    def clean_class(cls, v: str) -> str:
        s = v.strip().capitalize()
        for vc in VALID_CLASSES:
            if vc.lower() == s.lower():
                return vc
        raise ValueError(f"Invalid stop Class '{v}'. Must be one of: {sorted(list(VALID_CLASSES))}")

    @field_validator("stop_type")
    @classmethod
    def clean_type(cls, v: str) -> str:
        s = v.strip().capitalize()
        for vt in VALID_TYPES:
            if vt.lower() == s.lower():
                return vt
        raise ValueError(f"Invalid stop Type '{v}'. Must be one of: {sorted(list(VALID_TYPES))}")

    @field_validator("duration_hours")
    @classmethod
    def round_duration(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"Duration must be strictly positive (> 0), got {v}")
        return round(float(v), 2)

    @model_validator(mode="after")
    def compute_kpi_flag_and_hash(self) -> "StoppageRecord":
        # Incidents and Circumstance affect machine KPIs, Schedule does not
        self.affects_kpi = self.stop_class in ["Incidents", "Circumstance"]
        
        # Build deterministic SHA-256 hash key for deduplication
        hash_payload = (
            f"{self.plant}|{self.machine}|"
            f"{self.start_time.isoformat()}|{self.end_time.isoformat()}|"
            f"{self.duration_hours:.2f}|{self.reason.strip().lower()}"
        )
        self.record_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()
        return self


class IngestionRowError(BaseModel):
    """Details of a rejected or invalid row during ingestion."""
    row_number: int
    raw_data: Dict[str, Any]
    error_message: str


class IngestionReport(BaseModel):
    """Comprehensive audit report for an ingestion batch."""
    batch_id: str
    filename: str
    plant_detected: str
    total_rows_read: int
    valid_rows_count: int
    duplicates_skipped: int
    inserted_rows_count: int
    error_rows_count: int
    errors: List[IngestionRowError] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_success(self) -> bool:
        return self.inserted_rows_count > 0 or (self.total_rows_read > 0 and self.error_rows_count == 0)

