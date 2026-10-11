"""
Conversational Guardrail AI Agent for Multi-Plant Cement Stoppages.
Supports:
- Cleopatra Plant & BMIC Plant (and All Plants Combined).
- Multi-turn conversational flow, entity resolution, and plant awareness.
- Offline deterministic calculation + Google Gemini live synthesis.
"""
import re
import os
from datetime import datetime
import pandas as pd
from analytics import (
    filter_data,
    calculate_plant_kpis,
    get_machine_summary_table,
    get_pareto_analysis,
    get_downtime_by_category,
    get_monthly_trend
)

# Core plant terminology
SCOPE_KEYWORDS = [
    "stop", "downtime", "breakdown", "fault", "trip", "incident", "schedule",
    "circumstance", "maintenance", "repair", "availability", "kpi", "run time",
    "runtime", "operating", "hours", "duration", "machine", "equipment", "plant",
    "plants", "cleopatra", "bmic", "coal mill", "coal", "sand mill", "raw mill",
    "kiln", "mill", "crusher", "cooler", "preheater", "cement mill", "mechanical",
    "electrical", "production", "reason", "cause", "pareto", "month", "year",
    "september", "october", "august", "trend", "summary", "filter", "pump", "gear",
    "girth", "bearing", "motor", "vfd", "hopper", "silo", "feeder", "cyclone",
    "calciner", "roller", "c4", "fl", "pm", "drift", "fleet"
]

CONVERSATIONAL_FOLLOWUPS = [
    "what about", "why", "how about", "tell me more", "explain", "which one",
    "compare", "how many", "show me", "details", "breakdown", "what was",
    "how long", "elaborate", "summarize", "list", "causes", "reasons",
    "dates", "when", "second", "first", "third", "longest", "worst",
    "highest", "lowest", "more", "less", "difference", "versus", "vs",
    "august", "september", "october", "november", "december", "january",
    "february", "march", "april", "may", "june", "july", "2025", "2026",
    "can you", "and", "is there", "what happened", "occur", "severe", "most",
    "that", "these", "those", "it", "them", "both", "either", "total"
]

OUT_OF_SCOPE_MESSAGE = (
    "⚠️ **Operational Scope Lock**\n\n"
    "I am strictly configured as the **Cement Plant Operations & Reliability Assistant** for **Cleopatra & BMIC Plants**.\n"
    "I can only assist with questions regarding plant machinery downtime, operational stop causes, "
    "equipment availability, and maintenance incident data.\n\n"
    "*Examples of questions you can ask me:*\n"
    "- *'What is the overall availability for Cleopatra Plant vs BMIC Plant?'*\n"
    "- *'Top 5 causes for Kiln downtime in Cleopatra?'*\n"
    "- *'How many hours did Coal Mill lose in BMIC Plant?'*\n"
    "- *'Compare Electrical vs Mechanical stops across both plants.'*\n"
    "- *'Which machine has the lowest availability in the entire fleet?'*"
)

def is_query_in_scope(user_query: str, chat_history: list = None) -> bool:
    """Checks if user's question is within cement plant stoppage scope."""
    q = user_query.lower().strip()
    if len(q) < 2:
        return False
        
    disallowed_topics = [
        "recipe", "weather", "poem", "joke", "politics", "president", "sports",
        "movie", "song", "translate", "capital of", "who are you", "write code for website",
        "stock price", "crypto", "bitcoin", "horoscope", "cook", "pasta", "pizza",
        "bake", "cake", "food", "game", "football", "soccer", "basketball"
    ]
    for bad in disallowed_topics:
        if bad in q:
            return False
            
    # Direct plant keyword match
    for kw in SCOPE_KEYWORDS:
        if kw in q:
            return True

    # Multi-turn conversational follow-up check:
    if chat_history and len(chat_history) > 1:
        for trigger in CONVERSATIONAL_FOLLOWUPS:
            if trigger in q:
                return True
            
    return False

def extract_target_plant(query_lower: str, chat_history: list = None, default_plant: str = None) -> str:
    """Extracts plant context (Cleopatra Plant, BMIC Plant, or All Plants)."""
    if "cleopatra" in query_lower:
        return "Cleopatra Plant"
    elif "bmic" in query_lower:
        return "BMIC Plant"
    elif any(k in query_lower for k in ["both plants", "all plants", "total plants", "across plants", "whole company"]):
        return "All Plants"

    # Check chat history backwards
    if chat_history:
        for msg in reversed(chat_history):
            c_low = msg.get("content", "").lower()
            if "cleopatra" in c_low:
                return "Cleopatra Plant"
            elif "bmic" in c_low:
                return "BMIC Plant"

    return default_plant or "All Plants"

def extract_target_machine(query_lower: str, chat_history: list = None, df_machines: list = None) -> str:
    """Extracts machine name from current query, or inherits from previous turns."""
    aliases = {
        "cement mill a": "W.CEMENT MILL (A)",
        "mill a": "W.CEMENT MILL (A)",
        "cement mill b": "W.CEMENT MILL (B)",
        "mill b": "W.CEMENT MILL (B)",
        "coal mill": "Coal mill",
        "coal": "Coal mill",
        "sand mill": "Sand mill",
        "sand": "Sand mill",
        "raw mill": "Raw mill",
        "raw": "Raw mill",
        "kiln": "Kiln",
        "crusher": "Crusher"
    }
    
    for alias, machine_name in aliases.items():
        if alias in query_lower:
            return machine_name

    if df_machines:
        for m in df_machines:
            if m.lower() in query_lower:
                return m

    # Inherit from chat history
    if chat_history:
        for msg in reversed(chat_history):
            content_low = msg.get("content", "").lower()
            for alias, machine_name in aliases.items():
                if alias in content_low or machine_name.lower() in content_low:
                    return machine_name

    return None

def extract_date_range(query_lower: str, chat_history: list = None):
    """Extracts date range from current query or previous conversation turns."""
    month_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    for m_name, m_num in month_map.items():
        if m_name in query_lower:
            year = 2026 if "2026" in query_lower else 2025 if "2025" in query_lower else 2026
            start_date = f"{year}-{m_num:02d}-01"
            if m_num in [1, 3, 5, 7, 8, 10, 12]:
                end_date = f"{year}-{m_num:02d}-31"
            elif m_num == 2:
                end_date = f"{year}-02-28"
            else:
                end_date = f"{year}-{m_num:02d}-30"
            return start_date, end_date

    if "2025" in query_lower and "2026" not in query_lower:
        return "2025-01-01", "2025-12-31"
    if "2026" in query_lower and "2025" not in query_lower:
        return "2026-01-01", "2026-10-10"

    if chat_history:
        for msg in reversed(chat_history):
            c_low = msg.get("content", "").lower()
            for m_name, m_num in month_map.items():
                if m_name in c_low:
                    year = 2026 if "2026" in c_low else 2025 if "2025" in c_low else 2026
                    start_date = f"{year}-{m_num:02d}-01"
                    if m_num in [1, 3, 5, 7, 8, 10, 12]:
                        end_date = f"{year}-{m_num:02d}-31"
                    elif m_num == 2:
                        end_date = f"{year}-02-28"
                    else:
                        end_date = f"{year}-{m_num:02d}-30"
                    return start_date, end_date

    return None, None

def answer_query(user_query: str, df: pd.DataFrame, api_key: str = None, chosen_model: str = "auto", chat_history: list = None, default_plant: str = None, active_machines: list = None) -> str:
    """
    Main entrypoint for answering multi-plant questions with full conversational memory.
    """
    # 1. Scope Enforcement Guardrail
    if not is_query_in_scope(user_query, chat_history=chat_history):
        return OUT_OF_SCOPE_MESSAGE

    q_lower = user_query.lower()
    all_machines = list(df["Machine"].unique())
    
    # 2. Extract / Inherit Plant, Machine, Date Filters
    target_plant = extract_target_plant(q_lower, chat_history=chat_history, default_plant=default_plant)
    target_machine = extract_target_machine(q_lower, chat_history=chat_history, df_machines=all_machines)
    start_date, end_date = extract_date_range(q_lower, chat_history=chat_history)

    # 3. Compute Deterministic Ground-Truth Facts
    kpis = calculate_plant_kpis(df, start_date=start_date, end_date=end_date, machine=target_machine, machines=active_machines, plant=target_plant)
    machine_summary = get_machine_summary_table(df, start_date=start_date, end_date=end_date, plant=target_plant, machines=active_machines)
    pareto_reasons = get_pareto_analysis(df, machine=target_machine, machines=active_machines, plant=target_plant, top_n=6)
    category_breakdown = get_downtime_by_category(df, machine=target_machine, machines=active_machines, plant=target_plant)

    # 4. Extract specific drill-down rows if a failure reason is mentioned
    drilldown_df = pd.DataFrame()
    if target_machine:
        sub_df = filter_data(df, plant=target_plant, machine=target_machine)
        for _, row_r in pareto_reasons.iterrows():
            reason_str = str(row_r["Reason for downtime"]).lower()
            words = [w for w in reason_str.split() if len(w) > 3 and w not in ["check", "request", "instructions"]]
            if any(w in q_lower for w in words):
                drilldown_df = sub_df[sub_df["Reason for downtime"] == row_r["Reason for downtime"]].sort_values(by="Duration", ascending=False).head(5)
                break

    # 5. Live Synthesis with Google Gemini (Multi-Turn)
    if api_key:
        try:
            return synthesize_with_llm(
                user_query, df, kpis, machine_summary, pareto_reasons,
                category_breakdown, target_machine, target_plant, api_key,
                chosen_model=chosen_model, chat_history=chat_history,
                drilldown_df=drilldown_df
            )
        except Exception as e:
            err_notice = f"> ⚠️ **Google Gemini API Notice:** `{str(e)}`\n> *Falling back to the built-in deterministic engine below:*\n\n"
            return err_notice + synthesize_deterministic_response(user_query, kpis, machine_summary, pareto_reasons, category_breakdown, target_machine, target_plant, start_date, end_date, drilldown_df=drilldown_df)

    # 6. Built-in Deterministic Engine Response
    return synthesize_deterministic_response(user_query, kpis, machine_summary, pareto_reasons, category_breakdown, target_machine, target_plant, start_date, end_date, drilldown_df=drilldown_df)

def synthesize_deterministic_response(query, kpis, machine_summary, pareto, cat_breakdown, target_machine, target_plant, start_date, end_date, drilldown_df=None):
    """Generates an executive-level, mathematically sound markdown report with multi-plant context."""
    q_low = query.lower()
    plant_label = f"[{target_plant}] " if target_plant != "All Plants" else "[All Plants] "
    scope_target = f"for **{target_machine}** ({target_plant})" if target_machine else f"across **{target_plant}**"
    date_note = f"in {kpis.get('date_range', '')}" if start_date else f"over the full recording period ({kpis.get('date_range', '')})"

    # Drill-down on specific failure entries
    if drilldown_df is not None and not drilldown_df.empty:
        reason_name = drilldown_df.iloc[0]["Reason for downtime"]
        response = f"### 🔍 Detailed Incident Log {scope_target}\n\n"
        response += f"Specific records for stoppage cause: **\"{reason_name}\"**:\n\n"
        response += "| Plant | Date | Time | Duration | Class | Type | Log Description |\n"
        response += "| :--- | :--- | :--- | :---: | :--- | :--- | :--- |\n"
        for _, r in drilldown_df.iterrows():
            st_time = f"{r.get('Start Time', '—')} to {r.get('End Time', '—')}"
            plant_name = r.get('Plant', target_plant)
            d_str = r['Start Date'].strftime('%Y-%m-%d') if hasattr(r['Start Date'], 'strftime') else r['Start Date']
            response += f"| {plant_name} | {d_str} | {st_time} | **{r['Duration']:.2f}h** | {r['Class']} | {r['Type']} | {r['Reason for downtime']} |\n"
        tot_reason_hrs = drilldown_df['Duration'].sum()
        response += f"\n> **Occurrences:** Showing top {len(drilldown_df)} longest events totaling **{tot_reason_hrs:.2f} hours**.\n"
        return response

    # Top causes / Pareto
    if any(k in q_low for k in ["top", "reason", "cause", "pareto", "why", "root cause", "second", "third", "longest", "worst", "severe"]):
        response = f"### 📊 Downtime Root Cause Analysis {scope_target}\n\n"
        response += f"Based on plant stoppage records {date_note}:\n\n"
        if not pareto.empty:
            response += "| Stoppage Reason | Stop Count | Total Lost Hours | Share % | Cumulative % |\n"
            response += "| :--- | :---: | :---: | :---: | :---: |\n"
            for _, row in pareto.iterrows():
                response += f"| **{row['Reason for downtime']}** | {row['Stop_Count']} | {row['Total_Hours']:.2f} hrs | {row['Share_%']}% | {row['Cumulative_%']}% |\n"
            
            top_cause = pareto.iloc[0]
            response += f"\n> **Key Takeaway:** The leading stoppage cause in this scope is **\"{top_cause['Reason for downtime']}\"**, responsible for **{top_cause['Total_Hours']:.1f} hours** ({top_cause['Share_%']}% of downtime).\n"
        else:
            response += "No stoppage records matching this criteria."
        return response

    # Comparison / Fleet breakdown / Ranking
    if any(k in q_low for k in ["compare", "which machine", "bottleneck", "worst", "ranking", "fleet", "lowest", "between"]):
        response = f"### 🏭 Equipment Downtime & Availability Summary {scope_target}\n\n"
        response += f"Summary {date_note}:\n\n"
        if not machine_summary.empty:
            has_plant_col = "Plant" in machine_summary.columns
            if has_plant_col:
                response += "| Plant | Machine | Total Stops | Total Lost (hrs) | True Run Time (hrs) | Availability % | Incident Downtime (hrs) | Schedule (hrs) |\n"
                response += "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n"
                for _, row in machine_summary.iterrows():
                    response += f"| {row['Plant']} | **{row['Machine']}** | {row['Total Stops']} | {row['Total Downtime (hrs)']:.1f} | {row['True Run Time (hrs)']:.1f} | **{row['Availability %']}%** | {row['Incident Downtime (hrs)']:.1f} | {row['Schedule Downtime (hrs)']:.1f} |\n"
            else:
                response += "| Machine | Total Stops | Total Lost (hrs) | True Run Time (hrs) | Availability % | Incident Downtime (hrs) | Schedule (hrs) |\n"
                response += "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n"
                for _, row in machine_summary.iterrows():
                    response += f"| **{row['Machine']}** | {row['Total Stops']} | {row['Total Downtime (hrs)']:.1f} | {row['True Run Time (hrs)']:.1f} | **{row['Availability %']}%** | {row['Incident Downtime (hrs)']:.1f} | {row['Schedule Downtime (hrs)']:.1f} |\n"
            
            top_m = machine_summary.iloc[0]
            m_label = f"{top_m.get('Plant', '')} {top_m['Machine']}".strip()
            response += f"\n> **Observation:** **{m_label}** recorded the highest downtime with **{top_m['Total Downtime (hrs)']:.1f} hours** lost ({top_m['Availability %']}% availability).\n"
        return response

    # Stoppage Classification (Electrical vs Mechanical vs Production)
    if any(k in q_low for k in ["electrical", "mechanical", "production", "incident", "type", "class", "circumstance"]):
        response = f"### ⚙️ Stoppage Classification Breakdown {scope_target}\n\n"
        response += f"Analysis {date_note}:\n\n"
        if not cat_breakdown.empty:
            response += "| Class | Sub-Type | Stop Count | Lost Duration (hrs) |\n"
            response += "| :--- | :--- | :---: | :---: |\n"
            for _, row in cat_breakdown.iterrows():
                response += f"| {row['Class']} | **{row['Type']}** | {row['Stops']} | {row['Hours']:.2f} hrs |\n"
                
            inc_hrs = kpis["kpi_downtime_hours"]
            sch_hrs = kpis["scheduled_downtime_hours"]
            response += f"\n- **Unplanned / KPI Loss:** `{inc_hrs:.1f} hrs` (Incidents + Circumstances)\n"
            response += f"- **Scheduled Maintenance:** `{sch_hrs:.1f} hrs` (Planned overhauls & inspections)\n"
        return response

    # Default Brief
    response = f"### 📋 Operations Stoppage & Reliability Brief {scope_target}\n\n"
    response += f"Operational metrics {date_note}:\n\n"
    response += f"- **Evaluated Plant Scope:** `{target_plant}`\n"
    response += f"- **Total Stoppage Events:** `{kpis['total_stops']} stops`\n"
    response += f"- **Total Downtime Hours:** `{kpis['total_downtime_hours']} hrs`\n"
    response += f"- **Reconstructed True Operating Run Time:** `{kpis['true_runtime_hours']} hrs`\n"
    response += f"- **Overall Operational Availability:** `{kpis['availability_pct']}%`\n"
    response += f"- **Unplanned Downtime (Incidents & Circumstance):** `{kpis['kpi_downtime_hours']} hrs`\n"
    response += f"- **Scheduled Maintenance:** `{kpis['scheduled_downtime_hours']} hrs`\n"
    response += f"- **Leading Bottleneck Equipment:** `{kpis['top_bottleneck_machine']}`\n"
    response += f"- **Top Stoppage Cause:** `{kpis['top_reason']}`\n\n"
    
    if not pareto.empty:
        response += "#### Leading Downtime Drivers:\n"
        for i, row in pareto.head(3).iterrows():
            response += f"{i+1}. **{row['Reason for downtime']}** — {row['Total_Hours']:.1f} hrs ({row['Share_%']}%)\n"
            
    return response

def synthesize_with_llm(query, df, kpis, machine_summary, pareto, cat_breakdown, target_machine, target_plant, api_key, chosen_model="auto", chat_history=None, drilldown_df=None):
    """Uses Google Gemini with multi-turn conversation memory and verified multi-plant data."""
    history_transcript = ""
    if chat_history and len(chat_history) > 1:
        recent = [m for m in chat_history[1:] if m.get("content")][-4:]
        for m in recent:
            role = "User" if m["role"] == "user" else "Assistant"
            clean_content = m["content"].split("\n---\n*✨")[0].strip()
            history_transcript += f"[{role}]: {clean_content}\n\n"

    drilldown_str = ""
    if drilldown_df is not None and not drilldown_df.empty:
        drilldown_str = "SPECIFIC INCIDENT RECORDS:\n" + drilldown_df.to_string(index=False) + "\n"

    system_prompt = f"""You are the Cement Plant Operations Downtime & Reliability Assistant for Cleopatra Plant and BMIC Plant.
You are in an ongoing conversation with plant operations management, reliability engineers, and executive leadership.
You must strictly base your response ONLY on the verified stoppage data below.
DO NOT fabricate numbers. Use the exact figures provided.
Note: Cleopatra Plant has a Sand Mill, whereas BMIC Plant does NOT have a Sand Mill and instead operates a Coal Mill.

CONVERSATION CONTEXT SO FAR:
{history_transcript if history_transcript else 'No previous conversation turns.'}

VERIFIED PLANT METRICS FOR CURRENT CONTEXT:
Plant Scope: {target_plant}
Target Machine: {target_machine or 'All Fleet Machines in Scope'}
Date Range: {kpis.get('date_range')}
Total Stops: {kpis.get('total_stops')}
Total Downtime (hrs): {kpis.get('total_downtime_hours')}
True Operating Run Time (hrs): {kpis.get('true_runtime_hours')}
Availability (%): {kpis.get('availability_pct')}%
Unplanned Loss (Incidents & Circumstance): {kpis.get('kpi_downtime_hours')} hrs
Scheduled Maintenance: {kpis.get('scheduled_downtime_hours')} hrs

TOP STOPPAGE REASONS:
{pareto.to_string(index=False) if not pareto.empty else 'N/A'}

FLEET / PLANT COMPARISON:
{machine_summary.to_string(index=False) if not machine_summary.empty else 'N/A'}

CATEGORY BREAKDOWN:
{cat_breakdown.to_string(index=False) if not cat_breakdown.empty else 'N/A'}

{drilldown_str}

Format your answer professionally in markdown with bullet points and clear operational takeaways."""

    full_prompt = f"{system_prompt}\n\nLATEST USER QUESTION / FOLLOW-UP: {query}"
    
    candidates = [chosen_model] if (chosen_model and chosen_model != "auto") else [
        "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro"
    ]

    try:
        from google import genai
        client = genai.Client(api_key=api_key.strip())
        last_err = None
        for m in candidates:
            try:
                response = client.models.generate_content(model=m, contents=full_prompt)
                if response and response.text:
                    return response.text + f"\n\n---\n*✨ Synthesized live using Google Gemini ({m}) via Google AI Studio*"
            except Exception as err:
                last_err = err
                continue
    except Exception as e:
        last_err = e

    try:
        import google.generativeai as legacy_genai
        legacy_genai.configure(api_key=api_key.strip())
        for m in candidates:
            try:
                model = legacy_genai.GenerativeModel(m)
                response = model.generate_content(full_prompt)
                if response and response.text:
                    return response.text + f"\n\n---\n*✨ Synthesized live using Google Gemini ({m}) via Google AI Studio*"
            except Exception as err:
                last_err = err
                continue
    except Exception as e:
        last_err = e

    raise RuntimeError(f"Gemini API returned: {last_err}")
