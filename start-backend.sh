#!/bin/bash
# Vibe-Trading Backend Start Script (Unix/Bash)

# Get the script's directory
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$ROOT/agent"

# Detect python binary
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
elif [[ -x "$ROOT/agent/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/agent/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

echo "Starting backend with $PYTHON_BIN..."
exec "$PYTHON_BIN" "$ROOT/agent/cli.py" serve --port 8899 --host 127.0.0.1
