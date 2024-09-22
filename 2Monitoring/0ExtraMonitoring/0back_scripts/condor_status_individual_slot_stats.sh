#!/bin/bash

# Function to display help
show_help() {
    echo "Usage: $0 [-f <base_filename>] [-h]"
    echo "Options:"
    echo "  -f <base_filename>   Specify the base filename for the output CSVs. Default is 'condor_status'."
    echo "  -h                   Show this help message."
}

# Set default base filename
base_filename="_no_args"

# Parse command-line arguments
while getopts ":f:h" opt; do
    case ${opt} in
        f )
            base_filename=$OPTARG
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
shift $((OPTIND -1))

# Define the output files
status_activity_file="condor_status_individual_slot_activity_${base_filename}.csv"
status_state_file="condor_status_individual_slot_state_${base_filename}.csv"

# Run condor_status command and store the output
status_header_name_output=$(condor_status -autoformat Name)

header=$(echo "$status_header_name_output" | tr '\n' ',' | sed 's/,$//')

echo "timestamp,$header" > "$status_activity_file"
echo "timestamp,$header" > "$status_state_file"

# Function to get stats
get_stats() {
    # Get timestamp
    timestamp=$(date +%s)
    
    state_output=$(condor_status -autoformat State)
    state_output_formatted=$(echo "$state_output" | tr '\n' ',' | sed 's/,$//')

    activity_output=$(condor_status -autoformat Activity)
    activity_output_formatted=$(echo "$activity_output" | tr '\n' ',' | sed 's/,$//')

    echo "$timestamp,$state_output_formatted" >> "$status_state_file"
    echo "$timestamp,$activity_output_formatted" >> "$status_activity_file"
}

# Main loop
while true; do
    # Get stats
    get_stats
    # Wait for 1 second
    sleep 1
done