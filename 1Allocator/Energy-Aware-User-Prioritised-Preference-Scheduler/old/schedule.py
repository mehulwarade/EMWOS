#!/usr/bin/env python3

import argparse
import os
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

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
    dag_id: str
    preference: str
    priority: int = 0
    upward_rank: float = 0.0
    execution_number: int = 0
    estimated_start: float = 0.0
    estimated_finish: float = 0.0
    assigned_resource: str = ""

class DAGScheduler:
    def __init__(self):
        self.jobs: Dict[str, Job] = {}  # job_name -> Job
        self.dependencies: Dict[str, List[str]] = defaultdict(list)  # parent -> [children]
        self.reverse_dependencies: Dict[str, List[str]] = defaultdict(list)  # child -> [parents]
        self.resources: List[str] = []
        self.execution_counter: int = 1

    def read_resources(self, resource_file: str):
        """Read resource file containing slot definitions."""
        with open(resource_file, 'r') as f:
            self.resources = [line.strip() for line in f if line.strip()]

    def parse_dag_file(self, dag_file: str, preference: str, dag_id: str):
        """Parse a DAG file and add its jobs and dependencies."""
        with open(dag_file, 'r') as f:
            content = f.read()

        for line in content.split('\n'):
            if line.startswith('JOB'):
                parts = line.split()
                job_name = parts[1]
                job_type = job_name.split('_')[0] if '_' in job_name else job_name
                full_job_name = f"{dag_id}:{job_name}"
                
                self.jobs[full_job_name] = Job(
                    name=job_name,
                    type=job_type,
                    dag_id=dag_id,
                    preference=preference
                )
            
            elif line.startswith('PARENT'):
                parts = line.split()
                parent = f"{dag_id}:{parts[1]}"
                children = [f"{dag_id}:{child}" for child in parts[3:] if child != 'CHILD']
                
                self.dependencies[parent].extend(children)
                for child in children:
                    self.reverse_dependencies[child].append(parent)

    def calculate_upward_rank(self, job_id: str, memo: Dict[str, float] = None) -> float:
        """Calculate upward rank of a job using memoization."""
        if memo is None:
            memo = {}
            
        if job_id in memo:
            return memo[job_id]
            
        job = self.jobs[job_id]
        job_info = JOB_INFO.get(job.type, {'exec_time': 0, 'comm_before': 0, 'comm_after': 0})
        
        # If no children, return just the execution time
        if job_id not in self.dependencies:
            rank = job_info['exec_time']
        else:
            # Calculate maximum rank among children
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
        for parent in self.reverse_dependencies[job_id]:
            if self.jobs[parent].execution_number == 0:
                return False
        return True

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
            
        # For energy preference, check if any performance or balanced jobs are unscheduled
        for available_job_id in available_jobs:
            available_job = self.jobs[available_job_id]
            if available_job.preference in ['performance', 'balanced'] and available_job.execution_number == 0:
                return False
                
        return True

    def schedule_jobs(self) -> None:
        """Schedule all jobs considering preferences and dependencies."""
        # Calculate upward ranks for all jobs
        for job_id in self.jobs:
            if job_id not in self.jobs:
                self.calculate_upward_rank(job_id)

        # Track available resources and their earliest available time
        resource_available_time = {resource: 0 for resource in self.resources}
        
        while True:
            # Get all unscheduled jobs
            unscheduled = {job_id for job_id, job in self.jobs.items() if job.execution_number == 0}
            if not unscheduled:
                break
                
            # Find available jobs (those with all dependencies scheduled)
            available_jobs = {job_id for job_id in unscheduled if self.are_dependencies_scheduled(job_id)}
            if not available_jobs:
                break  # No more jobs can be scheduled
                
            # Find the best job to schedule next
            best_job_id = None
            best_rank = -1
            
            for job_id in available_jobs:
                job = self.jobs[job_id]
                
                # Check preferences
                if not self.are_higher_preferences_scheduled(job, available_jobs):
                    continue
                    
                # Among eligible jobs, pick the one with highest rank
                if job.upward_rank > best_rank:
                    best_rank = job.upward_rank
                    best_job_id = job_id
            
            if best_job_id is None:
                break
                
            # Schedule the selected job
            job = self.jobs[best_job_id]
            job_info = JOB_INFO.get(job.type, {'exec_time': 0, 'comm_before': 0, 'comm_after': 0})
            
            # Find the earliest available resource
            earliest_time = float('inf')
            best_resource = None
            
            for resource in self.resources:
                # Calculate earliest possible start time on this resource
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
            
            # Assign the job
            job.execution_number = self.execution_counter
            job.estimated_start = earliest_time
            job.estimated_finish = earliest_time + job_info['exec_time']
            job.assigned_resource = best_resource
            
            # Update resource availability
            resource_available_time[best_resource] = job.estimated_finish
            
            self.execution_counter += 1

    def write_schedule(self, output_file: str):
        """Write the schedule to a file."""
        with open(output_file, 'w') as f:
            f.write("Schedule Details:\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'DAG ID':<15} {'Job Name':<20} {'Preference':<12} {'Exec #':<8} "
                   f"{'Resource':<15} {'Start':<10} {'Finish':<10} {'Upward Rank':<12}\n")
            f.write("-" * 80 + "\n")
            
            # Sort by execution number
            sorted_jobs = sorted(self.jobs.values(), key=lambda x: x.execution_number)
            
            for job in sorted_jobs:
                f.write(f"{job.dag_id:<15} {job.name:<20} {job.preference:<12} {job.execution_number:<8} "
                       f"{job.assigned_resource:<15} {job.estimated_start:<10.2f} {job.estimated_finish:<10.2f} "
                       f"{job.upward_rank:<12.2f}\n")
            
            # Write summary statistics
            f.write("\nSchedule Summary:\n")
            f.write("-" * 40 + "\n")
            makespan = max(job.estimated_finish for job in self.jobs.values())
            f.write(f"Total Jobs: {len(self.jobs)}\n")
            f.write(f"Total Dependencies: {sum(len(deps) for deps in self.dependencies.values())}\n")
            f.write(f"Makespan: {makespan:.2f} seconds\n")

def main():
    parser = argparse.ArgumentParser(description="Multi-DAG HEFT Scheduler with Preferences")
    parser.add_argument("--resources", required=True, help="Path to resources file")
    parser.add_argument("--output", default="schedule.txt", help="Output schedule file")
    
    # Allow multiple DAG specifications with preferences
    parser.add_argument("-dag", action='append', nargs=2, metavar=('path', 'preference'),
                       help="DAG file path and preference (performance/balanced/energy)")
    
    args = parser.parse_args()
    
    scheduler = DAGScheduler()
    scheduler.read_resources(args.resources)
    
    # Parse each DAG file
    for i, (dag_file, preference) in enumerate(args.dag):
        if preference not in ['performance', 'balanced', 'energy']:
            print(f"Warning: Invalid preference '{preference}' for {dag_file}. Using 'balanced'.")
            preference = 'balanced'
        
        dag_id = f"dag_{i+1}"
        scheduler.parse_dag_file(dag_file, preference, dag_id)
    
    # Schedule all jobs
    scheduler.schedule_jobs()
    
    # Write the schedule
    scheduler.write_schedule(args.output)
    print(f"Schedule has been written to {args.output}")

if __name__ == "__main__":
    main()