import json
from typing import Dict, List
import sys
import os
from models import EnergyEstimate

# Add parent directory to Python path for importing ect_function
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ect_function import ect

def prepare_historical_data_for_ect(historical_data: Dict) -> Dict:
    """
    Convert historical data to the format expected by ECT function
    
    :param historical_data: Raw historical data from profiler
    :return: Historical data formatted for ECT
    """
    ect_data = {}
    for job_type in historical_data:
        ect_data[job_type] = {}
        for resource_id in historical_data[job_type]:
            if isinstance(historical_data[job_type][resource_id], list):
                # If it's a list of profiles, calculate average
                profiles = historical_data[job_type][resource_id]
                if profiles:
                    baseline_duration = profiles[0]['duration']
                    avg_duration = sum(p['duration'] for p in profiles) / len(profiles)
                    ect_data[job_type][resource_id] = avg_duration / baseline_duration
            elif isinstance(historical_data[job_type][resource_id], dict):
                # If it's already a factor dictionary
                ect_data[job_type][resource_id] = historical_data[job_type][resource_id].get('time_factor', 1.0)
            else:
                # If it's a direct value
                ect_data[job_type][resource_id] = float(historical_data[job_type][resource_id])
    return ect_data

def get_energy_factor(job: Dict, resource: Dict, historical_data: Dict) -> float:
    """Get energy factor from historical data"""
    job_type = job['type']
    resource_id = resource['id']
    
    if job_type in historical_data and resource_id in historical_data[job_type]:
        profiles = historical_data[job_type][resource_id]
        if isinstance(profiles, list) and profiles:
            baseline_energy = profiles[0]['total_energy']
            avg_energy = sum(p['total_energy'] for p in profiles) / len(profiles)
            return avg_energy / baseline_energy
    return 1.0

def estimate_transfer_energy(transfer_time: float, network_power: float) -> float:
    """Estimate energy consumption for data transfer"""
    return network_power * transfer_time

def eec(job: Dict, resource: Dict, historical_data: Dict, current_state: Dict,
        data_source: Dict, network_info: Dict) -> EnergyEstimate:
    """
    Calculate Estimated Energy Consumption (EEC) for a job on a resource
    """
    # Prepare historical data for ECT
    ect_historical_data = prepare_historical_data_for_ect(historical_data)
    
    # Get time estimate from ECT function
    total_time = ect(job, resource, ect_historical_data, current_state, 
                    data_source, network_info)
    
    # Calculate transfer portion
    data_ratio = job['data_size'] / (job['data_size'] + job['cpu_instructions'])
    transfer_time = total_time * data_ratio
    compute_time = total_time * (1 - data_ratio)
    
    # Get base power for the resource
    base_power = resource.get('base_power', 100)  # Default to 100W if not specified
    
    # Calculate energy components
    transfer_energy = estimate_transfer_energy(
        transfer_time,
        network_info.get('network_power', 20)  # Default to 20W if not specified
    )
    
    # Load factor based on CPU utilization
    load_factor = 1 + (current_state['cpu_load'] / 50)
    
    # Get energy factor from historical data
    energy_factor = get_energy_factor(job, resource, historical_data)
    
    compute_energy = base_power * compute_time * energy_factor * load_factor
    
    total_energy = transfer_energy + compute_energy
    average_watts = total_energy / total_time if total_time > 0 else 0
    
    return EnergyEstimate(
        energy_joules=total_energy,
        average_watts=average_watts,
        transfer_energy=transfer_energy,
        compute_energy=compute_energy,
        duration=total_time
    )

# Example usage
if __name__ == "__main__":
    # Example job matching ECT usage
    job = {
        'id': 'mProject',
        'type': 'mProject',
        'cpu_instructions': 2997234631314,  # 2.997 trillion instructions
        'data_size': 100000000  # 100 MB of data
    }

    # Example resources matching ECT usage
    resources = [
        {
            'id': 'alphai7',
            'mips_performance': 13880.35,
            'base_power': 65
        },
        {
            'id': 'romeoi5',
            'mips_performance': 13466.97,
            'base_power': 55
        },
        {
            'id': 'rpi4',
            'mips_performance': 2037,
            'base_power': 15
        },
        {
            'id': 'master',
            'mips_performance': 8559.31,
            'base_power': 45
        }
    ]

    # Load historical data
    try:
        with open('historical_profiles.json', 'r') as f:
            historical_data = json.load(f)
            print("Loaded historical data:")
            print(json.dumps(historical_data, indent=2))
    except FileNotFoundError:
        print("No historical data found. Please run profiler first.")
        exit(1)

    # Prepare and print ECT historical data for verification
    ect_historical_data = prepare_historical_data_for_ect(historical_data)
    print("\nPrepared historical data for ECT:")
    print(json.dumps(ect_historical_data, indent=2))

    current_state = {'cpu_load': 0}
    data_source = {'cpu_load': 0}
    network_info = {
        'bandwidth': 125000000,
        'load': 0,
        'network_power': 20
    }

    # Calculate estimates for each resource
    print("\nEnergy Estimates:")
    for resource in resources:
        estimate = eec(
            job, resource, historical_data, current_state, 
            data_source, network_info
        )
        
        print(f"\nResource: {resource['id']}")
        print(f"Total Energy: {estimate.energy_joules:.2f} Joules")
        print(f"Average Power: {estimate.average_watts:.2f} Watts")
        print(f"Duration: {estimate.duration:.2f} seconds")
        print(f"Transfer Energy: {estimate.transfer_energy:.2f} Joules")
        print(f"Compute Energy: {estimate.compute_energy:.2f} Joules")