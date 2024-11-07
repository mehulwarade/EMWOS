#!/usr/bin/env python3

"""
DAG and Submit File Editor for EMWOS Workflow Scheduling

This script processes workflow DAG files based on a scheduling CSV file to:
1. Add PRE/POST script commands with execution numbers for each job
2. Optionally remove priority settings from both DAG and submit files
3. Create backups of all modified files

Input Requirements:
-----------------
1. Schedule CSV file with columns:
   - workflow_folder_path: Absolute path to the workflow folder
   - job_name: Name of the job
   - execution_number: Scheduling order number
   - [other columns are ignored]

2. Workflow folders containing:
   - A single .dag file in the root
   - Submit (.sub) files referenced in the DAG

Operations Performed:
------------------
1. For each workflow in the schedule:
   - Locates the DAG file in the workflow folder
   - Adds PRE/POST script lines with execution numbers
   - Removes PRIORITY lines if -rm-prio flag is used
   - Creates backup as .dag.bak

2. For submit files (if -rm-prio is used):
   - Removes priority lines from all submit files
   - Creates backup as .sub.bak

Usage:
-----
Basic usage:
    python3 dag_editor.py -s schedule.csv

Remove priority settings:
    python3 dag_editor.py -s schedule.csv -rm-prio

Arguments:
---------
Required:
    -s, --schedule    Path to the schedule CSV file

Optional:
    -rm-prio         Remove priority lines from both DAG and submit files

Example Schedule CSV:
------------------
workflow_folder_path,job_name,execution_number
/path/to/workflow1,job1,1
/path/to/workflow1,job2,2
/path/to/workflow2,job1,3

Output:
-------
1. Modified DAG files with added PRE/POST scripts:
   SCRIPT PRE job_name emwos-pre-post.sh pre submit_file.sub execution_number
   SCRIPT POST job_name emwos-pre-post.sh post submit_file.sub execution_number

2. Backup files:
   - Original DAG: filename.dag.bak
   - Original submit files: filename.sub.bak

3. Console output:
   - Processing status for each workflow
   - Location of backup files
   - Summary of successful/failed operations

Error Handling:
-------------
- Creates backups before modifications
- Attempts to restore from backup if errors occur
- Reports specific errors for each file
- Non-zero exit code if any workflow fails

Authors:
-------
Created for EMWOS Workflow Scheduling System by Mehul Warade
November 7, 2024
"""

import sys
import os
import argparse
import csv
from collections import defaultdict
from pathlib import Path

def read_schedule(csv_file):
    """Read the schedule CSV file and organize job information by workflow."""
    workflow_jobs = defaultdict(dict)
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                workflow_folder = row['workflow_folder_path']
                job_name = row['job_name']
                exec_num = row['execution_number']
                workflow_jobs[workflow_folder][job_name] = exec_num
    except FileNotFoundError:
        print(f"Error: Schedule file '{csv_file}' not found.")
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Required column {e} not found in CSV file.")
        sys.exit(1)
    return workflow_jobs

def find_dag_file(workflow_folder):
    """Find the .dag file in the workflow folder."""
    try:
        dag_files = list(Path(workflow_folder).glob("*.dag"))
        if not dag_files:
            print(f"Error: No DAG file found in {workflow_folder}")
            return None
        if len(dag_files) > 1:
            print(f"Warning: Multiple DAG files found in {workflow_folder}. Using {dag_files[0]}")
        return str(dag_files[0])
    except Exception as e:
        print(f"Error accessing workflow folder {workflow_folder}: {e}")
        return None

def remove_priority_from_submit(submit_file):
    """Remove priority lines from submit files."""
    try:
        with open(submit_file, 'r') as f:
            lines = f.readlines()
        
        new_lines = [line for line in lines if not line.strip().startswith('priority')]
        
        # Create backup of submit file
        backup_file = f"{submit_file}.bak"
        os.rename(submit_file, backup_file)
        
        with open(submit_file, 'w') as f:
            f.writelines(new_lines)
            
        print(f"Removed priority from submit file: {submit_file}")
        print(f"Submit file backup created at: {backup_file}")
        return True
    except Exception as e:
        print(f"Error processing submit file {submit_file}: {e}")
        return False

def get_absolute_submit_path(dag_dir, submit_file):
    """Convert submit file path to absolute path."""
    if os.path.isabs(submit_file):
        return submit_file
    return os.path.abspath(os.path.join(dag_dir, submit_file))

def edit_dag_file(dag_file, job_exec_numbers, remove_priority):
    """Edit the DAG file to add PRE/POST scripts with execution numbers."""
    backup_file = f"{dag_file}.bak"
    dag_dir = os.path.dirname(dag_file)
    submit_files_processed = set()
    
    try:
        # Create backup
        os.rename(dag_file, backup_file)

        with open(backup_file, 'r') as infile, open(dag_file, 'w') as outfile:
            # Keep the first 10 lines unchanged
            for _ in range(10):
                line = infile.readline()
                outfile.write(line)

            # Process the rest of the file
            current_job = None
            for line in infile:
                if line.startswith('JOB '):
                    parts = line.split()
                    if len(parts) < 3:
                        print(f"Warning: Invalid JOB line in {dag_file}: {line}")
                        outfile.write(line)
                        continue
                        
                    current_job = parts[1]
                    submit_file = parts[2]
                    exec_num = job_exec_numbers.get(current_job, "UNKNOWN")
                    
                    # Get absolute path of submit file
                    abs_submit_path = get_absolute_submit_path(dag_dir, submit_file)
                    
                    # Remove priority from submit file if needed
                    if remove_priority and abs_submit_path not in submit_files_processed:
                        if os.path.exists(abs_submit_path):
                            if remove_priority_from_submit(abs_submit_path):
                                submit_files_processed.add(abs_submit_path)
                        else:
                            print(f"Warning: Submit file not found: {abs_submit_path}")
                    
                    outfile.write(line)
                    outfile.write(f"SCRIPT PRE {current_job} emwos-pre-post pre {submit_file} {exec_num}\n")
                    outfile.write(f"SCRIPT POST {current_job} emwos-pre-post post {submit_file} {exec_num}\n")
                
                elif line.startswith('SCRIPT POST '):
                    # Skip the old POST line
                    continue
                elif line.startswith('PRIORITY'):
                    if not remove_priority:
                        outfile.write(line)
                else:
                    outfile.write(line)

        print(f"Processed DAG file: {dag_file}")
        print(f"DAG file backup created at: {backup_file}")
        print(f"Processed {len(submit_files_processed)} submit files")
        return True

    except Exception as e:
        print(f"Error processing DAG file {dag_file}: {e}")
        # Try to restore backup if something went wrong
        if os.path.exists(backup_file):
            try:
                os.replace(backup_file, dag_file)
                print(f"Restored original DAG file from backup")
            except Exception as restore_error:
                print(f"Error restoring backup: {restore_error}")
        return False

def process_workflows(schedule_file, remove_priority):
    """Process all workflows from the schedule."""
    # Read the schedule
    workflow_jobs = read_schedule(schedule_file)
    
    successful = 0
    failed = 0
    total_submit_files = 0
    
    # Process each workflow
    for workflow_folder, job_exec_numbers in workflow_jobs.items():
        print(f"\nProcessing workflow: {workflow_folder}")
        
        # Find DAG file
        dag_file = find_dag_file(workflow_folder)
        if not dag_file:
            print(f"Skipping workflow folder: {workflow_folder}")
            failed += 1
            continue
            
        # Edit the DAG file
        if edit_dag_file(dag_file, job_exec_numbers, remove_priority):
            successful += 1
        else:
            failed += 1
    
    return successful, failed

def main():
    parser = argparse.ArgumentParser(
        description="Edit DAG files and submit files based on schedule to add PRE-POST scripts with execution numbers"
    )
    parser.add_argument(
        '-s', '--schedule',
        required=True,
        help="Path to the schedule CSV file"
    )
    parser.add_argument(
        '-rm-prio',
        action='store_true',
        help="Remove PRIORITY lines from both DAG and submit files"
    )
    
    args = parser.parse_args()

    print(f"Processing schedule from: {args.schedule}")
    print(f"Remove priority lines: {args.rm_prio}")
    
    successful, failed = process_workflows(args.schedule, args.rm_prio)
    
    print("\nSummary:")
    print(f"Successfully processed: {successful} workflow(s)")
    print(f"Failed to process: {failed} workflow(s)")
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()