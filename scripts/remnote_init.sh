#!/bin/bash
# RemNote Initialization Script (Bash)

echo "--- RemNote Bridge Initialization ---"

# 1. Check status using the CLI (in JSON mode for parsing)
STATUS=$(npx remnote-cli status --json 2>/dev/null)

# 2. Check if "connected":true exists in the output
if [[ $STATUS == *"\"connected\":true"* ]]; then
    echo "SUCCESS: RemNote Bridge is already CONNECTED."
else
    echo "Bridge not connected nesting. Starting daemon..."
    # Attempt to start the daemon
    npx remnote-cli daemon start
    
    # Wait for the daemon to spin up and connect
    echo "Waiting 5 seconds for connection..."
    sleep 5
    
    # Re-check status
    NEW_STATUS=$(npx remnote-cli status --json 2>/dev/null)
    if [[ $NEW_STATUS == *"\"connected\":true"* ]]; then
        echo "SUCCESS: RemNote Bridge is now CONNECTED."
    else
        echo "ERROR: Could not establish connection. Please ensure RemNote is open with the Automation Bridge plugin."
        exit 1
    fi
fi
