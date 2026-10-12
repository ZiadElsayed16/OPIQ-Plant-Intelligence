@echo off
title Cement Plant Stoppage AI Agent - Streamlit Prototype
echo =======================================================
echo Starting Cement Plant Stoppage AI Assistant...
echo URL: http://localhost:8501
echo =======================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
) else (
    "C:\Users\ziade\AppData\Local\Programs\Python\Python39\python.exe" -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
)
pause
