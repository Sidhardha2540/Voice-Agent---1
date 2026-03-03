@echo off
REM Run the Voice Agent backend. Use from project root.
cd /d "%~dp0..\backend"
if not exist .venv\Scripts\activate.bat (
  echo Creating venv...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
echo Starting server at http://localhost:8000
uvicorn main:app --reload
