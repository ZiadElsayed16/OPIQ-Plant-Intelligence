"""
Multi-Plant Synthetic Stoppage Generator for Cement Manufacturing:
1. Cleopatra Plant: Kiln, Raw mill, W.CEMENT MILL (A), W.CEMENT MILL (B), Sand mill, Crusher
2. BMIC Plant: Kiln, Raw mill, W.CEMENT MILL (A), W.CEMENT MILL (B), Coal mill, Crusher
Spans 2025-01-01 to 2026-10-10.
"""
import random
from datetime import datetime, timedelta
import pandas as pd

# Cleopatra machines
CLEOPATRA_MACHINES = [
    "Kiln",
    "Raw mill",
    "W.CEMENT MILL (A)",
    "W.CEMENT MILL (B)",
    "Sand mill",
    "Crusher"
]

# BMIC machines (No Sand Mill, has Coal Mill)
BMIC_MACHINES = [
    "Kiln",
    "Raw mill",
    "W.CEMENT MILL (A)",
    "W.CEMENT MILL (B)",
    "Coal mill",
    "Crusher"
]

COMMON_CATALOG = {
    "W.CEMENT MILL (A)": [
        ("Circumstance", "Circumstance", "As instructions.", 1.5, 12.0, 0.20),
        ("Circumstance", "Circumstance", "High Level of small silo.", 1.0, 8.0, 0.15),
        ("Circumstance", "Circumstance", "Clinker hopper empty.", 2.0, 10.0, 0.15),
        ("Circumstance", "Circumstance", "As high level of silo A.", 4.0, 24.0, 0.20),
        ("Incidents", "Electrical", "As contactor fault in bad cement B.E.", 0.5, 2.0, 0.07),
        ("Incidents", "Mechanical", "As PM request to check mill filter.", 1.0, 4.0, 0.08),
        ("Schedule", "Schedule", "As Schedule.", 2.5, 18.0, 0.15),
    ],
    "W.CEMENT MILL (B)": [
        ("Circumstance", "Circumstance", "As instructions.", 1.5, 14.0, 0.25),
        ("Circumstance", "Circumstance", "As lab request.", 2.0, 9.5, 0.20),
        ("Circumstance", "Circumstance", "Clinker hopper empty.", 3.0, 12.0, 0.15),
        ("Incidents", "Mechanical", "As PM request to check mill filter.", 1.0, 3.5, 0.15),
        ("Incidents", "Electrical", "As electrical trip on fan drive.", 0.5, 3.0, 0.10),
        ("Schedule", "Schedule", "As Schedule.", 4.0, 16.0, 0.15),
    ],
    "Raw mill": [
        ("Circumstance", "Circumstance", "As kiln down.", 2.0, 16.0, 0.25),
        ("Incidents", "Mechanical", "As PM request to check filter.", 1.0, 7.5, 0.15),
        ("Incidents", "Mechanical", "As mechanical request to check oil of girth gear unit.", 1.0, 4.0, 0.10),
        ("Incidents", "Mechanical", "As mechanical request to check lubrication unit gearth gear pumb.", 1.0, 6.0, 0.10),
        ("Incidents", "Mechanical", "As limestone weigh feeder drifted.", 0.2, 1.5, 0.10),
        ("Incidents", "Mechanical", "As mechanical maintenance to check kaolin prefeeder.", 0.3, 2.0, 0.08),
        ("Incidents", "Production", "As Blockage in filter above silo NO. 3270.", 0.5, 3.0, 0.08),
        ("Incidents", "Production", "As blockage in airslide after bucket elevator.", 0.8, 3.5, 0.06),
        ("Schedule", "Schedule", "As Schedule.", 4.0, 12.0, 0.08),
    ],
    "Kiln": [
        ("Incidents", "Production", "blockage in C4.", 2.0, 8.0, 0.25),
        ("Incidents", "Mechanical", "As High High kiln postion.", 1.0, 3.0, 0.20),
        ("Incidents", "Mechanical", "tire 2 retaining ring welding.", 1.2, 5.0, 0.15),
        ("Incidents", "Mechanical", "Cooler hydraulic cylinder leak.", 1.5, 4.0, 0.10),
        ("Incidents", "Electrical", "Kiln main drive VFD fault.", 0.5, 3.0, 0.10),
        ("Schedule", "Schedule", "As Schedule.", 6.0, 24.0, 0.20),
    ],
    "Crusher": [
        ("Circumstance", "Circumstance", "As instructions.", 2.0, 16.0, 0.55),
        ("Incidents", "Mechanical", "Hammer crusher rotor inspection.", 1.0, 4.0, 0.20),
        ("Incidents", "Electrical", "Conveyor belt pull cord switch trip.", 0.3, 1.5, 0.10),
        ("Schedule", "Schedule", "As Schedule.", 3.0, 8.0, 0.15),
    ]
}

# Cleopatra-specific (Sand mill)
SAND_MILL_CATALOG = [
    ("Circumstance", "Circumstance", "As high level of ground sand.", 1.5, 14.0, 0.65),
    ("Incidents", "Mechanical", "As flow low of girth gear pump.", 0.5, 2.5, 0.10),
    ("Incidents", "Mechanical", "As P.M request to check gearbox pump.", 1.0, 3.5, 0.08),
    ("Incidents", "Mechanical", "As F.L in gearbox pump.", 0.8, 2.2, 0.05),
    ("Incidents", "Electrical", "As electrical problem in mill main drive.", 1.5, 5.0, 0.07),
    ("Schedule", "Schedule", "As Schedule.", 4.0, 12.0, 0.05),
]

# BMIC-specific (Coal mill)
COAL_MILL_CATALOG = [
    ("Circumstance", "Circumstance", "Fine coal bin full.", 1.5, 12.0, 0.30),
    ("Circumstance", "Circumstance", "Raw coal bunker empty.", 1.0, 6.0, 0.15),
    ("Circumstance", "Circumstance", "As safety inerting system purge.", 0.5, 3.0, 0.10),
    ("Incidents", "Mechanical", "Coal mill bag filter pulse valve fault.", 0.8, 3.5, 0.12),
    ("Incidents", "Mechanical", "Grinding roller hydraulic pressure low.", 1.0, 4.0, 0.10),
    ("Incidents", "Mechanical", "Coal mill table liner wear inspection.", 1.5, 5.0, 0.08),
    ("Incidents", "Electrical", "CO analyzer alarm high trip.", 0.5, 2.0, 0.07),
    ("Incidents", "Electrical", "Mill inlet gas temperature high trip.", 0.8, 2.5, 0.05),
    ("Incidents", "Electrical", "Main drive motor overload trip.", 0.5, 3.0, 0.05),
    ("Schedule", "Schedule", "As Schedule.", 4.0, 16.0, 0.08),
]

def format_time_str(dt):
    return dt.strftime("%I:%M:%S %p").lstrip("0")

def generate_records_for_plant(plant_name, machine_list, seed=42):
    random.seed(seed)
    records = []
    start_dt = datetime(2025, 1, 1)
    end_dt = datetime(2026, 10, 10)
    current_dt = start_dt

    while current_dt <= end_dt:
        date_str = f"{current_dt.month}/{current_dt.day}/{current_dt.year}"
        for machine in machine_list:
            prob = 0.35 if machine in ["Kiln", "Raw mill"] else 0.42
            if random.random() < prob:
                num_stops = random.choices([1, 2, 3], weights=[0.72, 0.24, 0.04])[0]
                day_total_dur = 0.0
                curr_hour = random.uniform(0.0, 4.0)

                if machine == "Sand mill":
                    catalog = SAND_MILL_CATALOG
                elif machine == "Coal mill":
                    catalog = COAL_MILL_CATALOG
                else:
                    catalog = COMMON_CATALOG[machine]

                for _ in range(num_stops):
                    weights = [item[5] for item in catalog]
                    chosen = random.choices(catalog, weights=weights)[0]
                    cls, typ, reason, min_d, max_d, _ = chosen

                    dur = round(random.uniform(min_d, max_d), 2)
                    if day_total_dur + dur > 23.95:
                        dur = round(max(0.5, 23.95 - day_total_dur), 2)
                        if dur <= 0.1:
                            break

                    st_hour = int(curr_hour) % 24
                    st_min = int((curr_hour - int(curr_hour)) * 60)
                    start_time_obj = datetime(current_dt.year, current_dt.month, current_dt.day, st_hour, st_min)
                    end_time_obj = start_time_obj + timedelta(hours=dur)

                    records.append({
                        "Plant": plant_name,
                        "Machine": machine,
                        "Start Date": date_str,
                        "End Date": date_str,
                        "Start Time": format_time_str(start_time_obj),
                        "End Time": format_time_str(end_time_obj),
                        "Duration": dur,
                        "Class": cls,
                        "Type": typ,
                        "Reason for downtime": reason
                    })

                    day_total_dur += dur
                    curr_hour += dur + random.uniform(1.0, 5.0)
                    if curr_hour >= 24:
                        break

        current_dt += timedelta(days=1)
    return records

def main():
    print("Generating simulated multi-plant stoppage datasets...")
    # Cleopatra Plant
    cleopatra_records = generate_records_for_plant("Cleopatra Plant", CLEOPATRA_MACHINES, seed=101)
    df_cleopatra = pd.DataFrame(cleopatra_records)

    # BMIC Plant (has Coal Mill instead of Sand Mill)
    bmic_records = generate_records_for_plant("BMIC Plant", BMIC_MACHINES, seed=202)
    df_bmic = pd.DataFrame(bmic_records)

    # Combined All Plants
    df_all = pd.concat([df_cleopatra, df_bmic], ignore_index=True)

    # Save Cleopatra files (both standard 9-column and with Plant column)
    df_cleopatra.to_csv("cleopatra_plant_stops_2025_2026.csv", index=False)
    df_cleopatra.to_excel("cleopatra_plant_stops_2025_2026.xlsx", index=False)

    # Save BMIC files
    df_bmic.to_csv("bmic_plant_stops_2025_2026.csv", index=False)
    df_bmic.to_excel("bmic_plant_stops_2025_2026.xlsx", index=False)

    # Save Combined All Plants
    df_all.to_csv("all_plants_stops_2025_2026.csv", index=False)
    df_all.to_excel("all_plants_stops_2025_2026.xlsx", index=False)

    # Update backward-compatible plant_stops_2025_2026.csv with the combined data
    df_all.to_csv("plant_stops_2025_2026.csv", index=False)
    df_all.to_excel("plant_stops_2025_2026.xlsx", index=False)

    print(f"Generated Cleopatra records: {len(df_cleopatra)} rows (Sand mill included)")
    print(f"Generated BMIC records: {len(df_bmic)} rows (Coal mill included, no Sand mill)")
    print(f"Generated Combined records: {len(df_all)} rows")

if __name__ == "__main__":
    main()
