"""
OPIQ — Cement Operations Intelligence Platform
Clean Enterprise Light Theme:
- Fully aligned with Streamlit light mode config.
- Crisp high-contrast typography (#0F172A / #334155).
- All white/off-white surfaces (#FFFFFF / #F8FAFC) with slate borders (#E2E8F0).
- Zero black elements, zero invisible text.
- Cleopatra Plant, BMIC Plant, All Plants (Total).
- Dynamic Fleet Filter for KPI cards.
- Sticky bottom chat input with auto-scroll and multi-turn memory.
"""
import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from analytics import (
    calculate_plant_kpis,
    get_downtime_by_category,
    get_machine_summary_table,
    get_monthly_trend,
    get_pareto_analysis,
    load_and_preprocess_data,
    filter_data,
)
from agent import answer_query

# ═══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="OPIQ · Plant Intelligence",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
# CLEAN ENTERPRISE LIGHT DESIGN SYSTEM (FULLY RESPONSIVE)
# ═══════════════════════════════════════════════════════════════
st.markdown(
    """
<style>
/* ── Base Fonts & Canvas ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    color: #0F172A !important;
    max-width: 100vw !important;
}

/* ── Streamlit Chrome & Header (Clean floating toggle, no white blocker) ── */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] {
    background: transparent !important;
    border: none !important;
    height: 40px !important;
    z-index: 1000 !important;
}
header[data-testid="stHeader"] [data-testid="stToolbar"] {
    display: none !important;
}
header[data-testid="stHeader"] button,
header[data-testid="stHeader"] [data-testid="stSidebarCollapseButton"] {
    color: #0F172A !important;
    fill: #0F172A !important;
}

.stApp {
    background-color: #F8FAFC !important;
    color: #0F172A !important;
    max-width: 100vw !important;
}

/* ── Container Spacing & Responsiveness ── */
.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 6rem !important;
}
@media (max-width: 768px) {
    .block-container {
        padding-top: 3.2rem !important; /* Clears floating header so logo and title are 100% visible */
        padding-bottom: 5.5rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }
}

/* ── Sidebar (Clean Drawer on Mobile, Fixed on Desktop) ── */
section[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #E2E8F0 !important;
    box-shadow: 2px 0 12px rgba(0, 0, 0, 0.04) !important;
}
@media (min-width: 769px) {
    section[data-testid="stSidebar"] {
        min-width: 280px !important;
        max-width: 280px !important;
    }
}
section[data-testid="stSidebar"] * {
    color: #334155 !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #334155 !important;
}

/* ── Top Brand Bar ── */
.brand-bar {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 0 12px 0;
    border-bottom: 1px solid #E2E8F0;
    margin-bottom: 16px;
}
.brand-title {
    font-size: 1.45rem;
    font-weight: 700;
    color: #0F172A !important;
    margin: 0;
    letter-spacing: -0.3px;
}
.brand-sub {
    font-size: 0.72rem;
    color: #64748B !important;
    margin: 0;
    letter-spacing: 0.6px;
    text-transform: uppercase;
}
.live-pill {
    margin-left: auto;
    background: #ECFDF5;
    color: #059669 !important;
    border: 1px solid #A7F3D0;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 4px 12px;
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
    flex-shrink: 0;
}
.live-dot {
    width: 6px;
    height: 6px;
    background: #10B981;
    border-radius: 50%;
    animation: blink 1.8s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0.25;} }

@media (max-width: 768px) {
    .brand-bar {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 8px !important;
        padding: 8px 0 10px 0 !important;
        margin-bottom: 12px !important;
    }
    .brand-title {
        font-size: 1.15rem !important;
        line-height: 1.25 !important;
    }
    .brand-sub {
        font-size: 0.65rem !important;
    }
    .live-pill {
        margin-left: 0 !important;
        font-size: 0.64rem !important;
        padding: 2px 8px !important;
    }
}

/* ── Status Ribbon ── */
.chat-status-ribbon {
    display: flex;
    align-items: center;
    gap: 16px;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 10px 18px;
    margin-bottom: 14px;
    font-size: 0.8rem;
    color: #475569 !important;
    flex-wrap: wrap;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.chat-status-item {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #475569 !important;
}
.chat-status-val {
    color: #0F172A !important;
    font-weight: 700;
}
@media (max-width: 768px) {
    .chat-status-ribbon {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 6px 12px !important;
        padding: 8px 12px !important;
        font-size: 0.72rem !important;
        margin-bottom: 10px !important;
    }
    .chat-status-item {
        font-size: 0.72rem !important;
        display: flex !important;
        justify-content: space-between !important;
        gap: 4px !important;
    }
    .chat-status-item[style*="margin-left:auto"] {
        margin-left: 0 !important;
    }
}

/* ── KPI Cards ── */
.kpi-row {
    display: flex;
    gap: 14px;
    margin-bottom: 22px;
    flex-wrap: wrap;
}
.kpi-card {
    flex: 1;
    min-width: 170px;
    height: 110px;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 14px 18px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.kpi-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
}
.kc-blue::after   { background: linear-gradient(90deg, #2563EB, #60A5FA); }
.kc-teal::after   { background: linear-gradient(90deg, #0891B2, #22D3EE); }
.kc-green::after  { background: linear-gradient(90deg, #059669, #34D399); }
.kc-amber::after  { background: linear-gradient(90deg, #D97706, #FCD34D); }
.kc-violet::after { background: linear-gradient(90deg, #7C3AED, #A78BFA); }
.kpi-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #64748B !important;
    letter-spacing: 0.7px;
    text-transform: uppercase;
}
.kpi-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #0F172A !important;
    line-height: 1.1;
}
.kpi-sub {
    font-size: 0.72rem;
    color: #64748B !important;
}

@media (max-width: 768px) {
    .kpi-row {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 8px !important;
        margin-bottom: 14px !important;
    }
    .kpi-card {
        min-width: 0 !important;
        height: auto !important;
        min-height: 86px !important;
        padding: 10px 12px !important;
    }
    .kpi-card:last-child {
        grid-column: span 2 !important;
    }
    .kpi-label {
        font-size: 0.62rem !important;
        letter-spacing: 0.3px !important;
    }
    .kpi-value {
        font-size: 1.25rem !important;
        margin: 3px 0 !important;
    }
    .kpi-sub {
        font-size: 0.65rem !important;
    }
}

/* ── Operational Scope Notice ── */
.gr-bar {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-left: 4px solid #2563EB;
    border-radius: 8px;
    padding: 10px 16px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 14px;
}
.gr-text {
    font-size: 0.8rem;
    color: #1E40AF !important;
    line-height: 1.5;
}
@media (max-width: 768px) {
    .gr-bar {
        padding: 8px 12px !important;
        font-size: 0.74rem !important;
    }
    .gr-text {
        font-size: 0.74rem !important;
    }
}

/* ── Section Dividers ── */
.sec-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #475569 !important;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 22px 0 12px;
}
.sec-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #E2E8F0;
}

/* ── Segmented Control (Light Mode Unified Pill Container) ── */
[data-testid="stSegmentedControl"] {
    background: #F1F5F9 !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    padding: 3px !important;
}

/* Desktop: elegant, well-proportioned tab bar */
@media (min-width: 769px) {
    [data-testid="stSegmentedControl"] {
        display: inline-flex !important;
        width: auto !important;
        min-width: 440px !important;
    }
    [data-testid="stSegmentedControl"] [role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 6px !important;
    }
    [data-testid="stSegmentedControl"] button,
    [data-testid="stSegmentedControl"] [role="radio"] {
        padding: 7px 22px !important;
        font-size: 0.86rem !important;
        font-weight: 500 !important;
    }
}

/* Mobile: strictly 1 row with 3 equal columns, never wrapping */
@media (max-width: 768px) {
    [data-testid="stSegmentedControl"] {
        width: 100% !important;
        display: block !important;
        padding: 2px !important;
    }
    [data-testid="stSegmentedControl"] [role="radiogroup"],
    [data-testid="stSegmentedControl"] > div {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        width: 100% !important;
        gap: 2px !important;
    }
    [data-testid="stSegmentedControl"] [role="radiogroup"] > div,
    [data-testid="stSegmentedControl"] > div > div {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        display: flex !important;
    }
    [data-testid="stSegmentedControl"] button,
    [data-testid="stSegmentedControl"] [role="radio"] {
        width: 100% !important;
        flex: 1 1 0 !important;
        min-width: 0 !important;
        padding: 6px 2px !important;
        font-size: 0.73rem !important;
        white-space: nowrap !important;
        text-align: center !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
}

[data-testid="stSegmentedControl"] button,
[data-testid="stSegmentedControl"] [role="radio"] {
    background: transparent !important;
    border: none !important;
    border-radius: 7px !important;
    color: #475569 !important;
    box-shadow: none !important;
    transition: all 0.15s !important;
}
[data-testid="stSegmentedControl"] button[aria-selected="true"],
[data-testid="stSegmentedControl"] [role="radio"][aria-checked="true"] {
    background: #FFFFFF !important;
    color: #0F172A !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
}

/* ── Radio Buttons (Ensures Crisp Dark Labels) ── */
[data-testid="stRadio"] label, [data-testid="stRadio"] p, [data-testid="stRadio"] span {
    color: #0F172A !important;
    font-weight: 500 !important;
}

/* ── Suggestion Pills (Light Mode Override & Swipeable Row on Mobile) ── */
[data-testid="stPills"] {
    background: transparent !important;
}
[data-testid="stPills"] button {
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 20px !important;
    color: #2563EB !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
    transition: all 0.15s !important;
}
[data-testid="stPills"] button:hover {
    background: #EFF6FF !important;
    border-color: #2563EB !important;
    color: #1D4ED8 !important;
}
[data-testid="stPills"] button[aria-selected="true"] {
    background: #2563EB !important;
    border-color: #2563EB !important;
    color: #FFFFFF !important;
}
@media (max-width: 768px) {
    [data-testid="stPills"] {
        overflow-x: auto !important;
        display: flex !important;
        flex-wrap: nowrap !important;
        -webkit-overflow-scrolling: touch !important;
        scrollbar-width: none !important;
        padding-bottom: 4px !important;
        margin-bottom: 6px !important;
        width: 100% !important;
    }
    [data-testid="stPills"]::-webkit-scrollbar {
        display: none !important;
    }
    [data-testid="stPills"] button {
        font-size: 0.74rem !important;
        padding: 5px 12px !important;
        white-space: nowrap !important;
        flex-shrink: 0 !important;
    }
}

/* ── Chat Messages ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 6px 0 !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stChatMessageContent,
[data-testid="stChatMessage"]:has([aria-label="assistant"]) .stChatMessageContent {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 4px 14px 14px 14px !important;
    color: #1E293B !important;
    font-size: 0.92rem !important;
    line-height: 1.65 !important;
    padding: 14px 18px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stChatMessageContent * {
    color: #1E293B !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stChatMessageContent strong {
    color: #0F172A !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stChatMessageContent h3,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stChatMessageContent h4 {
    color: #0F172A !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stChatMessageContent,
[data-testid="stChatMessage"]:has([aria-label="user"]) .stChatMessageContent {
    background: #EFF6FF !important;
    border: 1px solid #BFDBFE !important;
    border-radius: 14px 4px 14px 14px !important;
    color: #1E3A8A !important;
    font-size: 0.92rem !important;
    padding: 12px 18px !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stChatMessageContent * {
    color: #1E3A8A !important;
}

/* Chat tables */
.stChatMessageContent table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.86rem;
    margin: 10px 0;
}
.stChatMessageContent th {
    background: #F8FAFC !important;
    color: #475569 !important;
    font-size: 0.74rem;
    letter-spacing: 0.4px;
    text-transform: uppercase;
    padding: 8px 10px;
    border-bottom: 2px solid #E2E8F0;
}
.stChatMessageContent td {
    border-bottom: 1px solid #E2E8F0;
    padding: 7px 10px;
    color: #334155 !important;
}
.stChatMessageContent code {
    background: #F1F5F9 !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 4px !important;
    padding: 2px 6px !important;
    font-size: 0.82rem !important;
    color: #2563EB !important;
}

@media (max-width: 768px) {
    [data-testid="stChatMessage"] {
        padding: 4px 0 !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stChatMessageContent,
    [data-testid="stChatMessage"]:has([aria-label="assistant"]) .stChatMessageContent {
        padding: 10px 12px !important;
        font-size: 0.86rem !important;
        border-radius: 4px 12px 12px 12px !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stChatMessageContent,
    [data-testid="stChatMessage"]:has([aria-label="user"]) .stChatMessageContent {
        padding: 8px 12px !important;
        font-size: 0.86rem !important;
        border-radius: 12px 4px 12px 12px !important;
    }
    .stChatMessageContent table {
        display: block !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        max-width: 100% !important;
        font-size: 0.74rem !important;
    }
}

/* ── Fixed Bottom Input Bar (iOS Safe Area & Mobile Keyboard Friendly) ── */
div[data-testid="stBottom"] {
    background: #F8FAFC !important;
    border-top: 1px solid #E2E8F0 !important;
    padding-bottom: max(16px, env(safe-area-inset-bottom)) !important;
    padding-top: 10px !important;
    z-index: 900 !important;
}
div[data-testid="stChatInput"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}
div[data-testid="stChatInput"] > div {
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 24px !important;
    padding: 6px 16px !important;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
div[data-testid="stChatInput"] > div:focus-within {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2), 0 2px 16px rgba(0, 0, 0, 0.08) !important;
}
div[data-testid="stChatInput"] textarea {
    background: transparent !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    caret-color: #2563EB !important;
    font-size: 0.95rem !important;
    font-weight: 400 !important;
    font-family: 'Inter', sans-serif !important;
    line-height: 1.5 !important;
    padding: 8px 6px !important;
    opacity: 1 !important;
}
div[data-testid="stChatInput"] textarea::placeholder {
    color: #94A3B8 !important;
    -webkit-text-fill-color: #94A3B8 !important;
    opacity: 1 !important;
}
div[data-testid="stChatInput"] button {
    background: #2563EB !important;
    border: none !important;
    border-radius: 50% !important;
    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
    min-height: 32px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: auto 0 !important;
    box-shadow: none !important;
    outline: none !important;
    cursor: pointer !important;
    transition: background 0.15s ease !important;
}
div[data-testid="stChatInput"] button:hover {
    background: #1D4ED8 !important;
}
div[data-testid="stChatInput"] button svg {
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
    width: 15px !important;
    height: 15px !important;
}

.chat-scroll-spacer {
    height: 120px;
    width: 100%;
}

@media (max-width: 768px) {
    div[data-testid="stBottom"] {
        padding-left: 8px !important;
        padding-right: 8px !important;
        padding-top: 6px !important;
        padding-bottom: max(10px, env(safe-area-inset-bottom)) !important;
    }
    div[data-testid="stBottom"] > div {
        width: 100% !important;
        max-width: 100% !important;
        padding: 0 !important;
    }
    div[data-testid="stChatInput"] {
        width: 100% !important;
    }
    div[data-testid="stChatInput"] > div {
        padding: 3px 10px !important;
        border-radius: 20px !important;
    }
    div[data-testid="stChatInput"] textarea {
        font-size: 16px !important; /* CRITICAL: 16px prevents iOS Safari auto-zoom on tap */
        padding: 6px 4px !important;
        line-height: 1.35 !important;
    }
    div[data-testid="stChatInput"] button {
        width: 30px !important;
        height: 30px !important;
        min-width: 30px !important;
        min-height: 30px !important;
    }
    .chat-scroll-spacer {
        height: 85px !important;
    }
}

/* ── Plotly & DataFrame Wrappers ── */
.js-plotly-plot .modebar { display: none !important; }
.stPlotlyChart {
    background: #FFFFFF !important;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #E2E8F0 !important;
    padding: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}
[data-testid="stDataFrame"] {
    background: #FFFFFF !important;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #E2E8F0 !important;
}
@media (max-width: 768px) {
    .stPlotlyChart {
        padding: 4px !important;
        margin-bottom: 10px !important;
    }
    [data-testid="stDataFrame"] {
        max-width: 100% !important;
        overflow-x: auto !important;
    }
}

/* ── Sidebar Typography ── */
.sb-logo   { font-size: 1.5rem; font-weight: 800; color: #0F172A !important; line-height: 1; }
.sb-tag    { font-size: 0.72rem; color: #64748B !important; letter-spacing: 0.7px; text-transform: uppercase; margin-top: 2px; }
.sb-label  { font-size: 0.68rem; font-weight: 600; color: #64748B !important; letter-spacing: 0.8px; text-transform: uppercase; margin: 18px 0 6px; }
</style>
""",
    unsafe_allow_html=True,
)

# Auto-collapse sidebar on mobile devices (<= 768px), keeping it expanded on desktop/laptop
components.html(
    """
    <script>
    try {
        if (window.parent && window.parent.innerWidth <= 768) {
            const sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
            if (sidebar && sidebar.getAttribute('aria-expanded') === 'true') {
                const btn = sidebar.querySelector('button[data-testid="stSidebarCollapseButton"]');
                if (btn) btn.click();
            }
        }
    } catch(e) {}
    </script>
    """,
    height=0,
)

# ═══════════════════════════════════════════════════════════════
# PLOTLY LIGHT THEME
# ═══════════════════════════════════════════════════════════════
_PLOT_BASE = dict(
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font=dict(color="#334155", family="Inter, sans-serif", size=12),
    margin=dict(l=30, r=30, t=40, b=60),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#475569", size=11)),
    hoverlabel=dict(bgcolor="#0F172A", font_color="#FFFFFF", bordercolor="#334155"),
)
_AX = dict(gridcolor="#F1F5F9", linecolor="#E2E8F0", zerolinecolor="#E2E8F0")

def light_layout(**extra) -> dict:
    return {**_PLOT_BASE, **extra}

# ═══════════════════════════════════════════════════════════════
# DATA PATHS
# ═══════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMBINED_CSV = os.path.join(BASE_DIR, "all_plants_stops_2025_2026.csv")
DEFAULT_CSV = COMBINED_CSV if os.path.exists(COMBINED_CSV) else os.path.join(BASE_DIR, "plant_stops_2025_2026.csv")

if not os.path.exists(DEFAULT_CSV):
    import subprocess, sys
    gen = os.path.join(BASE_DIR, "generate_multi_plant_data.py")
    if os.path.exists(gen):
        subprocess.run([sys.executable, gen], cwd=BASE_DIR, check=True)

# ═══════════════════════════════════════════════════════════════
# SIDEBAR CONTROLS
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="sb-logo">🏭 OPIQ</div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-tag">Operations Intelligence Platform</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown('<div class="sb-label">Data Source</div>', unsafe_allow_html=True)
    mode = st.radio(
        "", ["Multi-Plant Database (Cleopatra & BMIC)", "Upload Custom Excel / CSV"],
        index=0, label_visibility="collapsed"
    )
    uploaded = None
    if mode == "Upload Custom Excel / CSV":
        uploaded = st.file_uploader(
            "Drop file here", type=["xlsx", "xls", "csv"],
            help="Columns: Machine, Start Date, Duration, Class, Type, Reason for downtime, [Plant]"
        )

    st.divider()
    st.markdown('<div class="sb-label">AI Engine Settings</div>', unsafe_allow_html=True)
    secret_key = ""
    try:
        secret_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass

    api_key = st.text_input(
        "Google Gemini API Key",
        value=secret_key,
        type="password", placeholder="AIzaSy...",
        help="Paste your Google AI Studio key to activate live Gemini narration."
    )
    model_choice = st.selectbox(
        "Model Version",
        ["Auto (Multi-Model Fallback)", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    )
    chosen_model = "auto" if "Auto" in model_choice else model_choice

    if api_key:
        st.success("Gemini Engine Active", icon="🟢")
    else:
        st.caption("⚪ Built-in Analytics Engine (Offline)")

    st.divider()
    st.markdown('<div class="sb-label">Monitored Facilities</div>', unsafe_allow_html=True)
    st.markdown("""
    - **🏛️ Cleopatra Plant:** Kiln, Raw Mill, Cement Mills A/B, **Sand Mill**, Crusher
    - **🏭 BMIC Plant:** Kiln, Raw Mill, Cement Mills A/B, **Coal Mill**, Crusher
    """)

# ═══════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def _load(src):
    return load_and_preprocess_data(src)

try:
    df = _load(uploaded) if uploaded else _load(DEFAULT_CSV)
except Exception as exc:
    st.error(f"Failed to load dataset: {exc}")
    st.stop()

# ═══════════════════════════════════════════════════════════════
# BRAND BAR
# ═══════════════════════════════════════════════════════════════
now_str = datetime.now().strftime("%d %b · %H:%M")
st.markdown(
    f"""
<div class="brand-bar">
  <div style="font-size:1.8rem;line-height:1;flex-shrink:0;">🏭</div>
  <div style="flex:1;min-width:0;">
    <div class="brand-title">Operations Intelligence</div>
    <div class="brand-sub">Multi-Plant Cement Manufacturing · Cleopatra &amp; BMIC</div>
  </div>
  <div class="live-pill"><span class="live-dot"></span>LIVE &nbsp;·&nbsp; {now_str}</div>
</div>
""",
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════
# GLOBAL SCOPE CONTROLS (PLANT SELECTOR + FLEET SCOPE FILTER)
# ═══════════════════════════════════════════════════════════════
plant_col, fleet_col = st.columns([1, 1], gap="medium")

with plant_col:
    st.markdown('<div style="font-size:0.75rem;font-weight:600;color:#64748B;text-transform:uppercase;margin-bottom:6px;">🏢 Facility Scope</div>', unsafe_allow_html=True)
    plant_selector_ui = st.segmented_control(
        "Plant Selector",
        ["🌐 All Plants", "🏛️ Cleopatra", "🏭 BMIC"],
        default="🌐 All Plants",
        label_visibility="collapsed"
    )
    if not plant_selector_ui:
        plant_selector_ui = "🌐 All Plants"

    if "Cleopatra" in plant_selector_ui:
        active_plant = "Cleopatra Plant"
    elif "BMIC" in plant_selector_ui:
        active_plant = "BMIC Plant"
    else:
        active_plant = "All Plants"

# Determine available machines for the active plant scope
if active_plant == "Cleopatra Plant":
    available_fleet_machines = sorted([m for m in df[df["Plant"] == "Cleopatra Plant"]["Machine"].unique()])
elif active_plant == "BMIC Plant":
    available_fleet_machines = sorted([m for m in df[df["Plant"] == "BMIC Plant"]["Machine"].unique()])
else:
    available_fleet_machines = sorted(list(df["Machine"].unique()))

with fleet_col:
    st.markdown('<div style="font-size:0.75rem;font-weight:600;color:#64748B;text-transform:uppercase;margin-bottom:6px;">⚙️ Equipment Fleet Scope</div>', unsafe_allow_html=True)
    fleet_mode = st.radio(
        "Fleet Filter Mode",
        ["Whole Fleet", "Select Machines"],
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )
    if fleet_mode == "Select Machines":
        selected_fleet = st.multiselect(
            "Select Equipment:",
            options=available_fleet_machines,
            default=available_fleet_machines,
            label_visibility="collapsed"
        )
        if not selected_fleet:
            selected_fleet = available_fleet_machines
    else:
        selected_fleet = available_fleet_machines
        st.caption(f"✓ All **{len(available_fleet_machines)}** equipment units included")

# Compute KPIs for the selected Plant + Fleet slice
kpis = calculate_plant_kpis(df, plant=active_plant, machines=selected_fleet)

# ═══════════════════════════════════════════════════════════════
# TOP NAVIGATION (SEGMENTED CONTROL)
# ═══════════════════════════════════════════════════════════════
nav_options = [
    "💬 AI Assistant",
    "📊 Dashboard",
    "📋 Stoppages"
]
active_view = st.segmented_control(
    "Navigation View",
    nav_options,
    default="💬 AI Assistant",
    label_visibility="collapsed"
)
if not active_view:
    active_view = "💬 AI Assistant"

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# VIEW 1: AI QUERY ASSISTANT (CHATGPT / CLAUDE STYLE)
# ═══════════════════════════════════════════════════════════════
if "Assistant" in active_view:

    avail = kpis["availability_pct"]
    fleet_count_label = f"{len(selected_fleet)} of {len(available_fleet_machines)} Units" if fleet_mode == "Select Machines" else f"Full Fleet ({len(available_fleet_machines)} Units)"

    # Sleek Multi-Plant Status Ribbon
    st.markdown(
        f"""
<div class="chat-status-ribbon">
  <div class="chat-status-item">
    <span>Active Plant:</span>
    <span class="chat-status-val" style="color:#2563EB">{active_plant}</span>
  </div>
  <div class="chat-status-item">
    <span>Fleet Scope:</span>
    <span class="chat-status-val">{fleet_count_label}</span>
  </div>
  <div class="chat-status-item">
    <span>Availability:</span>
    <span class="chat-status-val" style="color:#059669">{avail}%</span>
  </div>
  <div class="chat-status-item">
    <span>True Run Time:</span>
    <span class="chat-status-val">{kpis['true_runtime_hours']:,.0f} hrs</span>
  </div>
  <div class="chat-status-item">
    <span>Total Downtime:</span>
    <span class="chat-status-val">{kpis['total_downtime_hours']:,.0f} hrs</span>
  </div>
  <div class="chat-status-item" style="margin-left:auto;">
    <span>Unplanned Loss:</span>
    <span class="chat-status-val" style="color:#D97706">{kpis['kpi_downtime_hours']:,.0f} hrs</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Operational Scope Notice
    st.markdown(
        """
<div class="gr-bar">
  <div style="font-size:1.1rem;flex-shrink:0;">🛡️</div>
  <div class="gr-text">
    <strong style="color:#1D4ED8">Multi-Plant Scope Lock Active</strong> — Answers are grounded strictly in
    verified stoppage records for <strong>Cleopatra Plant</strong> and <strong>BMIC Plant</strong>.
    Multi-turn conversation memory is active.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Suggested Inquiries (Plant & Fleet Aware)
    CHIPS = [
        "Compare availability: Cleopatra vs BMIC",
        "Top 5 causes for Kiln downtime in Cleopatra",
        "How many hours did Coal Mill lose in BMIC?",
        "Overall total downtime across both plants",
        "Electrical vs Mechanical incidents — Raw mill",
        "Which machine has the lowest availability in the fleet?",
        "Scheduled maintenance comparison between plants"
    ]
    
    col_pills, col_clear = st.columns([5, 1])
    with col_pills:
        selected_chip = st.pills("Quick Inquiries", CHIPS, selection_mode="single", default=None, label_visibility="collapsed")
    with col_clear:
        if st.session_state.get("messages") and len(st.session_state.messages) > 1:
            if st.button("🗑 Clear", use_container_width=True, help="Reset conversation"):
                st.session_state.messages = []
                st.session_state.pop("_last_chip", None)
                st.rerun()

    # Welcome Message
    WELCOME_MSG = (
        "### OPIQ Multi-Plant Operations Intelligence — Ready\n\n"
        "I provide validated, data-backed downtime and availability analytics across your cement manufacturing facilities:\n\n"
        "- **🏛️ Cleopatra Plant:** Kiln · Raw Mill · W. Cement Mills (A/B) · **Sand Mill** · Crusher\n"
        "- **🏭 BMIC Plant:** Kiln · Raw Mill · W. Cement Mills (A/B) · **Coal Mill** · Crusher\n\n"
        "You can ask for plant-specific inquiries, comparative fleet benchmarks, or enterprise totals. "
        "All calculations reflect exact reconstructed operating hours without hallucinations.\n\n"
        "*Select any suggestion above or type your question in the box below.*"
    )

    if "messages" not in st.session_state or not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": WELCOME_MSG}]

    # Render Chat History
    chat_box = st.container()
    with chat_box:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="🏭" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])

    # Bottom spacer
    st.markdown('<div class="chat-scroll-spacer"></div>', unsafe_allow_html=True)

    # Chat Input
    user_input = st.chat_input("Ask about Cleopatra, BMIC, machine availability, Coal Mill, or downtime causes...")
    
    if selected_chip and selected_chip != st.session_state.get("_last_chip"):
        st.session_state["_last_chip"] = selected_chip
        user_input = selected_chip

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with chat_box:
            with st.chat_message("user", avatar="👤"):
                st.markdown(user_input)

            with st.chat_message("assistant", avatar="🏭"):
                with st.spinner("Analyzing multi-plant stoppage records..."):
                    reply = answer_query(
                        user_input, df,
                        api_key=api_key.strip() if api_key else None,
                        chosen_model=chosen_model,
                        chat_history=st.session_state.messages,
                        default_plant=active_plant,
                        active_machines=selected_fleet,
                    )
                st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})

    # Auto-scroll to bottom of chat
    components.html(
        """
        <script>
        try {
            const mainContainer = window.parent.document.querySelector('section.main');
            if (mainContainer) {
                mainContainer.scrollTo({
                    top: mainContainer.scrollHeight,
                    behavior: 'smooth'
                });
            }
        } catch (e) {}
        </script>
        """,
        height=0,
    )

# ═══════════════════════════════════════════════════════════════
# VIEW 2: PERFORMANCE DASHBOARD
# ═══════════════════════════════════════════════════════════════
elif "Dashboard" in active_view:

    avail = kpis["availability_pct"]
    avail_sub = "▲ Above 85% target" if avail >= 85 else "▼ Below 85% target"
    avail_color = "#059669" if avail >= 85 else "#DC2626"

    fleet_summary_sub = f"{active_plant} · {len(selected_fleet)} of {len(available_fleet_machines)} Units" if fleet_mode == "Select Machines" else f"{active_plant} · All {len(available_fleet_machines)} Units"

    # KPI Cards (Clean Light Mode)
    st.markdown(
        f"""
<div style="font-size:0.75rem;color:#64748B;font-weight:600;text-transform:uppercase;margin-bottom:8px;">
  Scope: <span style="color:#2563EB;">{fleet_summary_sub}</span>
</div>
<div class="kpi-row">
  <div class="kpi-card kc-blue">
    <div class="kpi-label">📉 Total Downtime</div>
    <div class="kpi-value">{kpis['total_downtime_hours']:,.0f} <span style="font-size:1rem;font-weight:500;color:#64748B">hrs</span></div>
    <div class="kpi-sub">{kpis['total_stops']:,} stop events</div>
  </div>
  <div class="kpi-card kc-teal">
    <div class="kpi-label">⏱ True Operating Time</div>
    <div class="kpi-value">{kpis['true_runtime_hours']:,.0f} <span style="font-size:1rem;font-weight:500;color:#64748B">hrs</span></div>
    <div class="kpi-sub">{kpis['active_tracks']} continuous equipment tracks</div>
  </div>
  <div class="kpi-card kc-green">
    <div class="kpi-label">✅ Fleet Availability</div>
    <div class="kpi-value">{avail}<span style="font-size:1.1rem;font-weight:500;color:#64748B">%</span></div>
    <div class="kpi-sub" style="color:{avail_color}">{avail_sub}</div>
  </div>
  <div class="kpi-card kc-amber">
    <div class="kpi-label">🔴 Unplanned KPI Loss</div>
    <div class="kpi-value">{kpis['kpi_downtime_hours']:,.0f} <span style="font-size:1rem;font-weight:500;color:#64748B">hrs</span></div>
    <div class="kpi-sub">Incidents &amp; Circumstances</div>
  </div>
  <div class="kpi-card kc-violet">
    <div class="kpi-label">🔧 Scheduled Maintenance</div>
    <div class="kpi-value">{kpis['scheduled_downtime_hours']:,.0f} <span style="font-size:1rem;font-weight:500;color:#64748B">hrs</span></div>
    <div class="kpi-sub">Planned stops — excluded from KPIs</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    filt_col, _ = st.columns([2, 5])
    with filt_col:
        chart_machine = st.selectbox(
            "Filter Visualizations by Equipment:",
            ["All Selected Fleet"] + selected_fleet,
            key="dash_eq",
        )
    dash_m_target = None if chart_machine == "All Selected Fleet" else chart_machine

    # Row 1: Pareto & Sunburst
    r1a, r1b = st.columns([3, 2], gap="medium")

    with r1a:
        st.markdown(f'<div class="sec-label">🔍 Root-Cause Pareto — {active_plant}</div>', unsafe_allow_html=True)
        pareto = get_pareto_analysis(df, machine=dash_m_target, machines=selected_fleet if not dash_m_target else None, plant=active_plant, top_n=8)
        if not pareto.empty:
            pareto["lbl"] = pareto["Reason for downtime"].str[:36].apply(lambda x: x + ("..." if len(x) == 36 else ""))
            fig_p = go.Figure()
            fig_p.add_trace(
                go.Bar(
                    x=pareto["lbl"],
                    y=pareto["Total_Hours"],
                    name="Lost Hours",
                    marker=dict(
                        color=pareto["Total_Hours"],
                        colorscale=[[0, "#93C5FD"], [1, "#2563EB"]],
                        showscale=False,
                    ),
                    text=pareto["Total_Hours"].apply(lambda v: f"{v:.0f}h"),
                    textposition="outside",
                    textfont=dict(size=10, color="#475569"),
                    customdata=pareto["Reason for downtime"],
                    hovertemplate="<b>%{customdata}</b><br>%{y:.1f} hrs lost<extra></extra>",
                )
            )
            fig_p.add_trace(
                go.Scatter(
                    x=pareto["lbl"],
                    y=pareto["Cumulative_%"],
                    name="Cumulative %",
                    yaxis="y2",
                    line=dict(color="#D97706", width=2.5),
                    mode="lines+markers",
                    marker=dict(size=7, color="#D97706", line=dict(color="#FFFFFF", width=1.5)),
                    hovertemplate="Cumulative: %{y:.1f}%<extra></extra>",
                )
            )
            fig_p.add_hline(
                y=80, yref="y2", line_dash="dot", line_color="#DC2626",
                annotation_text="80% mark", annotation_position="top right",
                annotation_font_color="#DC2626", annotation_font_size=11,
            )
            fig_p.update_layout(
                **light_layout(
                    height=360,
                    xaxis=dict(tickangle=-28, tickfont=dict(size=10), **_AX),
                    yaxis=dict(title="Hours Lost", **_AX),
                    yaxis2=dict(
                        title="Cumulative %", overlaying="y", side="right",
                        range=[0, 108], gridcolor="rgba(0,0,0,0)", linecolor="#CBD5E1",
                    ),
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.03,
                        xanchor="right", x=1, bgcolor="rgba(0,0,0,0)",
                    ),
                )
            )
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.info("No records found for this filter.")

    with r1b:
        st.markdown(f'<div class="sec-label">⚙️ Stoppage Class Breakdown — {active_plant}</div>', unsafe_allow_html=True)
        cat_df = get_downtime_by_category(df, machine=dash_m_target, machines=selected_fleet if not dash_m_target else None, plant=active_plant)
        if not cat_df.empty:
            fig_s = px.sunburst(
                cat_df,
                path=["Class", "Type"],
                values="Hours",
                color="Class",
                color_discrete_map={
                    "Incidents": "#EF4444",
                    "Circumstance": "#F59E0B",
                    "Schedule": "#10B981",
                },
            )
            fig_s.update_traces(
                textfont=dict(family="Inter", size=12),
                insidetextorientation="radial",
            )
            fig_s.update_layout(
                **light_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
            )
            st.plotly_chart(fig_s, use_container_width=True)
            st.markdown(
                """<div style="display:flex;gap:18px;font-size:.74rem;color:#475569;margin-top:4px;">
                  <span><span style="color:#EF4444">●</span> Incidents (KPI-affecting)</span>
                  <span><span style="color:#F59E0B">●</span> Circumstance (KPI-affecting)</span>
                  <span><span style="color:#10B981">●</span> Schedule (planned)</span>
                </div>""",
                unsafe_allow_html=True,
            )

    # Row 2: Fleet Table
    st.markdown(f'<div class="sec-label">🏭 Fleet Availability &amp; Downtime Benchmarks ({active_plant})</div>', unsafe_allow_html=True)
    tbl = get_machine_summary_table(df, plant=active_plant, machines=selected_fleet)
    if not tbl.empty:
        def _color_avail(v):
            if v >= 90:   return "color:#059669;font-weight:600"
            elif v >= 80: return "color:#D97706;font-weight:600"
            return "color:#DC2626;font-weight:600"

        styled = (
            tbl.style
            .format({
                "Total Downtime (hrs)": "{:,.1f}",
                "True Run Time (hrs)": "{:,.1f}",
                "Availability %": "{:.1f}%",
                "Incident Downtime (hrs)": "{:,.1f}",
                "Schedule Downtime (hrs)": "{:,.1f}",
            })
            .applymap(_color_avail, subset=["Availability %"])
        )
        st.dataframe(styled, use_container_width=True, height=270)

    # Row 3: Monthly Trend
    st.markdown(f'<div class="sec-label">📈 Monthly Downtime Trend — {active_plant}</div>', unsafe_allow_html=True)
    trend = get_monthly_trend(df, machine=dash_m_target, machines=selected_fleet if not dash_m_target else None, plant=active_plant)
    if not trend.empty:
        fig_t = go.Figure()
        fig_t.add_trace(
            go.Bar(
                x=trend["YearMonth"], y=trend["Incident_Downtime"],
                name="Unplanned (Incidents + Circumstance)",
                marker_color="#EF4444", opacity=0.88,
                hovertemplate="%{x}<br>Unplanned: %{y:.1f} hrs<extra></extra>",
            )
        )
        fig_t.add_trace(
            go.Bar(
                x=trend["YearMonth"], y=trend["Schedule_Downtime"],
                name="Scheduled Maintenance",
                marker_color="#10B981", opacity=0.88,
                hovertemplate="%{x}<br>Scheduled: %{y:.1f} hrs<extra></extra>",
            )
        )
        fig_t.update_layout(
            **light_layout(
                height=290,
                barmode="stack",
                xaxis=dict(tickangle=-35, tickfont=dict(size=10), **_AX),
                yaxis=dict(title="Hours", **_AX),
                legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1),
            )
        )
        st.plotly_chart(fig_t, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
# VIEW 3: STOPPAGE RECORDS
# ═══════════════════════════════════════════════════════════════
elif "Stoppages" in active_view or "Records" in active_view:
    st.markdown(f'<div class="sec-label">📋 Stoppage Records Log ({active_plant})</div>', unsafe_allow_html=True)

    fc0, fc1, fc2, fc3 = st.columns(4)
    with fc0:
        plant_options = sorted(df["Plant"].unique()) if "Plant" in df.columns else ["Cleopatra Plant"]
        p_sel = st.multiselect(
            "Plant", plant_options,
            default=[active_plant] if active_plant in plant_options else plant_options,
            key="rd_p"
        )
    with fc1:
        m_sel = st.multiselect(
            "Machine", available_fleet_machines,
            default=selected_fleet, key="rd_m"
        )
    with fc2:
        c_sel = st.multiselect(
            "Class", sorted(df["Class"].unique()),
            default=sorted(df["Class"].unique()), key="rd_c"
        )
    with fc3:
        t_sel = st.multiselect(
            "Type", sorted(df["Type"].unique()),
            default=sorted(df["Type"].unique()), key="rd_t"
        )

    plant_filter = df["Plant"].isin(p_sel) if "Plant" in df.columns else True
    filtered = df[
        plant_filter &
        df["Machine"].isin(m_sel) &
        df["Class"].isin(c_sel) &
        df["Type"].isin(t_sel)
    ]

    info_col, btn_col = st.columns([5, 1])
    with info_col:
        st.caption(
            f"**{len(filtered):,}** records · out of {len(df):,} total  ·  "
            f"Period: {kpis.get('date_range', '—')}"
        )
    with btn_col:
        st.download_button(
            "📥 Export CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"stoppages_{active_plant.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.dataframe(filtered, use_container_width=True, height=520)
