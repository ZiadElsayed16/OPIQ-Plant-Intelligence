@echo off
title OPIQ Automated Test Suite
echo =======================================================
echo Running OPIQ Industrial Automated Test Suite (pytest)
echo =======================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONPATH=%cd%
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pytest -v
) else (
    "C:\Users\ziade\AppData\Local\Programs\Python\Python39\python.exe" -m pytest -v
)
echo =======================================================
pause
