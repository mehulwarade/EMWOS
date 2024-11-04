from ect_function import ect

job = {
    'id': 'mProject',
    'type': 'mProject',
    'cpu_instructions': 2997234631314,  # 2.997 trillion instructions
    'data_size': 100000000  # 100 MB of data
}

resource = [{
    'id': 'alphai7',
    'mips_performance': 13880.35  # MIPS
},
{
    'id': 'romeoi5',
    'mips_performance': 13466.97  # MIPS
},
{
    'id': 'rpi4',
    'mips_performance': 2037 # MIPS
},
{
    'id': 'master',
    'mips_performance': 8559.31 # MIPS
}]

historical_data = {
    'mProject': {
        # 'resource1': 1.2  # This job type historically takes 20% longer on this resource
        'alphai7': 1
    }
}

current_state = {
    # 'cpu_load': 50  # 50% CPU load
    'cpu_load': 0  # 0% CPU load originally
}

data_source = {
    'cpu_load': 0  # 0% CPU load on the data source
}

network_info = {
    'bandwidth': 125000000,  # 1 Gbps = 125 MB/s
    # 'load': 40  # 40% network load
    'load': 0  # 0% network load
}

for x in range(len(resource)):
    estimated_time = ect(job, resource[x], historical_data, current_state, data_source, network_info)
    print(f"Estimated Completion Time on {resource[x]['id']} : {estimated_time:.2f} seconds")