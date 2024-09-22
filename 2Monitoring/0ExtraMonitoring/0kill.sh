#!/bin/bash

# Function to display help
show_help() {
    echo "Usage: $0 [-f <pid_file>] [-m] [-h]"
    echo "Options:"
    echo "  -f <pid_file>   Specify the file containing PIDs to kill. Default is '.background_process.pid'."
    echo "  -m              Move CSV files to folders based on their names."
    echo "  -h              Show this help message."
}

# Set default values
pid_file=".background_process.pid"
move_files=false

# Parse command-line arguments
while getopts ":f:mh" opt; do
    case ${opt} in
        f )
            pid_file=$OPTARG
            ;;
        m )
            move_files=true
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

# Check if the PID file exists
if [ ! -f "$pid_file" ]; then
    echo "Error: PID file '$pid_file' not found."
    exit 1
fi

# Read PIDs from the file and kill processes
while IFS= read -r pid; do
    if [ -n "$pid" ]; then
        if kill -0 "$pid" 2>/dev/null; then
            echo "Killing process with PID: $pid"
            kill "$pid"
        else
            echo "Process with PID $pid does not exist or is not killable."
        fi
    fi
done < "$pid_file"

# Remove the PID file after killing processes
rm -f "$pid_file"

echo "All processes have been terminated and PID file has been removed."

# Move CSV files if -m option is provided
if [ "$move_files" = true ]; then
    echo "Moving CSV files to their respective folders..."
    
    # Find all CSV files in the current directory
    for csv_file in *.csv; do
        if [ -f "$csv_file" ]; then
            # Extract the last part of the name (e.g., test1 from condor_q_total_stats_test1.csv)
            folder_name=$(echo "$csv_file" | sed -E 's/.*_([^_]+)\.csv$/\1/')
            
            # Create folder if it doesn't exist
            mkdir -p "$folder_name"
            
            # Move the file to the folder
            mv "$csv_file" "$folder_name/"
            echo "Moved $csv_file to $folder_name/"
        fi
    done
    
    echo "CSV files have been organized into folders."
fi