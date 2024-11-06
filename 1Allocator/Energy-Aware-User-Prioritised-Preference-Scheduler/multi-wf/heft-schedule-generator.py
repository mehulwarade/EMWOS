#!/usr/bin/env python3

#usage: python script_name.py path_to_dag_file path_to_resources_file path_to_output_file

#usage: ./heft-schedule-generator.py run0043/montage-0.dag resources.txt heft-schedule.txt


import argparse
import os

# Function to read the DAG file
def read_dag_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def read_resource_file(file_path):
    resources = []
    with open(file_path, 'r') as f:
        for line in f:
            name, processor = line.strip().split(',')
            resources.append(name)
    return resources

# Parse the DAG file
def parse_dag_file(content):
    jobs = {}
    dependencies = {}
    
    for line in content.split('\n'):
        if line.startswith('JOB'):
            parts = line.split()
            job_name = parts[1]
            job_type = job_name.split('_')[0] if '_' in job_name else job_name
            jobs[job_name] = {'name': job_name, 'type': job_type, 'priority': 0}
        elif line.startswith('PARENT'):
            parts = line.split()
            parent = parts[1]
            children = parts[3:]
            for child in children:
                if child != 'CHILD':
                    if parent not in dependencies:
                        dependencies[parent] = []
                    dependencies[parent].append(child)
        elif line.startswith('PRIORITY'):
            parts = line.split()
            job_name = parts[1]
            priority = int(parts[2])
            jobs[job_name]['priority'] = priority

    return jobs, dependencies

# Define execution times and communication costs for job types
job_info = {
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

# Generate execution times and communication costs for each job
execution_times = {}
comm_costs_before = {}
comm_costs_after = {}

def calculate_upward_rank(job):
    if job not in dependencies:
        return execution_times[job][resources[0]] + comm_costs_after[job]
    
    max_rank = 0
    for successor in dependencies.get(job, []):
        rank = calculate_upward_rank(successor)
        max_rank = max(max_rank, rank)
    
    return execution_times[job][resources[0]] + comm_costs_after[job] + max_rank

def heft():
    upward_ranks = {job: calculate_upward_rank(job) for job in jobs}
    sorted_jobs = sorted(upward_ranks, key=upward_ranks.get, reverse=True)
    
    schedule = {}
    resource_available_time = {resource: 0 for resource in resources}
    
    for job in sorted_jobs:
        est = {}
        eft = {}
        
        for resource in resources:
            est[resource] = resource_available_time[resource] + comm_costs_before[job]
            for parent in jobs:
                if job in dependencies.get(parent, []):
                    if parent in schedule:
                        parent_eft = schedule[parent]['eft']
                        parent_resource = schedule[parent]['resource']
                        comm_cost = comm_costs_after[parent] if parent_resource != resource else 0
                        est[resource] = max(est[resource], parent_eft + comm_cost)
            
            eft[resource] = est[resource] + execution_times[job][resource]
        
        selected_resource = min(eft, key=eft.get)
        
        schedule[job] = {
            'resource': selected_resource,
            'est': est[selected_resource],
            'eft': eft[selected_resource]
        }
        resource_available_time[selected_resource] = eft[selected_resource]
    
    return schedule

def main(dag_file, resource_file, output_file):
    # Read the DAG file
    dag_content = read_dag_file(dag_file)

    # Parse the DAG content
    global jobs, dependencies, resources
    jobs, dependencies = parse_dag_file(dag_content)

    # Define resources
    resources = read_resource_file(resource_file)

    # Generate execution times and communication costs for each job
    global execution_times, comm_costs_before, comm_costs_after

    for job, info in jobs.items():
        job_type = info['type']
        job_data = job_info.get(job_type, {'exec_time': 0, 'comm_before': 0, 'comm_after': 0})
        execution_times[job] = {resource: job_data['exec_time'] for resource in resources}
        comm_costs_before[job] = job_data['comm_before']
        comm_costs_after[job] = job_data['comm_after']

    # Run HEFT algorithm
    result = heft()

    # Write the schedule to the file
    with open(output_file, 'w') as output_file:
        for job, info in result.items():
            output_file.write(f"Job {job}: Resource {info['resource']}, Start: {info['est']:.2f}, Finish: {info['eft']:.2f}\n")

    # Print the schedule
    for job, info in result.items():
        print(f"Job {job}: Resource {info['resource']}, Start: {info['est']:.2f}, Finish: {info['eft']:.2f}")

    # Print some statistics
    print(f"\nTotal jobs: {len(jobs)}")
    print(f"Total dependencies: {sum(len(deps) for deps in dependencies.values())}")

    # Calculate makespan
    makespan = max(info['eft'] for info in result.values())
    print(f"Makespan: {makespan:.2f} seconds")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HEFT Scheduling Algorithm")
    parser.add_argument("dag_file", type=str, help="Path to the DAG file")
    parser.add_argument("resource_file", type=str, help="Path to the resources file")
    parser.add_argument("output_file", type=str, help="Path to the output file")

    args = parser.parse_args()
    main(args.dag_file, args.resource_file, args.output_file)
