#!/bin/bash

# Function to display help message
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Run multiple monitoring scripts in the background and log their execution."
    echo ""
    echo "Options:"
    echo "  -f <filename>   Specify the base filename for all scripts"
    echo "  -h              Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 -f testmw2"
}

# Function to log the command execution
log_command() {
    local log_file="background_script.log"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "$timestamp - Command: $0 $@" >> "$log_file"
}

# Initialize variables
filename=""

# Parse command-line options
while getopts "f:h" opt; do
    case ${opt} in
        f )
            filename=$OPTARG
            ;;
        h )
            show_help
            exit 0
            ;;
        \? )
            echo "Invalid option: $OPTARG" 1>&2
            show_help
            exit 1
            ;;
    esac
done

# Check if filename is provided
if [ -z "$filename" ]; then
    echo "Error: Filename is required. Use -f option to specify a filename."
    show_help
    exit 1
fi

# Log the command execution
log_command "$@"

# Array of scripts to run
scripts=(
    "./condor_q_total_stats.sh"
    "./condor_status_individual_slot_stats.sh"
    "./condor_status_total_stats.sh"
    "./freem_memory_total_stats.sh"
    "./disk_usage_monitor.sh"
)

# Run each script in the background
for script in "${scripts[@]}"; do
    nohup "$script" -f "$filename" >/dev/null 2>&1 &
    pid=$!
    echo "$pid" >> .background_process.pid
    echo "Started $script with PID: $pid"
done

echo "All processes started in the background. PIDs stored in .background_process.pid"