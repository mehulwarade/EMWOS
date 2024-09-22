# EMWOS Condor Monitoring System

This repository contains a set of scripts for monitoring various aspects of a Condor cluster and system resources. The scripts collect data on Condor queue status, slot status, memory usage, and disk usage. Additionally, there are scripts for managing the background processes and organizing the output files.

## Scripts Overview

1. `background.sh`: Runs all monitoring scripts in the background.
2. `condor_q_total_stats.sh`: Monitors Condor queue statistics.
3. `condor_status_total_stats.sh`: Monitors overall Condor slot statistics.
4. `condor_status_individual_slot_stats.sh`: Monitors individual Condor slot statistics.
5. `freem_memory_total_stats.sh`: Monitors system memory usage.
6. `disk_usage_monitor.sh`: Monitors disk usage.
7. `0kill.sh`: Terminates background processes and organizes output files.

## Usage

### Starting Monitoring

To start all monitoring scripts, use the `background.sh` script:

```bash
./background.sh -f <base_filename>
```

This will start all monitoring scripts in the background, with each script's output file having the specified base filename appended to it.

### Individual Scripts

Each monitoring script can also be run individually:

```bash
./<script_name>.sh -f <base_filename>
```

Replace `<script_name>` with the name of the specific script you want to run.

### Stopping Monitoring and Organizing Files

To stop all monitoring processes and organize the output files, use the `0kill.sh` script:

```bash
./0kill.sh -m
```

The `-m` option moves all CSV files into folders based on their names.

## Script Details

### background.sh

Runs all monitoring scripts in the background. It takes a base filename as an argument and passes it to each individual script.

### condor_q_total_stats.sh

Collects statistics about the Condor queue, including the number of jobs in various states (idle, running, held, etc.).

### condor_status_total_stats.sh

Gathers overall statistics about Condor slots, including the number of slots in different states (owner, claimed, unclaimed, etc.).

### condor_status_individual_slot_stats.sh

Monitors the state and activity of individual Condor slots.

### freem_memory_total_stats.sh

Tracks system memory usage, including total, used, free, shared, and available memory.

### disk_usage_monitor.sh

Monitors disk usage, tracking total, used, and available disk space.

### 0kill.sh

Terminates all background monitoring processes and organizes the output CSV files into folders based on their names.

## Output

Each script generates a CSV file with a timestamp and relevant statistics. The files are named in the format:

```
<script_name>_<base_filename>.csv
```

When the `0kill.sh` script is run with the `-m` option, it organizes these files into folders named after the `<base_filename>` part.

## Requirements

- Bash shell
- Condor command-line tools (`condor_q`, `condor_status`)
- Standard Unix utilities (`free`, `df`, etc.)

## Note

Ensure all scripts are made executable before running:

```bash
chmod +x *.sh
```

This monitoring system provides a comprehensive view of your Condor cluster and system resources, allowing for easy data collection and analysis.