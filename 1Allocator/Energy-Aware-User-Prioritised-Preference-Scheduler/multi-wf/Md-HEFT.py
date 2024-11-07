#!/usr/bin/env python3

"""
Basic Multi-DAG HEFT Scheduler

This script implements a pure HEFT (Heterogeneous Earliest Finish Time) algorithm 
for scheduling multiple workflows. Unlike the preference-based version, this implementation
focuses solely on optimizing the schedule based on task dependencies and execution costs.

Features:
---------
1. Multi-workflow support
2. Pure HEFT implementation
3. Resource-aware scheduling
4. Dependency-preserving execution order
5. CSV-based output

Usage:
-----
python3 basic_heft.py --resources <resource_file> \
    -workflow <workflow_folder1> \
    -workflow <workflow_folder2> \
    --output <output_file>
"""

import argparse
import os
import csv
import sys
import glob
from typing import Dict, List, Set
from dataclasses import dataclass
from collections import defaultdict
from pathlib import Path

# Job execution and communication costs
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
    workflow_folder: str
    upward_rank: float = 0.0
    execution_number: int = 0
    estimated_start: float = 0.0
    estimated_finish: float = 0.0
    assigned_resource: str = ""

class HEFTScheduler:
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

    def parse_workflow_folder(self, workflow_folder: str, workflow_id: str):
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

    def schedule_jobs(self) -> None:
        """Schedule all jobs based purely on HEFT algorithm."""
        # Calculate upward ranks for all jobs
        for job_id in self.jobs:
            self.calculate_upward_rank(job_id)

        resource_available_time = {resource: 0 for resource in self.resources}
        
        while True:
            # Get unscheduled jobs
            unscheduled = {job_id for job_id, job in self.jobs.items() 
                          if job.execution_number == 0}
            if not unscheduled:
                break
                
            # Get jobs with all dependencies scheduled
            available_jobs = {job_id for job_id in unscheduled 
                            if self.are_dependencies_scheduled(job_id)}
            if not available_jobs:
                break
                
            # Find job with highest upward rank
            best_job_id = max(available_jobs, 
                            key=lambda job_id: self.jobs[job_id].upward_rank)
            
            job = self.jobs[best_job_id]
            job_info = JOB_INFO.get(job.type, {'exec_time': 0, 'comm_before': 0, 'comm_after': 0})
            
            # Find earliest available resource
            earliest_time = float('inf')
            best_resource = None
            
            for resource in self.resources:
                start_time = resource_available_time[resource]
                
                # Consider parent completion times
                for parent_id in self.reverse_dependencies[best_job_id]:
                    parent = self.jobs[parent_id]
                    parent_completion = parent.estimated_finish
                    if parent.assigned_resource != resource:
                        parent_completion += JOB_INFO.get(parent.type, {}).get('comm_after', 0)
                    start_time = max(start_time, parent_completion)
                
                if start_time < earliest_time:
                    earliest_time = start_time
                    best_resource = resource
            
            # Assign job to resource
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
    parser = argparse.ArgumentParser(description="Basic Multi-DAG HEFT Scheduler")
    parser.add_argument("--resources", required=True, help="Path to resources file")
    parser.add_argument("--output", default="schedule.csv", help="Output schedule file (CSV)")
    parser.add_argument("-workflow", action='append', metavar='folder',
                       help="Workflow folder path")
    
    args = parser.parse_args()
    
    if not args.workflow:
        print("Error: At least one workflow folder must be specified")
        parser.print_help()
        sys.exit(1)
    
    scheduler = HEFTScheduler()
    scheduler.read_resources(args.resources)
    
    for i, workflow_folder in enumerate(args.workflow):
        workflow_id = f"workflow_{i+1}"
        scheduler.parse_workflow_folder(workflow_folder, workflow_id)
    
    scheduler.schedule_jobs()
    scheduler.write_schedule(args.output)
    
    print(f"Schedule has been written to {args.output}")
    print(f"Summary has been written to {os.path.splitext(args.output)[0]}_summary.txt")

if __name__ == "__main__":
    main()