#!/usr/bin/env python3

"""
Multi-DAG Multi-Preference HEFT Scheduler for EMWOS Workflow Management System

This script implements a multi-workflow scheduler using the Heterogeneous Earliest Finish Time (HEFT)
algorithm with support for workflow preferences and resource allocation.

Features:
---------
1. Multi-workflow support:
   - Process multiple workflows simultaneously
   - Assign preferences (performance/balanced/energy) to each workflow
   - Handle dependencies within and across workflows

2. HEFT Implementation:
   - Calculate upward rank for task prioritization
   - Consider communication costs and execution times
   - Resource-aware scheduling
   - Dependency-aware scheduling

3. Preference-based Scheduling:
   - Performance-oriented workflows get priority
   - Balanced workflows scheduled second
   - Energy-efficient workflows scheduled last
   - Within each preference level, use HEFT ranking

Usage:
-----
python3 scheduler.py --resources <resource_file> \
    -workflow <workflow_folder1> <preference1> \
    -workflow <workflow_folder2> <preference2> \
    --output <output_file>

Arguments:
---------
--resources : Path to resource definition file
--output   : Path for output schedule file (CSV)
-workflow  : Workflow folder path and preference (can be specified multiple times)

Preferences:
----------
- performance: Highest priority, scheduled first
- balanced: Medium priority, scheduled second
- energy: Lowest priority, scheduled last

Input Requirements:
----------------
1. Resource File:
   - One resource per line
   - Each resource should be a valid execution node

2. Workflow Folders:
   - Must contain exactly one .dag file
   - DAG file should follow HTCondor DAGMan syntax
   - Jobs in DAG should map to defined job types

Job Type Definitions:
------------------
Predefined job types with execution and communication costs:
- create_dir_montage: Directory creation jobs
- stage_in/stage_out: Data staging jobs
- mProject: Image projection
- mDiffFit: Image difference and fitting
- mConcatFit: Result concatenation
- mBgModel: Background model computation
- mBackground: Background correction
- mImgtbl: Image table creation
- mAdd: Image addition
- mViewer: Image visualization

Output:
------
1. CSV Schedule File:
   - execution_number: Order of execution (1 to N)
   - workflow_id: Identifier for the workflow
   - workflow_folder_path: Absolute path to workflow folder
   - job_name: Name of the job from DAG
   - preference: Workflow preference level
   - assigned_resource: Allocated resource
   - estimated_start: Expected start time
   - estimated_finish: Expected finish time
   - upward_rank: HEFT rank value

2. Summary File:
   - Total number of jobs
   - Total dependencies
   - Makespan (total execution time)
   - List of processed workflows

Error Handling:
-------------
- Validates resource file existence and content
- Checks for DAG file presence in workflow folders
- Validates workflow preferences
- Reports parsing errors for DAG files
- Creates detailed error messages

Dependencies:
-----------
Standard Python libraries:
- argparse: Command line argument parsing
- os: File and path operations
- csv: CSV file handling
- sys: System-specific parameters
- glob: File pattern matching
- typing: Type hints
- dataclasses: Data class decorators
- collections: Specialized container datatypes
- pathlib: Object-oriented filesystem paths

Authors:
-------
Created for EMWOS Workflow Management System by Mehul Warade
Nodember 7, 2024
"""

import argparse
import os
import csv
import sys
import glob
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
from pathlib import Path

# Job execution and communication costs remain the same
JOB_INFO = {
    'create_dir_montage': {'exec_time': 0, 'comm_before': 0, 'comm_after': 0},
    'stage_in': {'exec_time': 0, 'comm_before': 0, 'comm_after': 0},
    'stage_out': {'exec_time': 0, 'comm_before': 0, 'comm_after': 0},
    'mProject': {'exec_time': 599.75, 'comm_before': 18, 'comm_after': 3},
    'mDiffFit': {'exec_time': 46.23, 'comm_before': 46, 'comm_after': 2},
    'mConcatFit': {'exec_time': 10.0, 'comm_before': 30, 'comm_after': 2},
    'mBgModel': {'exec_time': 12.5, 'comm_before': 46, 'comm_after': 2},
    'mBackground': {'exec_time': 38.0, 'comm_before': 13, 'comm_after': 2},
    'mImgtbl': {'exec_time': 17.5, 'comm_before': 31, 'comm_after': 2},
    'mAdd': {'exec_time': 25.0, 'comm_before': 173, 'comm_after': 7},
    'mViewer': {'exec_time': 16.66, 'comm_before': 5, 'comm_after': 2}
}

@dataclass
class Job:
    name: str
    type: str
    workflow_id: str
    preference: str
    workflow_folder: str
    priority: int = 0
    upward_rank: float = 0.0
    execution_number: int = 0
    estimated_start: float = 0.0
    estimated_finish: float = 0.0
    assigned_resource: str = ""

class DAGScheduler:
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.dependencies: Dict[str, List[str]] = defaultdict(list)
        self.reverse_dependencies: Dict[str, List[str]] = defaultdict(list)
        self.resources: List[str] = []
        self.execution_counter: int = 1

    def read_resources(self, resource_file: str):
        """Read resource file containing slot definitions."""
        try:
            with open(resource_file, 'r') as f:
                self.resources = [line.strip() for line in f if line.strip()]
            if not self.resources:
                raise ValueError("Resource file is empty")
        except (FileNotFoundError, IOError) as e:
            print(f"Error reading resource file: {e}")
            sys.exit(1)

    def find_dag_file(self, workflow_folder: str) -> str:
        """Find the .dag file in the workflow folder."""
        try:
            dag_files = glob.glob(os.path.join(workflow_folder, "*.dag"))
            if not dag_files:
                raise FileNotFoundError(f"No .dag file found in {workflow_folder}")
            if len(dag_files) > 1:
                print(f"Warning: Multiple DAG files found in {workflow_folder}. Using {dag_files[0]}")
            return dag_files[0]
        except Exception as e:
            print(f"Error finding DAG file in {workflow_folder}: {e}")
            sys.exit(1)

    def parse_workflow_folder(self, workflow_folder: str, preference: str, workflow_id: str):
        """Parse workflow folder and find DAG file."""
        try:
            abs_workflow_path = os.path.abspath(workflow_folder)
            dag_file = self.find_dag_file(abs_workflow_path)
            
            with open(dag_file, 'r') as f:
                content = f.read()

            for line in content.split('\n'):
                if line.startswith('JOB'):
                    parts = line.split()
                    if len(parts) < 2:
                        print(f"Warning: Invalid JOB line in {dag_file}: {line}")
                        continue
                    
                    job_name = parts[1]
                    job_type = job_name.split('_')[0] if '_' in job_name else job_name
                    full_job_name = f"{workflow_id}:{job_name}"
                    
                    self.jobs[full_job_name] = Job(
                        name=job_name,
                        type=job_type,
                        workflow_id=workflow_id,
                        preference=preference,
                        workflow_folder=abs_workflow_path
                    )
                
                elif line.startswith('PARENT'):
                    parts = line.split()
                    if len(parts) < 4 or 'CHILD' not in parts:
                        print(f"Warning: Invalid PARENT line in {dag_file}: {line}")
                        continue
                    
                    parent = f"{workflow_id}:{parts[1]}"
                    child_idx = parts.index('CHILD') + 1
                    children = [f"{workflow_id}:{child}" for child in parts[child_idx:]]
                    
                    self.dependencies[parent].extend(children)
                    for child in children:
                        self.reverse_dependencies[child].append(parent)

        except FileNotFoundError:
            print(f"Error: Workflow folder not found: {workflow_folder}")
            sys.exit(1)
        except Exception as e:
            print(f"Error parsing workflow folder {workflow_folder}: {e}")
            sys.exit(1)

    def calculate_upward_rank(self, job_id: str, memo: Dict[str, float] = None) -> float:
        """Calculate upward rank of a job using memoization."""
        if memo is None:
            memo = {}
            
        if job_id in memo:
            return memo[job_id]
            
        job = self.jobs[job_id]
        job_info = JOB_INFO.get(job.type, {'exec_time': 0, 'comm_before': 0, 'comm_after': 0})
        
        if job_id not in self.dependencies:
            rank = job_info['exec_time']
        else:
            max_child_rank = 0
            for child in self.dependencies[job_id]:
                child_rank = self.calculate_upward_rank(child, memo)
                child_comm_cost = JOB_INFO.get(self.jobs[child].type, {}).get('comm_before', 0)
                max_child_rank = max(max_child_rank, child_rank + child_comm_cost)
            
            rank = job_info['exec_time'] + max_child_rank
            
        memo[job_id] = rank
        self.jobs[job_id].upward_rank = rank
        return rank

    def are_dependencies_scheduled(self, job_id: str) -> bool:
        """Check if all parent jobs are scheduled."""
        return all(self.jobs[parent].execution_number != 0 
                  for parent in self.reverse_dependencies[job_id])

    def are_higher_preferences_scheduled(self, job: Job, available_jobs: Set[str]) -> bool:
        """Check if all higher preference jobs are scheduled."""
        if job.preference == 'performance':
            return True
        
        for available_job_id in available_jobs:
            available_job = self.jobs[available_job_id]
            if available_job.preference == 'performance' and available_job.execution_number == 0:
                return False
            
        if job.preference == 'balanced':
            return True
            
        for available_job_id in available_jobs:
            available_job = self.jobs[available_job_id]
            if available_job.preference in ['performance', 'balanced'] and available_job.execution_number == 0:
                return False
                
        return True

    def schedule_jobs(self) -> None:
        """Schedule all jobs considering preferences and dependencies."""
        # Calculate upward ranks for all jobs
        for job_id in self.jobs:
            self.calculate_upward_rank(job_id)

        resource_available_time = {resource: 0 for resource in self.resources}
        
        while True:
            unscheduled = {job_id for job_id, job in self.jobs.items() 
                          if job.execution_number == 0}
            if not unscheduled:
                break
                
            available_jobs = {job_id for job_id in unscheduled 
                            if self.are_dependencies_scheduled(job_id)}
            if not available_jobs:
                break
                
            best_job_id = None
            best_rank = -1
            
            for job_id in available_jobs:
                job = self.jobs[job_id]
                
                if not self.are_higher_preferences_scheduled(job, available_jobs):
                    continue
                    
                if job.upward_rank > best_rank:
                    best_rank = job.upward_rank
                    best_job_id = job_id
            
            if best_job_id is None:
                break
                
            job = self.jobs[best_job_id]
            job_info = JOB_INFO.get(job.type, {'exec_time': 0, 'comm_before': 0, 'comm_after': 0})
            
            earliest_time = float('inf')
            best_resource = None
            
            for resource in self.resources:
                start_time = resource_available_time[resource]
                
                for parent_id in self.reverse_dependencies[best_job_id]:
                    parent = self.jobs[parent_id]
                    parent_completion = parent.estimated_finish
                    if parent.assigned_resource != resource:
                        parent_completion += JOB_INFO.get(parent.type, {}).get('comm_after', 0)
                    start_time = max(start_time, parent_completion)
                
                if start_time < earliest_time:
                    earliest_time = start_time
                    best_resource = resource
            
            job.execution_number = self.execution_counter
            job.estimated_start = earliest_time
            job.estimated_finish = earliest_time + job_info['exec_time']
            job.assigned_resource = best_resource
            
            resource_available_time[best_resource] = job.estimated_finish
            self.execution_counter += 1
    def write_schedule(self, output_file: str):
        """Write the schedule to a CSV file."""
        fieldnames = [
            'execution_number',
            'workflow_id',
            'workflow_folder_path',
            'job_name',
            'preference',
            'assigned_resource',
            'estimated_start',
            'estimated_finish',
            'upward_rank'
        ]

        try:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                sorted_jobs = sorted(self.jobs.values(), key=lambda x: x.execution_number)
                
                for job in sorted_jobs:
                    writer.writerow({
                        'execution_number': job.execution_number,
                        'workflow_id': job.workflow_id,
                        'workflow_folder_path': job.workflow_folder,
                        'job_name': job.name,
                        'preference': job.preference,
                        'assigned_resource': job.assigned_resource,
                        'estimated_start': f"{job.estimated_start:.2f}",
                        'estimated_finish': f"{job.estimated_finish:.2f}",
                        'upward_rank': f"{job.upward_rank:.2f}"
                    })

            summary_file = f"{os.path.splitext(output_file)[0]}_summary.txt"
            with open(summary_file, 'w') as f:
                f.write("Schedule Summary:\n")
                f.write("-" * 40 + "\n")
                makespan = max(job.estimated_finish for job in self.jobs.values())
                f.write(f"Total Jobs: {len(self.jobs)}\n")
                f.write(f"Total Dependencies: {sum(len(deps) for deps in self.dependencies.values())}\n")
                f.write(f"Makespan: {makespan:.2f} seconds\n")
                f.write("\nWorkflow Folders Processed:\n")
                unique_workflows = {job.workflow_folder: job.workflow_id for job in sorted_jobs}
                for folder, wf_id in unique_workflows.items():
                    f.write(f"{wf_id}: {folder}\n")

        except IOError as e:
            print(f"Error writing schedule to file: {e}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Multi-DAG HEFT Scheduler with Preferences")
    parser.add_argument("--resources", required=True, help="Path to resources file")
    parser.add_argument("--output", default="schedule.csv", help="Output schedule file (CSV)")
    parser.add_argument("-workflow", action='append', nargs=2, metavar=('folder', 'preference'),
                       help="Workflow folder path and preference (performance/balanced/energy)")
    
    args = parser.parse_args()
    
    if not args.workflow:
        print("Error: At least one workflow folder must be specified")
        parser.print_help()
        sys.exit(1)
    
    scheduler = DAGScheduler()
    scheduler.read_resources(args.resources)
    
    for i, (workflow_folder, preference) in enumerate(args.workflow):
        if preference not in ['performance', 'balanced', 'energy']:
            print(f"Warning: Invalid preference '{preference}' for {workflow_folder}. Using 'balanced'.")
            preference = 'balanced'
        
        workflow_id = f"workflow_{i+1}"
        scheduler.parse_workflow_folder(workflow_folder, preference, workflow_id)
    
    scheduler.schedule_jobs()
    scheduler.write_schedule(args.output)
    
    print(f"Schedule has been written to {args.output}")
    print(f"Summary has been written to {os.path.splitext(args.output)[0]}_summary.txt")

if __name__ == "__main__":
    main()