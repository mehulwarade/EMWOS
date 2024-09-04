#!/bin/sh

# Function to display help message
show_help() {
    echo "Usage: $0 [OPTIONS] <command>"
    echo "Run a command in the background and log its execution."
    echo ""
    echo "Options:"
    echo "  -h, --help     Display this help message"
    echo "  -c, --capture  Capture the output of the background job"
    echo ""
    echo "Example:"
    echo "  $0 --capture ./background-allocator-daemon.py"
}

# Function to log the command execution
log_command() {
    local script_name=$(basename "$0")
    local log_file="${script_name%.*}.log"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "$timestamp - Command: $0 $ORIGINAL_ARGS" >> "$log_file"
}

# Function to generate output filename
generate_output_filename() {
    local timestamp=$(date +%s)
    local script_name=$(basename "$0")
    local script_basename="${script_name%.*}"
    local background_job_name=$(basename "$1")
    echo "${timestamp}_${script_basename}_${background_job_name}.out"
}

# Function to check if resources are available
check_resources() {
    local resources_file="resources.txt"
    if [ ! -f "$resources_file" ]; then
        echo "Resources file not found. Creating an empty one."
        touch "$resources_file"
        return 0
    fi

    if [ -s "$resources_file" ]; then
        echo "Error: Resources are currently in use. Please wait for the current job to finish."
        return 1
    fi

    return 0
}

# Store original arguments
ORIGINAL_ARGS="$@"

# Initialize capture flag
capture_output=false

# Parse options
while [ "$1" != "" ]; do
    case $1 in
        -h | --help )
            show_help
            exit 0
            ;;
        -c | --capture )
            capture_output=true
            shift
            ;;
        * )
            break
            ;;
    esac
done

# Check if no command is provided
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

# Check resources
if ! check_resources; then
    exit 1
fi

# Log the command execution
log_command

# Generate the output filename
output_file=$(generate_output_filename "$1")

# Write job information to resources file
echo "$$ - $output_file" > resources.txt

if [ "$capture_output" = true ]; then
    # Run the command with nohup, send it to the background, and capture output
    nohup "$@" > "$output_file" 2>&1 &
else
    # Run the command with nohup, send it to the background, and discard output
    nohup "$@" >/dev/null 2>&1 &
fi

# Store the PID of the background process into a file
echo $! > background_process.pid

echo "Process started in the background with PID: $!"
if [ "$capture_output" = true ]; then
    echo "Output is being captured in $output_file"
fi

# Clean up resources file when the job is done
(
    wait $!
    echo "" > resources.txt
) &