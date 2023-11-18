import re

# Read the data from the file
with open('a.log', 'r') as file:
    data = file.read()

# Define regular expressions for extracting the information
cpu_pattern = r'Cpus\s+:\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)'
disk_pattern = r'Disk \(KB\)\s+:\s+(\d+)\s+(\d+)\s+(\d+)'
memory_pattern = r'Memory \(MB\)\s+:\s+(\d+)\s+(\d+)\s+(\d+)'

# Extract CPU data
cpu_data = re.search(cpu_pattern, data)
if cpu_data:
    usage_cpu, request_cpu, allocated_cpu = cpu_data.groups()

# Extract Disk data
disk_data = re.search(disk_pattern, data)
if disk_data:
    usage_disk, request_disk, allocated_disk = disk_data.groups()

# Extract Memory data
memory_data = re.search(memory_pattern, data)
if memory_data:
    usage_memory, request_memory, allocated_memory = memory_data.groups()

# Print the extracted data
print(f"CPU Usage: {usage_cpu}, Requested: {request_cpu}, Allocated: {allocated_cpu}")
print(f"Disk Usage (KB): {usage_disk}, Requested: {request_disk}, Allocated: {allocated_disk}")
print(f"Memory Usage (MB): {usage_memory}, Requested: {request_memory}, Allocated: {allocated_memory}")
