@echo off
REM Easy startup for the FastAPI web UI.
call conda activate downlaoder
if ERRORLEVEL 1 (
  echo [ERROR] Failed to activate conda environment "downloader".
  echo Make sure Anaconda/Miniconda is installed and conda on PATH.
  pause
  exit /b 1
)
python -m uvicorn app.server:app --reload --port 8000
