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
                log_message "$action" "$job_name" "release" "" "successful" "after $retry_count retries"
            fi
            return 0
        else
            local operation=$([ "$action" = "pre" ] && echo "allocate" || echo "release")
            log_message "$action" "$job_name" "$operation" "" "failed (HTTP $http_status)" "retrying"
            retry_count=$((retry_count + 1))
            sleep $(( RANDOM % 10 + 1 ))
        fi
    done
}

# Main script
if [ "$#" -ne 2 ]; then
    echo "Error: Two arguments are required."
    exit 0
fi

ACTION="$1"
SUBMIT_FILE="$2"

if [[ "$ACTION" != "pre" && "$ACTION" != "post" ]]; then
    echo "Error: First argument must be 'pre' or 'post'."
    exit 0
fi

if [[ ! "$SUBMIT_FILE" =~ \.sub$ ]]; then
    echo "Error: Second argument must be a .sub file."
    exit 0
fi

# Check if the submit file exists
if [ ! -f "$SUBMIT_FILE" ]; then
    echo "Error: Submit file '$SUBMIT_FILE' does not exist."
    exit 0
fi

JOB_NAME=$(basename "$SUBMIT_FILE" .sub)

if [ "$ACTION" = "pre" ]; then
    if should_skip_job "$JOB_NAME"; then
        log_message "$ACTION" "$JOB_NAME" "pre-skip" "" "skipped" "job type at path: $SUBMIT_FILE"
        exit 0
    fi

    while true; do
        resource=$(send_request "$ACTION" "$JOB_NAME")
        if [ -n "$resource" ]; then
            update_submit_file "$resource"
            log_message "$ACTION" "$JOB_NAME" "update" "$resource" "successful" "updated submit file"
            break
        else
            log_message "$ACTION" "$JOB_NAME" "update" "" "failed" "could not allocate resource, retrying"
            sleep $(( RANDOM % 10 + 1 ))
        fi
    done
else
    OUT_FILE="${SUBMIT_FILE%.sub}.out"
    META_FILE="${SUBMIT_FILE%.sub}.meta"

    # Check if .out file exists
    while [ ! -f "$OUT_FILE" ]; do
        log_message "$ACTION" "$JOB_NAME" "check" "" "failed" "OUT file not found: $OUT_FILE, retrying"
        sleep $(( RANDOM % 10 + 1 ))
    done

    # Run pegasus-exitcode
    while true; do
        /usr/bin/pegasus-exitcode "$OUT_FILE"
        exitcode_status=$?
        if [ $exitcode_status -eq 0 ]; then
            break
        else
            log_message "$ACTION" "$JOB_NAME" "check" "" "failed" "pegasus-exitcode failed with status $exitcode_status, retrying"
            sleep $(( RANDOM % 10 + 1 ))
        fi
    done

    # Check if .meta file exists
    while [ ! -f "$META_FILE" ]; do
        log_message "$ACTION" "$JOB_NAME" "check" "" "failed" "META file not found: $META_FILE, retrying"
        sleep $(( RANDOM % 10 + 1 ))
    done

    if should_skip_job "$JOB_NAME"; then
        log_message "$ACTION" "$JOB_NAME" "post-skip" "" "skipped" "job type at path: $SUBMIT_FILE"
        exit 0
    fi

    # If all checks pass, send the release request
    send_request "$ACTION" "$JOB_NAME"
fi