@echo off
echo Starting MapMyLeads...
cd /d "%~dp0"
echo Installing/verifying dependencies...
venv\Scripts\python.exe -m pip install fastapi uvicorn requests python-dotenv pydantic --quiet
echo.
echo Launching server at http://localhost:3000
echo Press Ctrl+C to stop.
echo.
venv\Scripts\python.exe -m uvicorn server:app --reload --port 3000
