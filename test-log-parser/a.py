from datetime import datetime

def parse_log_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    job_data = {}
    current_job_id = None

    for line in lines:
        if line.startswith('000'):
            current_job_id = line.split()[1]
            job_data[current_job_id] = {'events': []}
        else:
            job_data[current_job_id]['events'].append(line.strip())

    return job_data

def get_input_transfer_time(events):
    start_time = None
    end_time = None

    for event in events:
        if "Started transferring input files" in event:
            start_time = datetime.strptime(event.split()[2] + ' ' + event.split()[3], "%Y-%m-%d %H:%M:%S")
        elif "Finished transferring input files" in event:
            end_time = datetime.strptime(event.split()[2] + ' ' + event.split()[3], "%Y-%m-%d %H:%M:%S")

    if start_time and end_time:
        return (end_time - start_time).total_seconds()
    else:
        return None

def get_output_transfer_time(events):
    start_time = None
    end_time = None

    for event in events:
        if "Started transferring output files" in event:
            start_time = datetime.strptime(event.split()[2] + ' ' + event.split()[3], "%Y-%m-%d %H:%M:%S")
        elif "Finished transferring output files" in event:
            end_time = datetime.strptime(event.split()[2] + ' ' + event.split()[3], "%Y-%m-%d %H:%M:%S")

    if start_time and end_time:
        return (end_time - start_time).total_seconds()
    else:
        return None

def get_execution_time(events):
    start_time = datetime.strptime(events[0].split()[2] + ' ' + events[0].split()[3], "%Y-%m-%d %H:%M:%S")
    end_time = datetime.strptime(events[-1].split()[2] + ' ' + events[-1].split()[3], "%Y-%m-%d %H:%M:%S")

    return (end_time - start_time).total_seconds()

def get_resource_usage(events):
    resource_data = {}

    for event in events:
        if "Partitionable Resources" in event:
            resource_lines = event.split(':')[1:]
            for line in resource_lines:
                key, values = line.split()
                resource_data[key.strip()] = {
                    'Usage': float(values[0]),
                    'Request': float(values[1]),
                    'Allocated': float(values[2])
                }

    return resource_data

# Example usage:
file_path = 'logfile.txt'
job_data = parse_log_file(file_path)

job_id = '(3659.000.000)'
print(job_data)
events = job_data[job_id]['events']

input_transfer_time = get_input_transfer_time(events)
output_transfer_time = get_output_transfer_time(events)
execution_time = get_execution_time(events)
resource_usage = get_resource_usage(events)

print(f'Input Files Transfer Time: {input_transfer_time} seconds')
print(f'Output Files Transfer Time: {output_transfer_time} seconds')
print(f'Total Execution Time: {execution_time} seconds')
print('Resource Usage:')
for key, values in resource_usage.items():
    print(f'{key}:')
    print(f'  Usage: {values["Usage"]}')
    print(f'  Request: {values["Request"]}')
    print(f'  Allocated: {values["Allocated"]}')
