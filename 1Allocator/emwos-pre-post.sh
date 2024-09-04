#!/bin/bash

# Constants
SERVER_URL="http://localhost:8000"
ALLOCATE_ENDPOINT="/allocate"
RELEASE_ENDPOINT="/release"
LOG_FILE="emwos-pre-post.log"

# Function to log messages
log_message() {
    local timestamp=$(date +%s)
    local action="$1"
    local job_name="$2"
    local operation="$3"
    local resource="$4"
    local status="$5"
    local additional_info="$6"
    echo "$timestamp, $action, $job_name, $operation, $resource, $status $additional_info" >> "$LOG_FILE"
}

# Function to check if a job should be skipped
should_skip_job() {
    local job_name="$1"
    [[ "$job_name" == create_* ]] || [[ "$job_name" == stage_in_* ]] || [[ "$job_name" == stage_out_* ]]
}

# Function to update the submit file
update_submit_file() {
    local resource="$1"
    sed -i 's/^requirements.*$/requirements = (Name == "'"$resource"'")/' "$SUBMIT_FILE"
}

# Function to extract resource from JSON response
extract_resource() {
    local json="$1"
    echo "$json" | sed -n 's/.*"resource"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'
}

# Function to send request to server and handle retries
send_request() {
    local action="$1"
    local job_name="$2"
    local request_body="{\"job\":\"$job_name\"}"
    local retry_count=0
    local max_retries=10
    local endpoint

    if [ "$action" = "pre" ]; then
        endpoint="${SERVER_URL}${ALLOCATE_ENDPOINT}"
    else
        endpoint="${SERVER_URL}${RELEASE_ENDPOINT}"
    fi

    while true; do
        response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$request_body" "$endpoint")
        http_body=$(echo "$response" | sed '$d')
        http_status=$(echo "$response" | tail -n1)

        if [ "$http_status" -eq 200 ]; then
            if [ "$action" = "pre" ]; then
                resource=$(extract_resource "$http_body")
                log_message "$action" "$job_name" "allocate" "$resource" "successful" "after $retry_count retries"
                echo "$resource"
            else
                log_message "$action" "$job_name" "release" "" "successful" ""
            fi
            return 0
        else
            if [ "$action" = "post" ]; then
                log_message "$action" "$job_name" "release" "" "failed (HTTP $http_status)" "$http_body"
                return 1
            else
                log_message "$action" "$job_name" "allocate" "" "failed (HTTP $http_status)" "retrying"
                retry_count=$((retry_count + 1))
                if [ $retry_count -ge $max_retries ]; then
                    log_message "$action" "$job_name" "allocate" "" "failed" "max retries reached"
                    return 1
                fi
                sleep $(( RANDOM % 10 + 1 ))
            fi
        fi
    done
}

# Main script
if [ "$#" -ne 2 ]; then
    echo "Error: Two arguments are required."
    exit 1
fi

ACTION="$1"
SUBMIT_FILE="$2"

if [[ "$ACTION" != "pre" && "$ACTION" != "post" ]]; then
    echo "Error: First argument must be 'pre' or 'post'."
    exit 1
fi

if [[ ! "$SUBMIT_FILE" =~ \.sub$ ]]; then
    echo "Error: Second argument must be a .sub file."
    exit 1
fi

# Check if the submit file exists
if [ ! -f "$SUBMIT_FILE" ]; then
    echo "Error: Submit file '$SUBMIT_FILE' does not exist."
    exit 1
fi

JOB_NAME=$(basename "$SUBMIT_FILE" .sub)

if should_skip_job "$JOB_NAME"; then
    log_message "$ACTION" "$JOB_NAME" "skip" "" "skipped" "removing for job type at path: $SUBMIT_FILE"
    exit 0
fi

if [ "$ACTION" = "pre" ]; then
    resource=$(send_request "$ACTION" "$JOB_NAME")
    if [ $? -eq 0 ] && [ -n "$resource" ]; then
        update_submit_file "$resource"
        log_message "$ACTION" "$JOB_NAME" "update" "$resource" "successful" "updated submit file"
    else
        log_message "$ACTION" "$JOB_NAME" "update" "" "failed" "could not allocate resource"
        exit 1
    fi
else
    send_request "$ACTION" "$JOB_NAME"
fi