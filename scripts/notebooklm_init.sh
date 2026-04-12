#!/bin/bash
# NotebookLM Initialization Script (Bash)

echo "--- NotebookLM Initialization ---"

# Use the python executable from the virtual environment directly
VENV_PYTHON="./antigravitytest-env/Scripts/python.exe"
NOTEBOOKLM="./antigravitytest-env/Scripts/notebooklm.exe"
DEFAULT_NOTEBOOK_ID="804fd7b7-8c70-462e-829c-ba892d32e7b6"

# 1. Export encoding for Windows console (consistent results)
export PYTHONIOENCODING="utf-8"

echo "Checking Authentication status..."
AUTH_OUT=$($NOTEBOOKLM auth check --test 2>/dev/null)

if [[ $AUTH_OUT == *"Authentication is valid"* ]]; then
    echo "SUCCESS: Authentication is VALID."
else
    echo "Authentication failed. Attempting automatic login..."
    # Attempt automatic login using python subprocess
    "$VENV_PYTHON" -c "import subprocess, time; p=subprocess.Popen(['$NOTEBOOKLM', 'login'], stdin=subprocess.PIPE); time.sleep(5); p.communicate(input=b'\n')"

    echo "Re-checking Authentication status..."
    AUTH_OUT=$($NOTEBOOKLM auth check --test 2>/dev/null)
    if [[ $AUTH_OUT == *"Authentication is valid"* ]]; then
        echo "SUCCESS: Authentication is VALID."
    else
        echo "ERROR: Automatic login failed."
        echo "Please run 'notebooklm login' manually inside your shell."
        exit 1
    fi
fi

# List notebooks
echo "Retrieving available notebooks..."
$NOTEBOOKLM list --json

echo "Successfully initialized."

# Use default notebook
echo "Setting default notebook..."
if [ -z "$DEFAULT_NOTEBOOK_ID" ]; then
    echo "No default notebook ID specified."
    exit 1
fi
$NOTEBOOKLM use $DEFAULT_NOTEBOOK_ID
echo "Default notebook set."
