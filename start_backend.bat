@echo off 
title Inspection Intelligence - Backend API 
cd /d "%%~dp0" 
echo Starting backend on http://localhost:8000 ... 
echo Docs available at http://localhost:8000/docs 
echo. 
.venv\Scripts\python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload 
pause
