"""
Core Analytics and KPI Engine for Multi-Plant Cement Stoppages.
Supports:
- Cleopatra Plant & BMIC Plant (and All Plants Combined).
- Fleet filtering (Whole Fleet vs Custom Selected Machines).
- Deterministic runtime reconstruction and KPI separation.
"""
from datetime import datetime
import pandas as pd
import numpy as np

def load_and_preprocess_data(file_path_or_buffer):
    """
    Loads and normalizes the stoppage dataset from Excel or CSV.
    Supports multi-plant datasets (Cleopatra, BMIC).
    """
    file_name = ""
    if isinstance(file_path_or_buffer, str):
        file_name = file_path_or_buffer.lower()
        if file_path_or_buffer.endswith(".csv"):
            df = pd.read_csv(file_path_or_buffer)
        else:
            df = pd.read_excel(file_path_or_buffer)
    else:
        # File buffer from Streamlit uploader
        if hasattr(file_path_or_buffer, "name"):
            file_name = file_path_or_buffer.name.lower()
        try:
            df = pd.read_excel(file_path_or_buffer)
        except Exception:
            file_path_or_buffer.seek(0)
            df = pd.read_csv(file_path_or_buffer)
            
    # Clean whitespace in column names
    df.columns = [c.strip() for c in df.columns]
    
    # Required columns check
    required_cols = ["Machine", "Start Date", "Duration", "Class", "Type", "Reason for downtime"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: '{col}'. Present columns: {list(df.columns)}")

    # Assign Plant column if not present
    if "Plant" not in df.columns:
        if "bmic" in file_name:
            df["Plant"] = "BMIC Plant"
        else:
            df["Plant"] = "Cleopatra Plant"
    else:
        df["Plant"] = df["Plant"].astype(str).str.strip()
            
    # Clean data types
    df["Duration"] = pd.to_numeric(df["Duration"], errors="coerce").fillna(0.0)
    df["Start Date"] = pd.to_datetime(df["Start Date"], errors="coerce")
    df["End Date"] = pd.to_datetime(df["End Date"], errors="coerce").fillna(df["Start Date"])
    
    # Standardize string fields
    df["Machine"] = df["Machine"].astype(str).str.strip()
    df["Class"] = df["Class"].astype(str).str.strip()
    df["Type"] = df["Type"].astype(str).str.strip()
    df["Reason for downtime"] = df["Reason for downtime"].astype(str).str.strip()
    
    # Flag KPI-impacting stops: Incidents & Circumstance affect machine KPIs, Schedule does not
    df["Affects_KPI"] = df["Class"].isin(["Incidents", "Circumstance"])
    
    # Drop records with invalid dates or duration <= 0
    df = df.dropna(subset=["Start Date"])
    df = df[df["Duration"] > 0].copy()
    
    # Sort chronologically
    df = df.sort_values(by=["Start Date", "Plant", "Machine"]).reset_index(drop=True)
    return df

def filter_data(df, start_date=None, end_date=None, machine=None, machines=None, plant=None, stop_class=None, stop_type=None):
    """
    Filter dataframe with multi-plant and multi-machine support.
    """
    filtered = df.copy()
    
    # Plant filter
    if plant and plant not in ["All Plants", "All Plants (Total)", "Both Plants"]:
        filtered = filtered[filtered["Plant"].str.lower() == str(plant).strip().lower()]
        
    # Date filter
    if start_date:
        filtered = filtered[filtered["Start Date"] >= pd.to_datetime(start_date)]
    if end_date:
        filtered = filtered[filtered["Start Date"] <= pd.to_datetime(end_date)]
        
    # Multi-machine fleet filter
    if machines and len(machines) > 0 and "All Machines" not in machines and "Whole Fleet" not in machines:
        filtered = filtered[filtered["Machine"].isin(machines)]
    elif machine and machine != "All Machines":
        filtered = filtered[filtered["Machine"].str.lower() == str(machine).strip().lower()]
        
    # Stoppage classifications
    if stop_class and stop_class != "All Classes":
        filtered = filtered[filtered["Class"].str.lower() == str(stop_class).strip().lower()]
    if stop_type and stop_type != "All Types":
        filtered = filtered[filtered["Type"].str.lower() == str(stop_type).strip().lower()]
        
    return filtered

def calculate_plant_kpis(df, start_date=None, end_date=None, machine=None, machines=None, plant=None):
    """
    Computes true operational KPIs with accurate calendar hours:
    - Active tracks = distinct (Plant, Machine) pairs in the evaluation scope
    - Calendar Hours = Unique Days * 24 * Active tracks
    - True Operating Run Time = Calendar Hours - Total Downtime
    - Operational Availability % = (True Operating Run Time / Calendar Hours) * 100
    - KPI Impacting Downtime = Sum of (Incidents + Circumstance)
    - Scheduled Downtime = Sum of Schedule
    """
    sub_df = filter_data(df, start_date=start_date, end_date=end_date, machine=machine, machines=machines, plant=plant)
    
    if sub_df.empty:
        return {
            "num_days": 0,
            "date_range": "No records",
            "total_stops": 0,
            "total_downtime_hours": 0.0,
            "true_runtime_hours": 0.0,
            "calendar_hours": 0.0,
            "availability_pct": 100.0,
            "kpi_downtime_hours": 0.0,
            "scheduled_downtime_hours": 0.0,
            "kpi_availability_pct": 100.0,
            "top_bottleneck_machine": "None",
            "top_reason": "None",
            "active_tracks": 0
        }
        
    min_date = pd.to_datetime(sub_df["Start Date"].min())
    max_date = pd.to_datetime(sub_df["Start Date"].max())
    num_days = max(1, (max_date - min_date).days + 1)
    
    # Calculate active equipment tracks
    # In multi-plant, e.g. Cleopatra Kiln and BMIC Kiln are 2 separate continuous operating tracks
    if "Plant" in sub_df.columns:
        num_tracks = max(1, sub_df.groupby(["Plant", "Machine"]).ngroups)
    else:
        num_tracks = max(1, len(sub_df["Machine"].unique()))
        
    total_calendar_hours = num_days * 24.0 * num_tracks
    total_downtime = float(sub_df["Duration"].sum())
    
    true_runtime = max(0.0, total_calendar_hours - total_downtime)
    availability = (true_runtime / total_calendar_hours * 100.0) if total_calendar_hours > 0 else 0.0
    
    if "Affects_KPI" not in sub_df.columns:
        sub_df["Affects_KPI"] = sub_df["Class"].isin(["Incidents", "Circumstance"])
        
    kpi_downtime = float(sub_df[sub_df["Affects_KPI"]]["Duration"].sum())
    scheduled_downtime = float(sub_df[sub_df["Class"] == "Schedule"]["Duration"].sum())
    kpi_availability = max(0.0, (total_calendar_hours - kpi_downtime) / total_calendar_hours * 100.0) if total_calendar_hours > 0 else 0.0
    
    # Top bottleneck machine
    group_col = ["Plant", "Machine"] if ("Plant" in sub_df.columns and len(sub_df["Plant"].unique()) > 1) else ["Machine"]
    machine_loss = sub_df.groupby(group_col)["Duration"].sum()
    if not machine_loss.empty:
        top_idx = machine_loss.idxmax()
        top_m_name = f"{top_idx[0]} - {top_idx[1]}" if isinstance(top_idx, tuple) else str(top_idx)
        top_machine_loss = machine_loss.max()
    else:
        top_m_name = "None"
        top_machine_loss = 0.0
    
    # Top stop reason
    reason_loss = sub_df.groupby("Reason for downtime")["Duration"].sum()
    top_reason = reason_loss.idxmax() if not reason_loss.empty else "None"
    top_reason_hrs = reason_loss.max() if not reason_loss.empty else 0.0
    
    return {
        "num_days": num_days,
        "date_range": f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}",
        "total_stops": len(sub_df),
        "total_downtime_hours": round(total_downtime, 2),
        "true_runtime_hours": round(true_runtime, 2),
        "calendar_hours": round(total_calendar_hours, 2),
        "availability_pct": round(availability, 1),
        "kpi_downtime_hours": round(kpi_downtime, 2),
        "scheduled_downtime_hours": round(scheduled_downtime, 2),
        "kpi_availability_pct": round(kpi_availability, 1),
        "top_bottleneck_machine": f"{top_m_name} ({top_machine_loss:.1f} hrs lost)",
        "top_reason": f"{top_reason} ({top_reason_hrs:.1f} hrs)",
        "active_tracks": num_tracks
    }

def get_machine_summary_table(df, start_date=None, end_date=None, plant=None, machines=None):
    """
    Returns breakdown per machine with Plant context.
    """
    sub_df = filter_data(df, start_date=start_date, end_date=end_date, plant=plant, machines=machines)
    if sub_df.empty:
        return pd.DataFrame()
        
    min_date = pd.to_datetime(sub_df["Start Date"].min())
    max_date = pd.to_datetime(sub_df["Start Date"].max())
    num_days = max(1, (max_date - min_date).days + 1)
    cal_hours_per_machine = num_days * 24.0
    
    has_multi_plants = "Plant" in sub_df.columns and len(sub_df["Plant"].unique()) > 1
    group_cols = ["Plant", "Machine"] if "Plant" in sub_df.columns else ["Machine"]
    
    records = []
    for grp_keys, grp_df in sub_df.groupby(group_cols):
        p_name = grp_keys[0] if isinstance(grp_keys, tuple) else (sub_df["Plant"].iloc[0] if "Plant" in sub_df.columns else "Plant")
        m_name = grp_keys[1] if isinstance(grp_keys, tuple) else grp_keys
        
        tot_stops = len(grp_df)
        tot_downtime = grp_df["Duration"].sum()
        true_run = max(0.0, cal_hours_per_machine - tot_downtime)
        avail = (true_run / cal_hours_per_machine * 100.0)
        
        incidents_dur = grp_df[grp_df["Affects_KPI"]]["Duration"].sum()
        sched_dur = grp_df[grp_df["Class"] == "Schedule"]["Duration"].sum()
        
        rec = {
            "Machine": m_name,
            "Total Stops": tot_stops,
            "Total Downtime (hrs)": round(tot_downtime, 2),
            "True Run Time (hrs)": round(true_run, 2),
            "Availability %": round(avail, 1),
            "Incident Downtime (hrs)": round(incidents_dur, 2),
            "Schedule Downtime (hrs)": round(sched_dur, 2)
        }
        if has_multi_plants:
            rec["Plant"] = p_name
            
        records.append(rec)
        
    res_df = pd.DataFrame(records)
    if has_multi_plants:
        res_df = res_df[["Plant", "Machine", "Total Stops", "Total Downtime (hrs)", "True Run Time (hrs)", "Availability %", "Incident Downtime (hrs)", "Schedule Downtime (hrs)"]]
    res_df = res_df.sort_values(by="Total Downtime (hrs)", ascending=False).reset_index(drop=True)
    return res_df

def get_pareto_analysis(df, machine=None, machines=None, plant=None, top_n=10):
    """
    Calculates Pareto breakdown of downtime causes with multi-plant support.
    """
    sub_df = filter_data(df, machine=machine, machines=machines, plant=plant)
    if sub_df.empty:
        return pd.DataFrame()
        
    grouped = sub_df.groupby("Reason for downtime").agg(
        Stop_Count=("Duration", "count"),
        Total_Hours=("Duration", "sum")
    ).reset_index()
    
    grouped = grouped.sort_values(by="Total_Hours", ascending=False).reset_index(drop=True)
    total_hours = grouped["Total_Hours"].sum()
    
    grouped["Share_%"] = (grouped["Total_Hours"] / total_hours * 100.0).round(1) if total_hours > 0 else 0.0
    grouped["Cumulative_%"] = grouped["Share_%"].cumsum().round(1)
    grouped["Total_Hours"] = grouped["Total_Hours"].round(2)
    
    return grouped.head(top_n)

def get_downtime_by_category(df, machine=None, machines=None, plant=None):
    """
    Returns breakdown by Class and Type with multi-plant support.
    """
    sub_df = filter_data(df, machine=machine, machines=machines, plant=plant)
    if sub_df.empty:
        return pd.DataFrame()
        
    grouped = sub_df.groupby(["Class", "Type"]).agg(
        Stops=("Duration", "count"),
        Hours=("Duration", "sum")
    ).reset_index()
    grouped["Hours"] = grouped["Hours"].round(2)
    grouped = grouped.sort_values(by="Hours", ascending=False)
    return grouped

def get_monthly_trend(df, machine=None, machines=None, plant=None):
    """
    Returns monthly timeline of Downtime and Operating Hours.
    """
    sub_df = filter_data(df, machine=machine, machines=machines, plant=plant).copy()
    if sub_df.empty:
        return pd.DataFrame()
        
    sub_df["YearMonth"] = sub_df["Start Date"].dt.to_period("M").astype(str)
    
    grouped = sub_df.groupby("YearMonth").agg(
        Total_Stops=("Duration", "count"),
        Total_Downtime=("Duration", "sum"),
        Incident_Downtime=("Duration", lambda x: sub_df.loc[x.index][sub_df.loc[x.index, "Affects_KPI"]]["Duration"].sum()),
        Schedule_Downtime=("Duration", lambda x: sub_df.loc[x.index][sub_df.loc[x.index, "Class"] == "Schedule"]["Duration"].sum())
    ).reset_index()
    
    grouped["Total_Downtime"] = grouped["Total_Downtime"].round(2)
    grouped["Incident_Downtime"] = grouped["Incident_Downtime"].round(2)
    grouped["Schedule_Downtime"] = grouped["Schedule_Downtime"].round(2)
    return grouped
