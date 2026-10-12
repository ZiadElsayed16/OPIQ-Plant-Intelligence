"""
Automated Test Suite for OPIQ Phase 1 Data Ingestion & Storage Pipeline.
Tests:
- Schema validation & alias normalization
- Dirty data tolerance & error reporting
- Midnight-crossing resolution
- Duplicate detection & deduplication
- Database persistence & audit trail
- Analytical query retrieval
"""
from datetime import datetime, timedelta
import io
from pathlib import Path
import tempfile
import pandas as pd
import pytest

from src.models.stoppage import StoppageRecord
from src.database.repository import StoppageRepository
from src.services.ingestion import IngestionService


@pytest.fixture
def temp_db():
    """Provides a fresh temporary SQLite database path for isolated testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass


class TestModelValidation:
    def test_valid_stoppage_record(self):
        start = datetime(2025, 1, 1, 8, 0)
        end = datetime(2025, 1, 1, 12, 0)
        rec = StoppageRecord(
            plant="cleopatra plant",
            machine="cement mill a",
            start_time=start,
            end_time=end,
            duration_hours=4.0,
            stop_class="incidents",
            stop_type="mechanical",
            reason="Girth gear oil inspection",
            affects_kpi=True
        )
        assert rec.plant == "Cleopatra Plant"
        assert rec.machine == "W.CEMENT MILL (A)"  # Normalized alias
        assert rec.stop_class == "Incidents"
        assert rec.stop_type == "Mechanical"
        assert rec.affects_kpi is True
        assert len(rec.record_hash) == 64  # SHA-256 hash generated

    def test_schedule_does_not_affect_kpi(self):
        start = datetime(2025, 1, 1, 8, 0)
        end = datetime(2025, 1, 1, 14, 0)
        rec = StoppageRecord(
            plant="BMIC Plant",
            machine="Kiln",
            start_time=start,
            end_time=end,
            duration_hours=6.0,
            stop_class="Schedule",
            stop_type="Schedule",
            reason="Planned maintenance overhaul",
            affects_kpi=True
        )
        # Model validator must force affects_kpi = False for Schedule
        assert rec.affects_kpi is False

    def test_negative_duration_raises_error(self):
        with pytest.raises(ValueError):
            StoppageRecord(
                plant="Cleopatra Plant",
                machine="Raw mill",
                start_time=datetime(2025, 1, 1, 8, 0),
                end_time=datetime(2025, 1, 1, 10, 0),
                duration_hours=-2.5,
                stop_class="Incidents",
                stop_type="Mechanical",
                reason="Fault",
                affects_kpi=True
            )

    def test_invalid_class_raises_error(self):
        with pytest.raises(ValueError):
            StoppageRecord(
                plant="Cleopatra Plant",
                machine="Raw mill",
                start_time=datetime(2025, 1, 1, 8, 0),
                end_time=datetime(2025, 1, 1, 10, 0),
                duration_hours=2.0,
                stop_class="UnplannedTrip",  # Not in {Incidents, Circumstance, Schedule}
                stop_type="Mechanical",
                reason="Fault",
                affects_kpi=True
            )


class TestIngestionPipeline:
    def test_clean_csv_ingestion(self, temp_db):
        service = IngestionService(db_path=temp_db)
        csv_content = """Plant,Machine,Start Date,End Date,Start Time,End Time,Duration,Class,Type,Reason for downtime
Cleopatra Plant,Raw mill,1/1/2025,1/1/2025,3:41:00 AM,6:40:24 AM,2.99,Incidents,Mechanical,Oil inspection
Cleopatra Plant,Kiln,1/1/2025,1/1/2025,8:00:00 AM,12:00:00 PM,4.0,Circumstance,Circumstance,Silo full
"""
        report = service.ingest_file(
            file_source=csv_content.encode("utf-8"),
            filename="cleopatra_test.csv"
        )

        assert report.total_rows_read == 2
        assert report.valid_rows_count == 2
        assert report.inserted_rows_count == 2
        assert report.duplicates_skipped == 0
        assert report.error_rows_count == 0
        assert service.repository.get_total_records_count() == 2

    def test_duplicate_rejection(self, temp_db):
        service = IngestionService(db_path=temp_db)
        csv_content = """Plant,Machine,Start Date,End Date,Duration,Class,Type,Reason for downtime
Cleopatra Plant,Raw mill,2025-01-01 08:00,2025-01-01 10:00,2.0,Incidents,Mechanical,Oil check
"""
        # First upload
        rep1 = service.ingest_file(csv_content.encode("utf-8"), "batch1.csv")
        assert rep1.inserted_rows_count == 1
        assert rep1.duplicates_skipped == 0

        # Second upload of exact same record
        rep2 = service.ingest_file(csv_content.encode("utf-8"), "batch2.csv")
        assert rep2.inserted_rows_count == 0
        assert rep2.duplicates_skipped == 1
        assert service.repository.get_total_records_count() == 1  # No double count

    def test_midnight_crossing_resolution(self, temp_db):
        service = IngestionService(db_path=temp_db)
        # Stop starts at 6:21 PM on 1/1/2025, ends at 9:16 AM next day, but log has End Date as 1/1/2025
        csv_content = """Plant,Machine,Start Date,End Date,Start Time,End Time,Duration,Class,Type,Reason for downtime
Cleopatra Plant,Raw mill,1/1/2025,1/1/2025,6:21:00 PM,9:16:00 AM,14.92,Circumstance,Circumstance,As kiln down
"""
        report = service.ingest_file(csv_content.encode("utf-8"), "midnight_test.csv")
        assert report.inserted_rows_count == 1

        df = service.repository.query_stoppages(plant="Cleopatra Plant")
        assert len(df) == 1
        start_ts = df["Start Date"].iloc[0]
        end_ts = df["End Date"].iloc[0]
        assert end_ts > start_ts
        # End Date must have rolled over to 1/2/2025
        assert end_ts.day == 2

    def test_dirty_row_isolation(self, temp_db):
        """Valid rows must be saved even if some rows in the file contain errors."""
        service = IngestionService(db_path=temp_db)
        csv_content = """Plant,Machine,Start Date,End Date,Duration,Class,Type,Reason for downtime
Cleopatra Plant,Raw mill,2025-01-01 08:00,2025-01-01 10:00,2.0,Incidents,Mechanical,Good row 1
Cleopatra Plant,,2025-01-01 08:00,2025-01-01 10:00,2.0,Incidents,Mechanical,Bad row missing machine
Cleopatra Plant,Kiln,2025-01-01 08:00,2025-01-01 10:00,-4.0,Incidents,Mechanical,Bad row negative duration
Cleopatra Plant,Crusher,2025-01-01 10:00,2025-01-01 12:00,2.0,Incidents,Mechanical,Good row 2
"""
        report = service.ingest_file(csv_content.encode("utf-8"), "dirty_file.csv")
        assert report.total_rows_read == 4
        assert report.valid_rows_count == 2
        assert report.inserted_rows_count == 2
        assert report.error_rows_count == 2
        assert len(report.errors) == 2
        # Check error row numbers (row 3 and row 4 in 1-indexed spreadsheet)
        assert report.errors[0].row_number == 3
        assert report.errors[1].row_number == 4

    def test_filtered_repository_queries(self, temp_db):
        service = IngestionService(db_path=temp_db)
        csv_content = """Plant,Machine,Start Date,End Date,Duration,Class,Type,Reason for downtime
Cleopatra Plant,Raw mill,2025-01-01 08:00,2025-01-01 10:00,2.0,Incidents,Mechanical,Vibration
Cleopatra Plant,Kiln,2025-01-02 08:00,2025-01-02 12:00,4.0,Schedule,Schedule,PM overhaul
BMIC Plant,Coal mill,2025-01-03 08:00,2025-01-03 11:00,3.0,Incidents,Electrical,Motor trip
"""
        service.ingest_file(csv_content.encode("utf-8"), "multi_plant.csv")

        # 1. Query by Plant
        cleo_df = service.repository.query_stoppages(plant="Cleopatra Plant")
        assert len(cleo_df) == 2

        # 2. Query by Machine
        coal_df = service.repository.query_stoppages(machines=["Coal mill"])
        assert len(coal_df) == 1
        assert coal_df["Plant"].iloc[0] == "BMIC Plant"

        # 3. Query by Class
        sched_df = service.repository.query_stoppages(stop_class="Schedule")
        assert len(sched_df) == 1
        assert sched_df["Machine"].iloc[0] == "Kiln"
        assert bool(sched_df["Affects_KPI"].iloc[0]) is False

        # 4. Check Audit Batches
        batches = service.repository.get_batches()
        assert len(batches) == 1
        assert batches[0]["filename"] == "multi_plant.csv"
        assert batches[0]["inserted_rows_count"] == 3

