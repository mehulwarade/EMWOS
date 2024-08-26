#!/bin/sh

# ./0RunBackground.sh ./2monitoring -e -i 1000 -f test.csv

# Check if command-line argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <command>"
    exit 1
fi

# Run the command with nohup, send it to the background, and detach it from the terminal
nohup "$@" >/dev/null 2>&1 &

# Store the PID of the background process into a file
echo $! > background_process.pid

echo "Process started in the background with PID: $!"
