#!/bin/sh

# command line:
# free -m | head -n 2 | tail -n 1 | awk -F '[:,;]' '{print $2,$3,$4,$5,$6,$7,$8}' | tr -d '[:alpha:]' | tr -s ' ' | sed 's/^ //;s/ $//' | tr ' ' ','

# Function to display help
show_help() {
    echo "Usage: $0 [-f <base_filename>] [-h]"
    echo "Options:"
    echo "  -f <base_filename>   Specify the base filename to be appended to the output CSV filename."
    echo "  -h                   Show this help message."
}

# Set default base filename
base_filename="_no_args"

# Parse command-line arguments
while getopts ":f:h" opt; do
    case ${opt} in
        f )
            base_filename="_$OPTARG"
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

# Construct the full filename
filename="freem_memory_total_stats${base_filename}.csv"

# Function to get timestamp and freem output
get_stats() {
    # Get timestamp
    timestamp=$(date +%s)
    
    # Get freem output and process it
    freem_output=$(free -m | head -n 2 | tail -n 1)
    stats=$(echo "$freem_output" | awk -F '[:,;]' '{print $2,$3,$4,$5,$6,$7,$8}' | tr -d '[:alpha:]' | tr -s ' ' | sed 's/^ //;s/ $//' | tr ' ' ',')
    
    # Output timestamp and stats
    echo "$timestamp,$stats"
}

# CSV header
echo "Timestamp,Total,Used,Free,Shared,Buffers,Available" > "$filename"

# Main loop
while true; do
    # Get stats
    stats=$(get_stats)
    
    # Append to CSV
    echo "$stats" >> "$filename"
    
    # Wait for 1 second
    sleep 1
done