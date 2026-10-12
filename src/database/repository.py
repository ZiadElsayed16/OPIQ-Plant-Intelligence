"""
OPIQ Stoppage Database Repository.
Handles transactional batch insertions, duplicate detection, and filtered analytical queries.
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import json
import sqlite3
import pandas as pd

from src.models.stoppage import StoppageRecord, IngestionReport
from src.database.db import get_db_connection, init_db


class StoppageRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        init_db(self.db_path)

    def insert_batch(self, report: IngestionReport, records: List[StoppageRecord]) -> IngestionReport:
        """
        Atomically saves ingestion batch metadata and stoppage records.
        Skips records whose record_hash already exists in the database.
        Updates and returns the finalized IngestionReport.
        """
        conn = get_db_connection(self.db_path)
        inserted_count = 0
        duplicates_count = 0
        now_iso = datetime.utcnow().isoformat()

        errors_json = json.dumps([e.model_dump() for e in report.errors])

        try:
            with conn:
                # 1. Insert batch metadata
                conn.execute(
                    """
                    INSERT INTO ingestion_batches (
                        batch_id, filename, plant_detected, total_rows_read,
                        valid_rows_count, duplicates_skipped, inserted_rows_count,
                        error_rows_count, errors_json, ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report.batch_id,
                        report.filename,
                        report.plant_detected,
                        report.total_rows_read,
                        report.valid_rows_count,
                        0,  # placeholder, will update below
                        0,  # placeholder
                        report.error_rows_count,
                        errors_json,
                        now_iso
                    )
                )

                # 2. Insert records using INSERT OR IGNORE for hash uniqueness
                for rec in records:
                    cursor = conn.execute(
                        """
                        INSERT OR IGNORE INTO stoppages (
                            batch_id, plant, machine, start_time, end_time,
                            duration_hours, stop_class, stop_type, reason,
                            affects_kpi, record_hash, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            report.batch_id,
                            rec.plant,
                            rec.machine,
                            rec.start_time.isoformat(),
                            rec.end_time.isoformat(),
                            rec.duration_hours,
                            rec.stop_class,
                            rec.stop_type,
                            rec.reason,
                            1 if rec.affects_kpi else 0,
                            rec.record_hash,
                            now_iso
                        )
                    )
                    if cursor.rowcount > 0:
                        inserted_count += 1
                    else:
                        duplicates_count += 1

                # 3. Update batch metadata with exact counts
                conn.execute(
                    """
                    UPDATE ingestion_batches
                    SET inserted_rows_count = ?, duplicates_skipped = ?
                    WHERE batch_id = ?
                    """,
                    (inserted_count, duplicates_count, report.batch_id)
                )

        finally:
            conn.close()

        # Update in-memory report
        report.inserted_rows_count = inserted_count
        report.duplicates_skipped = duplicates_count
        return report

    def query_stoppages(
        self,
        plant: Optional[str] = None,
        machines: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        stop_class: Optional[str] = None,
        stop_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Executes an indexed SQL query to retrieve filtered stoppage records
        directly into an analytical Pandas DataFrame.
        """
        conn = get_db_connection(self.db_path)
        
        query = """
            SELECT
                id,
                batch_id,
                plant AS "Plant",
                machine AS "Machine",
                start_time AS "Start Date",
                end_time AS "End Date",
                duration_hours AS "Duration",
                stop_class AS "Class",
                stop_type AS "Type",
                reason AS "Reason for downtime",
                affects_kpi AS "Affects_KPI"
            FROM stoppages
            WHERE 1=1
        """
        params = []

        if plant and plant not in ["All Plants", "All Plants (Total)", "Both Plants"]:
            query += " AND plant = ?"
            params.append(plant)

        if machines and len(machines) > 0 and "All Machines" not in machines and "Whole Fleet" not in machines:
            placeholders = ",".join("?" for _ in machines)
            query += f" AND machine IN ({placeholders})"
            params.extend(machines)

        if start_date:
            query += " AND start_time >= ?"
            params.append(str(start_date))

        if end_date:
            query += " AND start_time <= ?"
            params.append(str(end_date))

        if stop_class and stop_class != "All Classes":
            query += " AND stop_class = ?"
            params.append(stop_class)

        if stop_type and stop_type != "All Types":
            query += " AND stop_type = ?"
            params.append(stop_type)

        query += " ORDER BY start_time ASC"

        try:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df["Start Date"] = pd.to_datetime(df["Start Date"])
                df["End Date"] = pd.to_datetime(df["End Date"])
                df["Duration"] = pd.to_numeric(df["Duration"], errors="coerce").fillna(0.0)
                df["Affects_KPI"] = df["Affects_KPI"].astype(bool)
            return df
        finally:
            conn.close()

    def get_plants(self) -> List[str]:
        """Returns distinct plants present in the database."""
        conn = get_db_connection(self.db_path)
        try:
            cur = conn.execute("SELECT DISTINCT plant FROM stoppages ORDER BY plant ASC")
            return [row["plant"] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_machines(self, plant: Optional[str] = None) -> List[str]:
        """Returns distinct machines for a given plant (or all plants)."""
        conn = get_db_connection(self.db_path)
        try:
            if plant and plant not in ["All Plants", "All Plants (Total)", "Both Plants"]:
                cur = conn.execute("SELECT DISTINCT machine FROM stoppages WHERE plant = ? ORDER BY machine ASC", (plant,))
            else:
                cur = conn.execute("SELECT DISTINCT machine FROM stoppages ORDER BY machine ASC")
            return [row["machine"] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_batches(self) -> List[Dict[str, Any]]:
        """Returns full audit history of all uploaded ingestion batches."""
        conn = get_db_connection(self.db_path)
        try:
            cur = conn.execute("SELECT * FROM ingestion_batches ORDER BY ingested_at DESC")
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_total_records_count(self) -> int:
        """Returns total number of stoppage records in the database."""
        conn = get_db_connection(self.db_path)
        try:
            cur = conn.execute("SELECT COUNT(*) as count FROM stoppages")
            return cur.fetchone()["count"]
        finally:
            conn.close()

