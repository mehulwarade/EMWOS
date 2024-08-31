#!/bin/bash

# Configuration
SERVER_URL="http://localhost:8000"
ALLOCATE_ENDPOINT="/allocate"
RELEASE_ENDPOINT="/release"
NUM_REQUESTS=100
CONCURRENT_REQUESTS=10

# Function to generate a random job name
generate_job_name() {
    echo "job_$(date +%s)_$RANDOM"
}

# Function to get current time in seconds
current_time_s() {
    date +%s
}

# Function to send allocation request
allocate_resource() {
    local job_name=$(generate_job_name)
    local start_time=$(current_time_s)
    local response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "{\"job\":\"$job_name\"}" "${SERVER_URL}${ALLOCATE_ENDPOINT}")
    local end_time=$(current_time_s)
    local status_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    local duration=$((end_time - start_time))

    if [ "$status_code" == "200" ]; then
        echo "$duration $job_name"
    else
        echo "ERROR $status_code $body"
    fi
}

# Function to send release request
release_resource() {
    local job_name="$1"
    local start_time=$(current_time_s)
    local response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "{\"job\":\"$job_name\"}" "${SERVER_URL}${RELEASE_ENDPOINT}")
    local end_time=$(current_time_s)
    local status_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    local duration=$((end_time - start_time))

    if [ "$status_code" == "200" ]; then
        echo "$duration"
    else
        echo "ERROR $status_code $body"
    fi
}

# Perform allocations
echo "Performing $NUM_REQUESTS allocations..."
allocate_results=$(for i in $(seq 1 $NUM_REQUESTS); do
    allocate_resource &
    if (( i % CONCURRENT_REQUESTS == 0 )); then wait; fi
done
wait)

# Calculate allocation statistics
allocate_times=$(echo "$allocate_results" | grep -v ERROR | cut -d' ' -f1)
allocate_avg=$(echo "$allocate_times" | awk '{ total += $1; count++ } END { if (count > 0) printf "%.2f", total/count; else print "0" }')
allocate_errors=$(echo "$allocate_results" | grep ERROR | wc -l)

# Extract job names for successful allocations
job_names=$(echo "$allocate_results" | grep -v ERROR | cut -d' ' -f2-)

# Perform releases
echo "Performing releases for allocated resources..."
release_results=$(echo "$job_names" | while read job_name; do
    release_resource "$job_name" &
    if (( i % CONCURRENT_REQUESTS == 0 )); then wait; fi
done
wait)

# Calculate release statistics
release_times=$(echo "$release_results" | grep -v ERROR | cut -d' ' -f1)
release_avg=$(echo "$release_times" | awk '{ total += $1; count++ } END { if (count > 0) printf "%.2f", total/count; else print "0" }')
release_errors=$(echo "$release_results" | grep ERROR | wc -l)

# Print results
echo "Allocation Results:"
echo "  Average response time: $allocate_avg seconds"
echo "  Errors: $allocate_errors"

echo "Release Results:"
echo "  Average response time: $release_avg seconds"
echo "  Errors: $release_errors"

# Print any errors encountered
if [ $allocate_errors -gt 0 ] || [ $release_errors -gt 0 ]; then
    echo "Errors encountered:"
    echo "$allocate_results" | grep ERROR
    echo "$release_results" | grep ERROR
fi