"""
Synthetic Data Generator for Cement Plant Machine Stoppages.
Covers: 2025-01-01 to 2026-10-10.
Schema (9 columns):
Machine, Start Date, End Date, Start Time, End Time, Duration, Class, Type, Reason for downtime
"""
import random
from datetime import datetime, timedelta
import pandas as pd

# Define machines
MACHINES = [
    "Kiln",
    "Raw mill",
    "W.CEMENT MILL (A)",
    "W.CEMENT MILL (B)",
    "Sand mill",
    "Crusher"
]

# Stoppage profiles reflecting cement manufacturing operations & user sample
STOP_CATALOG = {
    "Sand mill": [
        ("Circumstance", "Circumstance", "As high level of ground sand.", 1.5, 14.0, 0.65),
        ("Incidents", "Mechanical", "As flow low of girth gear pump.", 0.5, 2.5, 0.10),
        ("Incidents", "Mechanical", "As P.M request to check gearbox pump.", 1.0, 3.5, 0.08),
        ("Incidents", "Mechanical", "As F.L in gearbox pump.", 0.8, 2.2, 0.05),
        ("Incidents", "Electrical", "As electrical problem in mill main drive.", 1.5, 5.0, 0.07),
        ("Schedule", "Schedule", "As Schedule.", 4.0, 12.0, 0.05),
    ],
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

def format_time_str(dt):
    return dt.strftime("%I:%M:%S %p").lstrip("0")

def generate_records():
    records = []
    
    # Range: 2025-01-01 to 2026-08-31 (we will insert the exact Sept 2026 sample afterwards, plus early Oct 2026)
    start_dt = datetime(2025, 1, 1)
    end_dt = datetime(2026, 8, 31)
    
    current_dt = start_dt
    random.seed(42)
    
    while current_dt <= end_dt:
        date_str = f"{current_dt.month}/{current_dt.day}/{current_dt.year}"
        
        for machine in MACHINES:
            # Stoppage probability for this machine today
            prob = 0.35 if machine in ["Kiln", "Raw mill"] else 0.45
            if random.random() < prob:
                num_stops = random.choices([1, 2, 3], weights=[0.70, 0.25, 0.05])[0]
                
                # Available time window tracking to avoid unrealistic math
                day_total_dur = 0.0
                curr_hour = random.uniform(0.0, 4.0)
                
                for _ in range(num_stops):
                    catalog = STOP_CATALOG[machine]
                    weights = [item[5] for item in catalog]
                    chosen = random.choices(catalog, weights=weights)[0]
                    cls, typ, reason, min_d, max_d, _ = chosen
                    
                    dur = round(random.uniform(min_d, max_d), 2)
                    if day_total_dur + dur > 23.95:
                        dur = round(max(0.5, 23.95 - day_total_dur), 2)
                        if dur <= 0.1:
                            break
                    
                    # Synthesize realistic start and end times
                    st_hour = int(curr_hour) % 24
                    st_min = int((curr_hour - int(curr_hour)) * 60)
                    start_time_obj = datetime(current_dt.year, current_dt.month, current_dt.day, st_hour, st_min)
                    
                    end_time_obj = start_time_obj + timedelta(hours=dur)
                    
                    records.append({
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

# User's verified September 2026 sample rows
USER_SAMPLE = [
    ("Sand mill", "9/1/2026", "9/1/2026", "12:00:00 AM", "6:23:00 AM", 6.38, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Sand mill", "9/1/2026", "9/1/2026", "5:41:00 PM", "12:00:00 AM", 6.32, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("W.CEMENT MILL (A)", "9/1/2026", "9/1/2026", "8:09:00 AM", "9:45:00 AM", 1.6, "Circumstance", "Circumstance", "As instructions."),
    ("W.CEMENT MILL (A)", "9/1/2026", "9/1/2026", "12:13:00 PM", "12:47:00 PM", 0.57, "Incidents", "Electrical", "As contactor fault in bad cement B.E."),
    ("W.CEMENT MILL (A)", "9/1/2026", "9/1/2026", "1:26:00 PM", "3:01:00 PM", 1.58, "Circumstance", "Circumstance", "High Level of small silo."),
    ("W.CEMENT MILL (B)", "9/1/2026", "9/1/2026", "10:03:00 AM", "12:00:00 AM", 13.95, "Circumstance", "Circumstance", "As instructions."),
    ("Sand mill", "9/2/2026", "9/2/2026", "12:00:00 AM", "3:21:00 AM", 3.35, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Sand mill", "9/2/2026", "9/2/2026", "11:42:00 AM", "12:00:00 AM", 12.3, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Raw mill", "9/2/2026", "9/2/2026", "8:44:00 AM", "2:16:00 PM", 5.53, "Schedule", "Schedule", "As Schedule."),
    ("Raw mill", "9/2/2026", "9/2/2026", "5:27:00 PM", "6:20:00 PM", 0.88, "Incidents", "Production", "As Blockage in filter above silo NO. 3270."),
    ("W.CEMENT MILL (B)", "9/2/2026", "9/2/2026", "12:00:00 AM", "2:05:00 AM", 2.08, "Circumstance", "Circumstance", "As instructions."),
    ("W.CEMENT MILL (B)", "9/2/2026", "9/2/2026", "5:35:00 AM", "12:50:00 PM", 7.25, "Circumstance", "Circumstance", "As lab request."),
    ("Sand mill", "9/3/2026", "9/3/2026", "12:00:00 AM", "8:09:00 AM", 8.15, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Sand mill", "9/3/2026", "9/3/2026", "1:21:00 PM", "12:00:00 AM", 10.65, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Raw mill", "9/3/2026", "9/3/2026", "12:50:00 AM", "8:39:00 AM", 7.82, "Circumstance", "Circumstance", "As kiln down."),
    ("Raw mill", "9/3/2026", "9/3/2026", "10:20:00 AM", "5:58:00 PM", 7.63, "Incidents", "Mechanical", "As PM request to check filter."),
    ("Kiln", "9/3/2026", "9/3/2026", "12:30:00 AM", "7:33:00 AM", 7.05, "Incidents", "Production", "blockage in C4."),
    ("W.CEMENT MILL (A)", "9/3/2026", "9/3/2026", "6:40:00 AM", "12:00:00 AM", 17.33, "Schedule", "Schedule", "As Schedule."),
    ("Sand mill", "9/4/2026", "9/4/2026", "12:00:00 AM", "6:00:00 AM", 6.0, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Sand mill", "9/4/2026", "9/4/2026", "3:04:00 PM", "12:00:00 AM", 8.93, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Raw mill", "9/4/2026", "9/4/2026", "1:50:00 AM", "3:04:00 AM", 1.23, "Incidents", "Mechanical", "As mechanical request to check oil of girth gear unit."),
    ("W.CEMENT MILL (A)", "9/4/2026", "9/4/2026", "12:00:00 AM", "2:30:00 AM", 2.5, "Schedule", "Schedule", "As Schedule."),
    ("Sand mill", "9/5/2026", "9/5/2026", "12:00:00 AM", "1:54:00 AM", 1.9, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Sand mill", "9/5/2026", "9/5/2026", "9:50:00 AM", "12:00:00 AM", 14.17, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Raw mill", "9/5/2026", "9/5/2026", "11:26:00 AM", "5:16:00 PM", 5.83, "Incidents", "Mechanical", "As mechanical request to check lubrication unit gearth gear pumb."),
    ("W.CEMENT MILL (A)", "9/5/2026", "9/5/2026", "7:00:00 AM", "11:48:00 AM", 4.8, "Circumstance", "Circumstance", "Clinker hopper empty."),
    ("Sand mill", "9/6/2026", "9/6/2026", "12:00:00 AM", "12:45:00 AM", 0.75, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Sand mill", "9/6/2026", "9/6/2026", "12:45:00 AM", "1:15:00 AM", 0.5, "Incidents", "Mechanical", "As flow low of girth gear pump."),
    ("Sand mill", "9/6/2026", "9/6/2026", "1:15:00 AM", "4:28:00 AM", 3.22, "Incidents", "Electrical", "As electrical problem in mill main drive."),
    ("Sand mill", "9/6/2026", "9/6/2026", "4:30:00 PM", "12:00:00 AM", 7.5, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Raw mill", "9/6/2026", "9/6/2026", "3:25:00 AM", "5:13:00 AM", 1.8, "Incidents", "Mechanical", "As flow low of girth gear pump."),
    ("Raw mill", "9/6/2026", "9/6/2026", "10:12:00 AM", "10:34:00 AM", 0.37, "Incidents", "Mechanical", "As mechanical maintenance to check kaolin prefeeder."),
    ("W.CEMENT MILL (B)", "9/6/2026", "9/6/2026", "1:55:00 PM", "4:34:00 PM", 2.65, "Incidents", "Mechanical", "As PM request to check mill filter."),
    ("Sand mill", "9/7/2026", "9/7/2026", "12:00:00 AM", "12:30:00 AM", 0.5, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Sand mill", "9/7/2026", "9/7/2026", "10:45:00 AM", "6:32:00 PM", 7.78, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("W.CEMENT MILL (A)", "9/7/2026", "9/7/2026", "5:12:00 AM", "12:29:00 PM", 7.28, "Circumstance", "Circumstance", "Clinker hopper empty."),
    ("W.CEMENT MILL (B)", "9/7/2026", "9/7/2026", "7:25:00 AM", "4:48:00 PM", 9.38, "Circumstance", "Circumstance", "As lab Request."),
    ("Crusher", "9/8/2026", "9/8/2026", "5:32:00 AM", "10:09:00 AM", 4.62, "Circumstance", "Circumstance", "As instructions."),
    ("Crusher", "9/8/2026", "9/8/2026", "1:59:00 PM", "12:00:00 AM", 10.02, "Circumstance", "Circumstance", "As instructions."),
    ("Sand mill", "9/8/2026", "9/8/2026", "7:42:00 AM", "4:50:00 PM", 9.13, "Circumstance", "Circumstance", "As high level of ground sand ."),
    ("Raw mill", "9/8/2026", "9/8/2026", "11:47:00 PM", "12:00:00 AM", 0.22, "Incidents", "Mechanical", "As limestone weigh feeder drifted."),
    ("Kiln", "9/8/2026", "9/8/2026", "10:30:00 PM", "11:50:00 PM", 1.33, "Incidents", "Mechanical", "As High High kiln postion."),
    ("W.CEMENT MILL (A)", "9/8/2026", "9/8/2026", "12:12:00 PM", "12:00:00 AM", 11.8, "Circumstance", "Circumstance", "As high level of silo A."),
    ("W.CEMENT MILL (B)", "9/8/2026", "9/8/2026", "6:05:00 AM", "8:10:00 PM", 14.08, "Schedule", "Schedule", "As Schedule."),
    ("Crusher", "9/9/2026", "9/9/2026", "5:11:00 AM", "11:17:00 AM", 6.1, "Circumstance", "Circumstance", "As instructions."),
    ("Crusher", "9/9/2026", "9/9/2026", "1:52:00 PM", "5:13:00 PM", 3.35, "Circumstance", "Circumstance", "As instructions."),
    ("Crusher", "9/9/2026", "9/9/2026", "5:48:00 PM", "10:23:00 PM", 4.58, "Circumstance", "Circumstance", "As instructions."),
    ("Sand mill", "9/9/2026", "9/9/2026", "12:57:00 AM", "8:34:00 AM", 7.62, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Sand mill", "9/9/2026", "9/9/2026", "12:50:00 PM", "3:10:00 PM", 2.33, "Incidents", "Mechanical", "As P.M request to check gearbox pump."),
    ("Sand mill", "9/9/2026", "9/9/2026", "5:17:00 PM", "6:25:00 PM", 1.13, "Incidents", "Mechanical", "As F.L in gearbox pump."),
    ("Sand mill", "9/9/2026", "9/9/2026", "7:55:00 PM", "10:05:00 PM", 2.17, "Incidents", "Mechanical", "As F.L in gearbox pump."),
    ("Raw mill", "9/9/2026", "9/9/2026", "12:00:00 AM", "12:20:00 AM", 0.33, "Incidents", "Mechanical", "As limestone weigh feeder drifted."),
    ("Raw mill", "9/9/2026", "9/9/2026", "1:33:00 AM", "2:36:00 AM", 1.05, "Incidents", "Production", "As blockage in airslide after bucket elevator."),
    ("W.CEMENT MILL (A)", "9/9/2026", "9/9/2026", "12:00:00 AM", "11:59:00 PM", 23.98, "Circumstance", "Circumstance", "As high level of silo A."),
    ("Crusher", "9/10/2026", "9/10/2026", "1:33:00 AM", "11:59:00 PM", 22.43, "Circumstance", "Circumstance", "As instructions."),
    ("Sand mill", "9/10/2026", "9/10/2026", "11:45:00 AM", "9:26:00 PM", 9.68, "Circumstance", "Circumstance", "As high level of ground sand."),
    ("Raw mill", "9/10/2026", "9/10/2026", "12:25:00 PM", "2:28:00 PM", 2.05, "Circumstance", "Circumstance", "As kiln down."),
    ("Kiln", "9/10/2026", "9/10/2026", "12:15:00 PM", "1:41:00 PM", 1.43, "Incidents", "Mechanical", "tire 2 retaining ring welding"),
    ("W.CEMENT MILL (A)", "9/10/2026", "9/10/2026", "12:00:00 AM", "11:59:00 PM", 23.98, "Circumstance", "Circumstance", "As high level of silo A.")
]

def main():
    print("Generating simulated plant stoppage history...")
    historical = generate_records()
    df_hist = pd.DataFrame(historical)
    
    # Format sample into DataFrame
    sample_dicts = []
    for row in USER_SAMPLE:
        sample_dicts.append({
            "Machine": row[0],
            "Start Date": row[1],
            "End Date": row[2],
            "Start Time": row[3],
            "End Time": row[4],
            "Duration": row[5],
            "Class": row[6],
            "Type": row[7],
            "Reason for downtime": row[8]
        })
    df_sample = pd.DataFrame(sample_dicts)
    
    # Generate late Sept & early Oct 2026 data up to Oct 10, 2026
    oct_records = []
    current_dt = datetime(2026, 9, 11)
    end_dt = datetime(2026, 10, 10)
    while current_dt <= end_dt:
        date_str = f"{current_dt.month}/{current_dt.day}/{current_dt.year}"
        for machine in MACHINES:
            if random.random() < 0.38:
                catalog = STOP_CATALOG[machine]
                chosen = random.choice(catalog)
                dur = round(random.uniform(chosen[3], min(chosen[4], 16.0)), 2)
                st_hour = random.randint(1, 16)
                st_time = datetime(current_dt.year, current_dt.month, current_dt.day, st_hour, 0)
                end_time = st_time + timedelta(hours=dur)
                oct_records.append({
                    "Machine": machine,
                    "Start Date": date_str,
                    "End Date": date_str,
                    "Start Time": format_time_str(st_time),
                    "End Time": format_time_str(end_time),
                    "Duration": dur,
                    "Class": chosen[0],
                    "Type": chosen[1],
                    "Reason for downtime": chosen[2]
                })
        current_dt += timedelta(days=1)
        
    df_oct = pd.DataFrame(oct_records)
    
    # Combine all
    df_full = pd.concat([df_hist, df_sample, df_oct], ignore_index=True)
    
    # Save to Excel and CSV
    excel_path = "plant_stops_2025_2026.xlsx"
    csv_path = "plant_stops_2025_2026.csv"
    df_full.to_excel(excel_path, index=False)
    df_full.to_csv(csv_path, index=False)
    
    print(f"Dataset generated successfully!")
    print(f"Total rows: {len(df_full)}")
    print(f"Saved to: {excel_path} and {csv_path}")

if __name__ == "__main__":
    main()
