@echo off
REM Vibe-Trading Backend Start Script (Windows Batch)

SET PYTHONPATH=agent

IF EXIST ".venv\Scripts\python.exe" (
    echo Starting backend with .venv\Scripts\python.exe...
    ".venv\Scripts\python.exe" "agent\cli.py" serve --port 8899 --host 127.0.0.1
) ELSE IF EXIST "agent\.venv\Scripts\python.exe" (
    echo Starting backend with agent\.venv\Scripts\python.exe...
    "agent\.venv\Scripts\python.exe" "agent\cli.py" serve --port 8899 --host 127.0.0.1
) ELSE (
    echo Warning: No virtual environment found. Falling back to system python.
    python "agent\cli.py" serve --port 8899 --host 127.0.0.1
)
pause
