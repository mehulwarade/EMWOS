import re

def find_pattern_in_log(file_path, pattern):
    with open(file_path, 'r') as file:
        log_data = file.read()

    matches = re.findall(pattern, log_data)
    return matches

# Example usage:
file_path = 'a.log'
pattern_input_transfer = r'Started transferring input files.*?Finished transferring input files'
pattern_output_transfer = r'Started transferring output files.*?Finished transferring output files'
pattern_execution_time = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?Job terminated'

input_transfer_matches = find_pattern_in_log(file_path, pattern_input_transfer)
output_transfer_matches = find_pattern_in_log(file_path, pattern_output_transfer)
execution_time_matches = find_pattern_in_log(file_path, pattern_execution_time)

# Process the matches as needed
for match in input_transfer_matches:
    print(f'Input Transfer Match: {match}')

for match in output_transfer_matches:
    print(f'Output Transfer Match: {match}')

for match in execution_time_matches:
    print(f'Execution Time Match: {match}')





resource_usage_data = find_pattern_in_log(file_path, r'Partitionable Resources(.*?) Job terminated')


print(resource_usage_data)

if resource_usage_data and len(resource_usage_data) >= 1:
    resource_data = resource_usage_data[0][0].strip()
    cpu_used, disk_used, disk_requested, disk_allocated, memory_used, memory_requested, memory_allocated = re.findall(r'Cpus\s+:\s+(\d+\.\d+).*?Disk \(KB\)\s+:\s+(\d+)\s+(\d+)\s+(\d+).*?Memory \(MB\)\s+:\s+(\d+)\s+(\d+)\s+(\d+)', resource_data)[0]
    
    print(f'CPU Used: {cpu_used}')
    print(f'Disk Used: {disk_used} KB')
    print(f'Disk Requested: {disk_requested} KB')
    print(f'Disk Allocated: {disk_allocated} KB')
    print(f'Memory Used: {memory_used} MB')
    print(f'Memory Requested: {memory_requested} MB')
    print(f'Memory Allocated: {memory_allocated} MB')