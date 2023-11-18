import re
import csv
from datetime import datetime

# Define regular expressions for extracting information
job_number_pattern = re.compile(r'^\d+\s+\(([\d.]+)\)')
node_pattern = re.compile(r'<([\d.]+):(\d+)\?addrs=([\d.]+)-(\d+)&alias=([\w]+)&noUDP&sock=([\w_]+)>')
dag_node_pattern = re.compile(r'DAG Node: (.+)')
slot_name_pattern = re.compile(r'SlotName: (.+)')
scratch_dir_pattern = re.compile(r'CondorScratchDir = "(.+)"')
cpus_pattern = re.compile(r'Cpus = (\d+)')
disk_pattern = re.compile(r'Disk = (\d+)')
memory_pattern = re.compile(r'Memory = (\d+)')
image_size_pattern = re.compile(r'Image size of job updated: (\d+)')
termination_pattern = re.compile(r'Job terminated of its own accord at (.+) with exit-code (\d+)')
job_start_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Job submitted from host:')

# Initialize data structure to store extracted information
job_data = []

# Open the log file for reading
with open('a.log', 'r') as file:
    lines = file.readlines()

    current_job = None
    dag_node = None
    submission_node_ip = None
    submission_node_alias = None
    execution_node_ip = None
    execution_node_alias = None
    start_time = None
    input_transfer_time = None
    output_transfer_time = None
    execution_time = None
    scratch_dir = None
    requested_cpus = None
    requested_disk = None
    requested_memory = None
    actual_cpus = None
    actual_disk = None
    actual_memory = None

    job_info = {}  # Dictionary to store information for the current job

    for line in lines:
        job_number_match = job_number_pattern.match(line)
        node_match = node_pattern.search(line)
        dag_node_match = dag_node_pattern.search(line)
        slot_name_match = slot_name_pattern.search(line)
        scratch_dir_match = scratch_dir_pattern.search(line)
        cpus_match = cpus_pattern.search(line)
        disk_match = disk_pattern.search(line)
        memory_match = memory_pattern.search(line)
        image_size_match = image_size_pattern.search(line)
        termination_match = termination_pattern.search(line)
        job_start_match = job_start_pattern.search(line)
        if job_number_match:
            if current_job:
                job_data.append([current_job, dag_node, submission_node_ip, submission_node_alias, execution_node_ip, execution_node_alias,
                                 input_transfer_time, output_transfer_time, execution_time, scratch_dir,
                                 requested_cpus, requested_disk, requested_memory, actual_cpus, actual_disk, actual_memory])

            current_job = job_number_match.group(1)
            dag_node = None
            job_info = {}

        if node_match:
            if 'Job submitted' in line:
                submission_node_ip = node_match.group(1)
                submission_node_port = node_match.group(2)
                submission_node_alias = node_match.group(5)
            elif 'Job executing' in line:
                execution_node_ip = node_match.group(1)
                execution_node_port = node_match.group(2)
                execution_node_alias = node_match.group(5)

        if job_start_match:
            start_time = datetime.strptime(job_start_match.group(1), '%Y-%m-%d %H:%M:%S')
            start_timestamp = int(start_time.timestamp())
            print(start_timestamp)

        if dag_node_match:
            dag_node = dag_node_match.group(1)

        if slot_name_match:
            slot_name = slot_name_match.group(1)

        if scratch_dir_match:
            scratch_dir = scratch_dir_match.group(1)

        if cpus_match:
            requested_cpus = cpus_match.group(1)

        if disk_match:
            requested_disk = disk_match.group(1)

        if memory_match:
            requested_memory = memory_match.group(1)

        if image_size_match:
            image_size = image_size_match.group(1)

        if termination_match:
            end_time = datetime.strptime(termination_match.group(1), '%Y-%m-%dT%H:%M:%SZ')
            exit_code = termination_match.group(2)
            end_timestamp = int(end_time.timestamp())
            print(end_timestamp)
            execution_time = end_timestamp - start_timestamp
            print(execution_time)

# Write the extracted data to a CSV file
with open('output.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Job Number', 'DAG Node', 'Submission Node IP', 'Submission Node Alias', 'Execution Node IP', 'Execution Node Alias',
                     'Input Transfer Time', 'Output Transfer Time', 'Execution Time', 'Scratch Directory',
                     'Requested CPUs', 'Requested Disk', 'Requested Memory', 'Actual CPUs', 'Actual Disk', 'Actual Memory'])
    
    # Create a dictionary to store the last value for each ID
    last_values = {}

    # Iterate through the data in reverse order
    for entry in reversed(job_data):
        unique_id = entry[0]
        if unique_id not in last_values:
            last_values[unique_id] = entry
        else:
            # Replace the entry if a newer one is found
            last_values[unique_id] = entry

    # Convert the dictionary values back to a list
    result = list(last_values.values())
    
    writer.writerows(result)
