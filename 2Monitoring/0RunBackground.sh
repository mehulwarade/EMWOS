#!/bin/sh

# Function to display help message
show_help() {
    echo "Usage: $0 [OPTIONS] <command>"
    echo "Run a command in the background and log its execution."
    echo ""
    echo "Options:"
    echo "  -h    Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 ./2monitoring -e -i 1000 -f test.csv"
}

# Function to log the command execution
log_command() {
    # Get the name of this script without the path
    local script_name=$(basename "$0")
    # Remove the extension (if any) and add .log
    local log_file="${script_name%.*}.log"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "$timestamp - Command: $0 $@" >> "$log_file"
}

# Check for -h option or if no arguments are provided
if [ "$1" = "-h" ] || [ $# -eq 0 ]; then
    show_help
    exit 0
fi

# Log the command execution
log_command "$@"

# Run the command with nohup, send it to the background, and detach it from the terminal
nohup "$@" >/dev/null 2>&1 &

# Store the PID of the background process into a file
echo $! > .background_process.pid

echo "Process started in the background with PID: $!"