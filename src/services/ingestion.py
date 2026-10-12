"""
OPIQ Stoppage Ingestion Service.
Safely extracts, normalizes, validates, and ingests Excel/CSV stoppage files into the database.
Handles midnight-crossing edge cases, flexible column naming, and duplicate detection.
"""
from datetime import datetime, timedelta
import io
from pathlib import Path
from typing import Union, Optional, List, Dict, Any, Tuple, Sequence
import uuid
import pandas as pd

from src.models.stoppage import StoppageRecord, IngestionReport, IngestionRowError
from src.database.repository import StoppageRepository


class IngestionService:
    def __init__(self, db_path: Optional[Path] = None):
        self.repository = StoppageRepository(db_path=db_path)

    def ingest_file(
        self,
        file_source: Union[str, Path, bytes, io.BytesIO],
        filename: str,
        default_plant: Optional[str] = None
    ) -> IngestionReport:
        """
        Main entry point for processing and saving an uploaded stoppage file.
        Returns a complete IngestionReport with audit counts and any row-level errors.
        """
        batch_id = str(uuid.uuid4())
        clean_filename = Path(filename).name

        # 1. Detect plant from filename if not explicitly provided
        plant_detected = default_plant
        fn_low = clean_filename.lower()
        if not plant_detected:
            if "cleopatra" in fn_low:
                plant_detected = "Cleopatra Plant"
            elif "bmic" in fn_low:
                plant_detected = "BMIC Plant"
            else:
                plant_detected = "Cleopatra Plant"  # Default fallback

        # 2. Read raw tabular data into Pandas
        try:
            df = self._read_raw_dataframe(file_source, clean_filename)
        except Exception as e:
            return IngestionReport(
                batch_id=batch_id,
                filename=clean_filename,
                plant_detected=plant_detected,
                total_rows_read=0,
                valid_rows_count=0,
                duplicates_skipped=0,
                inserted_rows_count=0,
                error_rows_count=1,
                errors=[
                    IngestionRowError(
                        row_number=0,
                        raw_data={},
                        error_message=f"Failed to read file format: {str(e)}"
                    )
                ]
            )

        # 3. Clean and map columns
        col_map = self._map_columns(list(df.columns))
        missing_critical = [req for req in ["machine", "start_date"] if req not in col_map]
        if missing_critical:
            return IngestionReport(
                batch_id=batch_id,
                filename=clean_filename,
                plant_detected=plant_detected,
                total_rows_read=len(df),
                valid_rows_count=0,
                duplicates_skipped=0,
                inserted_rows_count=0,
                error_rows_count=1,
                errors=[
                    IngestionRowError(
                        row_number=0,
                        raw_data={"columns_found": list(df.columns)},
                        error_message=f"Missing critical column(s): {missing_critical}"
                    )
                ]
            )

        # 4. Parse row by row with edge-case resolution & validation
        valid_records: List[StoppageRecord] = []
        errors: List[IngestionRowError] = []

        total_rows = len(df)
        for row_idx, (_, row) in enumerate(df.iterrows(), start=2):
            raw_dict = {str(k): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}

            try:
                rec = self._parse_row(row, col_map, plant_detected)
                valid_records.append(rec)
            except Exception as ex:
                errors.append(
                    IngestionRowError(
                        row_number=row_idx,
                        raw_data=raw_dict,
                        error_message=str(ex)
                    )
                )

        # 5. Build initial report
        report = IngestionReport(
            batch_id=batch_id,
            filename=clean_filename,
            plant_detected=plant_detected,
            total_rows_read=total_rows,
            valid_rows_count=len(valid_records),
            duplicates_skipped=0,
            inserted_rows_count=0,
            error_rows_count=len(errors),
            errors=errors
        )

        # 6. Save batch and records into repository (handles duplicate skip)
        final_report = self.repository.insert_batch(report, valid_records)
        return final_report

    def _read_raw_dataframe(self, source: Union[str, Path, bytes, io.BytesIO], filename: str) -> pd.DataFrame:
        """Reads CSV or Excel from file path or bytes buffer."""
        is_excel = filename.lower().endswith((".xlsx", ".xls"))
        
        if isinstance(source, (str, Path)):
            if is_excel:
                return pd.read_excel(str(source))
            return pd.read_csv(str(source))
        elif isinstance(source, bytes):
            buffer = io.BytesIO(source)
            if is_excel:
                return pd.read_excel(buffer)
            return pd.read_csv(buffer)
        else:
            # Assumed io.BytesIO
            source.seek(0)
            if is_excel:
                return pd.read_excel(source)
            return pd.read_csv(source)

    def _map_columns(self, columns: Sequence[Any]) -> Dict[str, str]:
        """Maps loose spreadsheet column headers to standard canonical keys."""
        mapping = {}
        for c in columns:
            clean = str(c).strip().lower()
            if clean in ["plant", "facility", "site"]:
                mapping["plant"] = c
            elif clean in ["machine", "equipment", "asset"]:
                mapping["machine"] = c
            elif clean in ["start date", "start_date", "start datetime", "start time"]:
                # If both Start Date and Start Time exist, differentiate
                if "time" in clean and "start_date" in mapping:
                    mapping["start_time_part"] = c
                else:
                    mapping["start_date"] = c
            elif clean in ["end date", "end_date", "end datetime", "end time"]:
                if "time" in clean and "end_date" in mapping:
                    mapping["end_time_part"] = c
                else:
                    mapping["end_date"] = c
            elif clean in ["duration", "duration (hrs)", "duration hours", "hours"]:
                mapping["duration"] = c
            elif clean in ["class", "stoppage class", "stop class"]:
                mapping["class"] = c
            elif clean in ["type", "stoppage type", "stop type"]:
                mapping["type"] = c
            elif clean in ["reason for downtime", "reason", "cause", "downtime reason", "event"]:
                mapping["reason"] = c

        return mapping

    def _parse_row(self, row: pd.Series, col_map: Dict[str, str], fallback_plant: str) -> StoppageRecord:
        """Constructs and validates a single StoppageRecord from a row."""
        # 1. Plant
        plant_val = row[col_map["plant"]] if "plant" in col_map and pd.notna(row[col_map["plant"]]) else fallback_plant
        plant_val = str(plant_val).strip()

        # 2. Machine
        machine_val = row[col_map["machine"]]
        if pd.isna(machine_val) or not str(machine_val).strip():
            raise ValueError("Machine field is missing or empty")
        machine_val = str(machine_val).strip()

        # 3. Class and Type
        class_val = str(row[col_map["class"]]).strip() if "class" in col_map and pd.notna(row[col_map["class"]]) else "Incidents"
        type_val = str(row[col_map["type"]]).strip() if "type" in col_map and pd.notna(row[col_map["type"]]) else "Mechanical"
        reason_val = str(row[col_map["reason"]]).strip() if "reason" in col_map and pd.notna(row[col_map["reason"]]) else "Unspecified stop"

        # 4. Duration
        dur_val = row.get(col_map.get("duration", None), None)
        duration_hours = None
        if pd.notna(dur_val):
            try:
                duration_hours = float(dur_val)
                if duration_hours < 0:
                    raise ValueError(f"Explicit negative duration is not allowed: {duration_hours}")
            except ValueError as ve:
                raise ve
            except Exception:
                duration_hours = None

        # 5. Start and End Datetime Resolution
        start_dt = self._parse_datetime(
            date_val=row.get(col_map.get("start_date", None), None),
            time_val=row.get(col_map.get("start_time_part", None), None)
        )
        if not start_dt:
            raise ValueError(f"Invalid or missing start datetime: '{row.get(col_map.get('start_date', None))}'")

        end_dt = self._parse_datetime(
            date_val=row.get(col_map.get("end_date", None), None),
            time_val=row.get(col_map.get("end_time_part", None), None)
        )

        # ── Edge Case Resolution ──
        # Case A: If End Date is missing, compute from Duration
        if not end_dt and duration_hours and duration_hours > 0:
            end_dt = start_dt + timedelta(hours=duration_hours)

        # Case B: If Duration is missing or zero, compute from (end_dt - start_dt)
        if (duration_hours is None or duration_hours <= 0) and end_dt:
            calc_diff = (end_dt - start_dt).total_seconds() / 3600.0
            if calc_diff > 0:
                duration_hours = calc_diff

        # Case C: Midnight Crossing on Same Date:
        # e.g., Start Date = 2025-01-01 18:21, End Date entered as 2025-01-01 09:16 (the next morning)
        # If end_dt <= start_dt but duration > 0, the stop rolled into the next day(s)
        if end_dt and end_dt <= start_dt:
            if duration_hours and duration_hours > 0:
                # Add enough 24h increments until end_dt > start_dt
                candidate = end_dt
                while candidate <= start_dt:
                    candidate += timedelta(days=1)
                end_dt = candidate
            else:
                raise ValueError(f"End time ({end_dt}) is before or equal to start time ({start_dt}) with non-positive duration")

        # Fallback if duration is still invalid
        if duration_hours is None or duration_hours <= 0:
            raise ValueError(f"Duration must be strictly positive, calculated: {duration_hours}")

        if not end_dt:
            end_dt = start_dt + timedelta(hours=duration_hours)

        # Construct and validate through Pydantic
        return StoppageRecord(
            plant=plant_val,
            machine=machine_val,
            start_time=start_dt,
            end_time=end_dt,
            duration_hours=duration_hours,
            stop_class=class_val,
            stop_type=type_val,
            reason=reason_val,
            affects_kpi=True,
            record_hash=""
        )

    def _parse_datetime(self, date_val: Any, time_val: Any = None) -> Optional[datetime]:
        """Safely combines date and optional time component into a Python datetime."""
        if pd.isna(date_val) or date_val is None or str(date_val).strip() == "":
            return None

        # If date_val is already a timestamp
        if isinstance(date_val, (pd.Timestamp, datetime)):
            base_dt = pd.to_datetime(date_val).to_pydatetime()
        else:
            base_dt = pd.to_datetime(str(date_val).strip(), errors="coerce")
            if pd.isna(base_dt):
                return None
            base_dt = base_dt.to_pydatetime()

        # If a separate time value was supplied (e.g., "3:41:00 AM")
        if time_val is not None and pd.notna(time_val) and str(time_val).strip() != "":
            try:
                # Extract time portion
                t_str = str(time_val).strip()
                t_parsed = pd.to_datetime(t_str, errors="coerce")
                if not pd.isna(t_parsed):
                    base_dt = datetime(
                        year=base_dt.year,
                        month=base_dt.month,
                        day=base_dt.day,
                        hour=t_parsed.hour,
                        minute=t_parsed.minute,
                        second=t_parsed.second
                    )
            except Exception:
                pass  # Fall back to base_dt

        return base_dt
