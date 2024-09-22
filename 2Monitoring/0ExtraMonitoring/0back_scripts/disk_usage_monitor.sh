#!/bin/bash

# Function to display help
show_help() {
    echo "Usage: $0 [-f <filename>] [-d <directory>] [-h]"
    echo "Options:"
    echo "  -f <filename>   Specify the base filename. Default is 'disk_usage_stats'."
    echo "  -d <directory>  Specify the directory to monitor. Default is '/' (root)."
    echo "  -h              Show this help message."
}

# Set default values
base_filename="_no_args"
directory="/"

# Parse command-line arguments
while getopts ":f:d:h" opt; do
    case ${opt} in
        f )
            base_filename=$OPTARG
            ;;
        d )
            directory=$OPTARG
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
filename="disk_usage_monitor_${base_filename}.csv"

# Function to get timestamp and disk usage
get_stats() {
    # Get timestamp
    timestamp=$(date +%s)
    
    # Get disk usage in MB
    disk_info=$(df -BM "$directory" | tail -n 1)
    total=$(echo "$disk_info" | awk '{print $2}' | tr -d 'M')
    used=$(echo "$disk_info" | awk '{print $3}' | tr -d 'M')
    available=$(echo "$disk_info" | awk '{print $4}' | tr -d 'M')
    use_percent=$(echo "$disk_info" | awk '{print $5}' | tr -d '%')
    
    # Output timestamp and stats
    echo "$timestamp,$total,$used,$available,$use_percent"
}

# CSV header
echo "timestamp,total_mb,used_mb,available_mb,use_percent" > "$filename"

# Main loop
while true; do
    # Get stats
    stats=$(get_stats)
    
    # Append to CSV
    echo "$stats" >> "$filename"
    
    # Wait for 1 second
    sleep 1
done