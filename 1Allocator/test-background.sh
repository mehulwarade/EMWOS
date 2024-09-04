#!/bin/bash

# Configuration
SERVER_URL="http://localhost:8000"
ALLOCATE_ENDPOINT="/allocate"
RELEASE_ENDPOINT="/release"
NUM_REQUESTS=150
CONCURRENT_REQUESTS=10
LOG_FILE="test-background.log"
MAX_RETRY_DELAY=5

# Function to generate a random job name
generate_job_name() {
    echo "job_$(date +%s)_$RANDOM"
}

# Function to get current time in seconds
current_time_s() {
    date +%s
}

# Function to log messages
log_message() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Function to generate a random delay between 0 and MAX_RETRY_DELAY seconds
random_delay() {
    echo $(awk -v min=0 -v max=$MAX_RETRY_DELAY 'BEGIN{srand(); print int(min+rand()*(max-min+1))}')
}

# Function to send allocation request with infinite retry
allocate_resource() {
    local job_name=$(generate_job_name)
    local start_time=$(current_time_s)
    local request_body="{\"job\":\"$job_name\"}"
    local attempt=1
    local status_code
    local body
    local response

    while true; do
        log_message "ALLOCATION REQUEST (Attempt $attempt): $request_body"
        response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$request_body" "${SERVER_URL}${ALLOCATE_ENDPOINT}")
        status_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | sed '$d')

        if [ "$status_code" == "200" ]; then
            break
        else
            delay=$(random_delay)
            log_message "Received status $status_code. Retrying in $delay seconds... (Attempt $attempt)"
            sleep $delay
            attempt=$((attempt+1))
        fi
    done

    local end_time=$(current_time_s)
    local duration=$((end_time - start_time))

    log_message "ALLOCATION RESPONSE: Status: $status_code, Body: $body, Duration: ${duration}s, Attempts: $attempt"

    echo "$duration $job_name"
}

# Function to send release request with infinite retry
release_resource() {
    local job_name="$1"
    local start_time=$(current_time_s)
    local request_body="{\"job\":\"$job_name\"}"
    local attempt=1
    local status_code
    local body
    local response

    while true; do
        log_message "RELEASE REQUEST (Attempt $attempt): $request_body"
        response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$request_body" "${SERVER_URL}${RELEASE_ENDPOINT}")
        status_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | sed '$d')

        if [ "$status_code" == "200" ]; then
            break
        else
            delay=$(random_delay)
            log_message "Received status $status_code. Retrying in $delay seconds... (Attempt $attempt)"
            sleep $delay
            attempt=$((attempt+1))
        fi
    done

    local end_time=$(current_time_s)
    local duration=$((end_time - start_time))

    log_message "RELEASE RESPONSE: Status: $status_code, Body: $body, Duration: ${duration}s, Attempts: $attempt"

    echo "$duration"
}

# Clear the log file
> "$LOG_FILE"
log_message "Starting resource allocation test"

# Perform allocations
echo "Performing $NUM_REQUESTS allocations..."
allocate_results=$(for i in $(seq 1 $NUM_REQUESTS); do
    allocate_resource &
    if (( i % CONCURRENT_REQUESTS == 0 )); then wait; fi
done
wait)

# Calculate allocation statistics
allocate_times=$(echo "$allocate_results" | cut -d' ' -f1)
allocate_avg=$(echo "$allocate_times" | awk '{ total += $1; count++ } END { if (count > 0) printf "%.2f", total/count; else print "0" }')

# Extract job names for successful allocations
job_names=$(echo "$allocate_results" | cut -d' ' -f2-)

# Perform releases
echo "Performing releases for allocated resources..."
release_results=$(echo "$job_names" | while read job_name; do
    release_resource "$job_name" &
    if (( i % CONCURRENT_REQUESTS == 0 )); then wait; fi
done
wait)

# Calculate release statistics
release_times=$(echo "$release_results")
release_avg=$(echo "$release_times" | awk '{ total += $1; count++ } END { if (count > 0) printf "%.2f", total/count; else print "0" }')

# Print results
echo "Allocation Results:"
echo "  Average response time: $allocate_avg seconds"

echo "Release Results:"
echo "  Average response time: $release_avg seconds"

# Log the results
log_message "Test completed. Allocation avg: ${allocate_avg}s. Release avg: ${release_avg}s."

echo "Log file created at: $LOG_FILE"