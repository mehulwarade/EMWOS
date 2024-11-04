import math

def load_factor(current_state):
    """Calculate load factor based on current CPU load."""
    return 1 + (current_state['cpu_load'] / 100)

def historical_adjustment(job, resource, historical_data):
    """Adjust estimate based on historical data."""
    job_type = job['type']
    if job_type in historical_data and resource['id'] in historical_data[job_type]:
        return historical_data[job_type][resource['id']]
    return 1.0

def estimate_transfer_time(data_size, bandwidth, network_load, cpu_load_source, cpu_load_dest):
    """
    Estimate time to transfer data between resources.
    
    :param data_size: Size of data to transfer in bytes
    :param bandwidth: Network bandwidth in bytes per second
    :param network_load: Current network load as a percentage
    :param cpu_load_source: CPU load of the source resource as a percentage
    :param cpu_load_dest: CPU load of the destination resource as a percentage
    :return: Estimated transfer time in seconds
    """
    # Adjust bandwidth based on network load
    effective_bandwidth = bandwidth * (1 - network_load / 100)
    
    # Calculate base transfer time
    base_transfer_time = data_size / effective_bandwidth
    
    # Adjust for CPU load at both ends
    cpu_factor = 1 + (cpu_load_source / 200) + (cpu_load_dest / 200)
    
    return base_transfer_time * cpu_factor

def ect(job, resource, historical_data, current_state, data_source, network_info):
    """
    Calculate Estimated Completion Time (ECT) for a job on a resource, including data transfer time.
    
    :param job: Dict containing job information
    :param resource: Dict containing resource information
    :param historical_data: Dict containing historical performance data
    :param current_state: Dict containing current state of the resource
    :param data_source: Dict containing information about the data source
    :param network_info: Dict containing network information
    :return: Estimated completion time in seconds
    """
    # Estimate computation time in s
    # Base Execution time in seconds = (Number of instructions) / (MIPS * 1,000,000)
    base_time = job['cpu_instructions'] / (resource['mips_performance'] * 1000000)
    load_adj = load_factor(current_state)
    hist_adj = historical_adjustment(job, resource, historical_data)
    computation_time = base_time * load_adj * hist_adj
    
    # Estimate data transfer time in s
    transfer_time = estimate_transfer_time(
        job['data_size'],
        network_info['bandwidth'],
        network_info['load'],
        data_source['cpu_load'],
        current_state['cpu_load']
    )
    
    # Total estimated time is sum of transfer time and computation time
    return transfer_time + computation_time

# Example usage
if __name__ == "__main__":
    job = {
        'id': 'job1',
        'type': 'matrix_multiplication',
        'cpu_instructions': 1000000000,  # 1 billion instructions
        'data_size': 1000000000  # 1 GB of data
    }

    resource = {
        'id': 'resource1',
        'mips_performance': 1000  # 1000 MIPS
    }

    historical_data = {
        'matrix_multiplication': {
            'resource1': 1.2  # This job type historically takes 20% longer on this resource
        }
    }

    current_state = {
        'cpu_load': 50  # 50% CPU load
    }

    data_source = {
        'cpu_load': 30  # 30% CPU load on the data source
    }

    network_info = {
        'bandwidth': 125000000,  # 1 Gbps = 125 MB/s
        'load': 40  # 40% network load
    }

    estimated_time = ect(job, resource, historical_data, current_state, data_source, network_info)
    print(f"Estimated Completion Time: {estimated_time:.2f} seconds")