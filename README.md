# 🏭 OPIQ — Multi-Plant Operations Intelligence Platform

An enterprise-grade, mobile-responsive AI-powered operations monitoring and reliability analytics dashboard for cement manufacturing facilities (**Cleopatra Plant** & **BMIC Plant**).

Built with **Streamlit**, **Pandas**, **Plotly**, and **Google Gemini 2.5/2.0**.

---

## 🌟 Key Features

1. **Multi-Plant Facility Scope**:
   - **🏛️ Cleopatra Plant:** Kiln, Raw Mill, Cement Mills (A/B), **Sand Mill**, Crusher.
   - **🏭 BMIC Plant:** Kiln, Raw Mill, Cement Mills (A/B), **Coal Mill**, Crusher (distinguished equipment fleet).
   - **🌐 Enterprise Total:** Aggregated cross-facility operational benchmarks.

2. **Accurate Downtime & True Run Time Engine**:
   - Reconstructed continuous operating hours without per-row aggregation artifacts:
     $$\text{Daily Run Time} = \max(0,\, 24 - \sum \text{Downtime})$$
   - **Deterministic KPI Separation:**
     - **Unplanned KPI Loss:** `Incidents` (Mechanical, Electrical, Production) and `Circumstances` (silo full, lab stops, etc.).
     - **Planned Maintenance:** `Schedule` (preventive maintenance, scheduled overhauls) excluded from operational loss KPIs.

3. **Domain-Guardrailed AI Assistant**:
   - Conversational multi-turn memory grounded strictly in verified stoppage records.
   - Deterministic calculations powered by Pandas + Gemini synthesis (zero hallucinations on figures or hours).

4. **Executive Visual Analytics**:
   - Dynamic 80/20 Root-Cause Pareto analysis with cumulative threshold markers.
   - Interactive 2-level Sunburst breakdown (Class & Type).
   - Historical monthly downtime stacked trends.
   - Fleet benchmark comparison table with availability heat indicators.

5. **Responsive Light Design System**:
   - High-contrast, clean enterprise theme.
   - 100% mobile-friendly with responsive touch navigation, compact KPI grids, and fixed bottom chat capsule.

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/ZiadElsayed16/<your-repo-name>.git
cd <your-repo-name>
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Dashboard
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## 📂 Project Structure

```
├── app.py                         # Streamlit UI & responsive design system
├── analytics.py                   # Deterministic data processor & KPI engine
├── agent.py                       # Conversational AI agent with domain guardrails
├── generate_multi_plant_data.py   # Multi-plant dataset generator
├── cleopatra_plant_stops_2025_2026.csv / .xlsx
├── bmic_plant_stops_2025_2026.csv / .xlsx
├── all_plants_stops_2025_2026.csv / .xlsx
├── requirements.txt               # Dependencies
├── .streamlit/
│   └── config.toml                # Light theme and server configuration
├── run_app.bat                    # Windows 1-click local launcher
└── start_public_server.bat        # 1-click Cloudflare tunnel launcher
```

---

## ☁️ Deployment to Streamlit Community Cloud

1. Push this repository to your GitHub account: `https://github.com/ZiadElsayed16/<repo-name>`.
2. Go to [share.streamlit.io](https://share.streamlit.io) and log in with GitHub.
3. Click **"New app"**, select this repository and branch (`main`), set main file path to `app.py`.
4. Deploy! Your app will be live 24/7 at a permanent `https://<your-app-name>.streamlit.app` URL.
