"""
Database Seeder Script for OPIQ.
Ingests baseline plant stoppage files into the SQLite operations database.
"""
from pathlib import Path
import sys

from src.database.db import DEFAULT_DB_PATH
from src.database.repository import StoppageRepository
from src.services.ingestion import IngestionService


def main():
    base_dir = Path(__file__).resolve().parent
    db_path = DEFAULT_DB_PATH
    
    print(f"Initializing OPIQ Database at: {db_path}")
    service = IngestionService(db_path=db_path)
    
    files_to_ingest = [
        ("cleopatra_plant_stops_2025_2026.csv", "Cleopatra Plant"),
        ("bmic_plant_stops_2025_2026.csv", "BMIC Plant")
    ]
    
    total_inserted = 0
    total_duplicates = 0
    total_errors = 0
    
    for filename, plant in files_to_ingest:
        file_path = base_dir / filename
        if not file_path.exists():
            print(f"Warning: File {filename} not found, skipping.")
            continue
            
        print(f"\nIngesting {filename} ({plant})...")
        report = service.ingest_file(
            file_source=file_path,
            filename=filename,
            default_plant=plant
        )
        
        print(f"  Rows read:            {report.total_rows_read}")
        print(f"  Valid rows:           {report.valid_rows_count}")
        print(f"  Inserted rows:        {report.inserted_rows_count}")
        print(f"  Duplicates skipped:   {report.duplicates_skipped}")
        print(f"  Error rows:           {report.error_rows_count}")
        
        if report.errors:
            print(f"  Sample errors (first 3):")
            for err in report.errors[:3]:
                print(f"    - Row {err.row_number}: {err.error_message}")
                
        total_inserted += report.inserted_rows_count
        total_duplicates += report.duplicates_skipped
        total_errors += report.error_rows_count

    repo = StoppageRepository(db_path=db_path)
    total_in_db = repo.get_total_records_count()
    plants = repo.get_plants()
    machines = repo.get_machines()

    print("\n" + "=" * 50)
    print("DATABASE SEEDING SUMMARY")
    print("=" * 50)
    print(f"Total Stoppages in DB: {total_in_db}")
    print(f"Registered Plants:     {plants}")
    print(f"Unique Machines:       {len(machines)} fleet assets ({', '.join(machines)})")
    print(f"Ingestion Batches:     {len(repo.get_batches())}")
    print("=" * 50)


if __name__ == "__main__":
    main()

