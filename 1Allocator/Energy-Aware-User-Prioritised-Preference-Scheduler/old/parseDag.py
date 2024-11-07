import argparse
import os
import re
from collections import defaultdict
from typing import Dict, List, Set, DefaultDict

def parse_resources_file(file_path: str) -> Dict:
    """
    Parse the resources file containing slot definitions.
    Returns a dictionary with host information and slot counts.
    """
    resources = defaultdict(set)
    total_slots = 0
    hosts = set()
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                # Expected format: slotN@hostname
                match = re.match(r'slot(\d+)@(\w+)', line)
                if match:
                    slot_num, hostname = match.groups()
                    resources[hostname].add(int(slot_num))
                    hosts.add(hostname)
                    total_slots += 1
    
    # Convert to regular dict for return
    return {
        'slots_by_host': dict(resources),
        'total_slots': total_slots,
        'total_hosts': len(hosts),
        'hosts': sorted(list(hosts))
    }

def parse_dag_file(file_path: str) -> Dict:
    """Parse a DAG file and extract job and dependency information."""
    dag_info = {
        'jobs': set(),
        'dependencies': [],
        'resources': defaultdict(dict),
        'line_count': 0,
        'slot_requests': defaultdict(int)  # Track slot requests per job
    }
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
        dag_info['line_count'] = len(lines)
        
        for line in lines:
            line = line.strip()
            
            # Extract job definitions
            job_match = re.search(r'JOB\s+(\w+)\s+', line)
            if job_match:
                dag_info['jobs'].add(job_match.group(1))
            
            # Extract dependencies
            parent_match = re.search(r'PARENT\s+(\w+)\s+CHILD\s+(\w+)', line)
            if parent_match:
                dag_info['dependencies'].append({
                    'parent': parent_match.group(1),
                    'child': parent_match.group(2)
                })
            
            # Extract slot requirements
            slot_match = re.search(r'(\w+)\s+request_slots\s*=\s*(\d+)', line)
            if slot_match:
                job, slots = slot_match.groups()
                dag_info['slot_requests'][job] = int(slots)
    
    return dag_info

def analyze_dags(dag_files: List[str], resources_file: str) -> None:
    """Analyze multiple DAG files and print comprehensive information about slots and dependencies."""
    total_jobs = 0
    total_dependencies = 0
    
    # Parse resources file
    try:
        resources = parse_resources_file(resources_file)
        print("\nResource Information:")
        print("-" * 50)
        print(f"Total Available Slots: {resources['total_slots']}")
        print(f"Total Hosts: {resources['total_hosts']}")
        print("\nSlots per Host:")
        for host in resources['hosts']:
            slots = resources['slots_by_host'][host]
            print(f"  {host}: {len(slots)} slots (slots {min(slots)}-{max(slots)})")
    except FileNotFoundError:
        print(f"\nWarning: Resources file '{resources_file}' not found")
        resources = None
    
    print("\nDAG Analysis:")
    print("-" * 50)
    
    for dag_file in dag_files:
        try:
            print(f"\nAnalyzing DAG: {dag_file}")
            print("=" * 40)
            
            dag_info = parse_dag_file(dag_file)
            
            # Print basic statistics
            print(f"Number of jobs: {len(dag_info['jobs'])}")
            print(f"Number of dependencies: {len(dag_info['dependencies'])}")
            
            # Print jobs and their slot requests
            print("\nJobs and Resource Requests:")
            for job in sorted(dag_info['jobs']):
                slots = dag_info['slot_requests'].get(job, 'Not specified')
                print(f"  - {job}: {slots} slots")
            
            # Print dependencies
            if dag_info['dependencies']:
                print("\nDependencies:")
                for dep in dag_info['dependencies']:
                    print(f"  {dep['parent']} -> {dep['child']}")
            
            # Analyze slot usage
            if resources and dag_info['slot_requests']:
                print("\nSlot Usage Analysis:")
                max_requested = max(dag_info['slot_requests'].values(), default=0)
                print(f"  Maximum slots requested by any job: {max_requested}")
                if max_requested > resources['total_slots']:
                    print(f"  WARNING: Some jobs request more slots than available!")
            
            total_jobs += len(dag_info['jobs'])
            total_dependencies += len(dag_info['dependencies'])
            
        except FileNotFoundError:
            print(f"Error: DAG file '{dag_file}' not found")
        except Exception as e:
            print(f"Error processing '{dag_file}': {str(e)}")
    
    # Print summary
    print("\nOverall Summary:")
    print("-" * 50)
    print(f"Total DAGs analyzed: {len(dag_files)}")
    print(f"Total jobs across all DAGs: {total_jobs}")
    print(f"Total dependencies across all DAGs: {total_dependencies}")

def main():
    parser = argparse.ArgumentParser(description='Analyze DAG files and slot-based resource requirements')
    parser.add_argument('dag_files', nargs='+', help='Path to DAG files')
    parser.add_argument('--resources', help='Path to resources file containing slot definitions')
    
    args = parser.parse_args()
    analyze_dags(args.dag_files, args.resources)

if __name__ == "__main__":
    main()