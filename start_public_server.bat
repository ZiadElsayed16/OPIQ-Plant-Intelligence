@echo off
title Cement Operations AI Server
echo ======================================================
echo Starting Streamlit Dashboard and Public Cloudflare Tunnel...
echo ======================================================

REM Launch Streamlit in background
start "Streamlit App" cmd /k "python -m streamlit run app.py --server.port 8501"

REM Wait 3 seconds for Streamlit to start
timeout /t 3 >nul

REM Launch Cloudflare Tunnel
echo Starting public tunnel...
start "Public Internet Tunnel" cmd /k "cloudflared.exe tunnel --url http://localhost:8501"

echo ======================================================
echo Both servers have been launched!
echo Check the Cloudflare window for your live https://...trycloudflare.com link.
echo On local Wi-Fi, you can also use: http://192.168.1.11:8501
echo ======================================================
pause
