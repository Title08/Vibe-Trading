# Vibe-Trading Backend Start Script (Windows PowerShell)

# Set PYTHONPATH to include the agent directory
$env:PYTHONPATH = "agent"

# Check if .venv exists in root
if (Test-Path ".\.venv\Scripts\python.exe") {
    Write-Host "Starting backend with .venv/Scripts/python.exe..." -ForegroundColor Cyan
    & ".\.venv\Scripts\python.exe" "agent\cli.py" serve --port 8899 --host 127.0.0.1
}
# Check if .venv exists in agent folder
elseif (Test-Path ".\agent\.venv\Scripts\python.exe") {
    Write-Host "Starting backend with agent/.venv/Scripts/python.exe..." -ForegroundColor Cyan
    & ".\agent\.venv\Scripts\python.exe" "agent\cli.py" serve --port 8899 --host 127.0.0.1
}
else {
    Write-Host "Warning: No virtual environment found. Falling back to system python." -ForegroundColor Yellow
    python "agent\cli.py" serve --port 8899 --host 127.0.0.1
}
