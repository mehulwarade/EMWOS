from ect_function import ect
from datetime import datetime
import numpy as np
from typing import Dict, List, Tuple, NamedTuple
import time
from dataclasses import dataclass
import math

class EnergyEstimate(NamedTuple):
    """Container for energy consumption estimates"""
    energy_joules: float
    average_watts: float
    transfer_energy: float
    compute_energy: float
    duration: float

@dataclass
class EnergyProfile:
    """Store energy profiling data for a job"""
    job_id: str
    job_type: str
    start_time: datetime
    end_time: datetime
    energy_readings: List[float]  # Watts
    cpu_loads: List[float]  # Percentage per thread
    total_energy: float  # Joules
    average_power: float  # Watts
    baseline_power: float  # Watts

def load_factor(current_state):
    """Calculate load factor based on current CPU load."""
    return 1 + (current_state['cpu_load'] / 100)

def historical_adjustment(job, resource, historical_data):
    """Adjust estimate based on historical data."""
    job_type = job['type']
    if job_type in historical_data and resource['id'] in historical_data[job_type]:
        if isinstance(historical_data[job_type][resource['id']], dict):
            return historical_data[job_type][resource['id']].get('time_factor', 1.0)
        return historical_data[job_type][resource['id']]
    return 1.0

def estimate_transfer_time(data_size, bandwidth, network_load, cpu_load_source, cpu_load_dest):
    """
    Estimate time to transfer data between resources.
    """
    effective_bandwidth = bandwidth * (1 - network_load / 100)
    base_transfer_time = data_size / effective_bandwidth
    cpu_factor = 1 + (cpu_load_source / 200) + (cpu_load_dest / 200)
    return base_transfer_time * cpu_factor

def ect(job, resource, historical_data, current_state, data_source, network_info):
    """
    Calculate Estimated Completion Time (ECT) for a job on a resource.
    """
    base_time = job['cpu_instructions'] / (resource['mips_performance'] * 1000000)
    load_adj = load_factor(current_state)
    hist_adj = historical_adjustment(job, resource, historical_data)
    computation_time = base_time * load_adj * hist_adj
    
    transfer_time = estimate_transfer_time(
        job['data_size'],
        network_info['bandwidth'],
        network_info['load'],
        data_source['cpu_load'],
        current_state['cpu_load']
    )
    
    return transfer_time + computation_time

def energy_load_factor(current_state):
    """Calculate energy load factor based on current CPU load."""
    return 1 + (current_state['cpu_load'] / 50)

def historical_energy_coefficient(job, resource, historical_data):
    """Get historical energy coefficient for job-resource pair."""
    job_type = job['type']
    if job_type in historical_data and resource['id'] in historical_data[job_type]:
        if isinstance(historical_data[job_type][resource['id']], dict):
            return historical_data[job_type][resource['id']].get('energy_factor', 1.0)
        return 1.0
    return 1.0

def estimate_transfer_energy(transfer_time, network_power):
    """
    Estimate energy consumption for data transfer.
    """
    return network_power * transfer_time

def calculate_job_energy(energy_readings, baseline_power, sampling_interval=1.0):
    """
    Calculate total energy consumption of a job considering baseline power.
    """
    total_energy = sum([(reading - baseline_power) * sampling_interval 
                       for reading in energy_readings])
    return max(0, total_energy)

class JobProfiler:
    def __init__(self, baseline_power: float):
        self.baseline_power = baseline_power
        self.profiles = {}

    def start_profiling(self, job_id: str, job_type: str) -> dict:
        """Start profiling a job"""
        return {
            'job_id': job_id,
            'job_type': job_type,
            'start_time': datetime.now(),
            'energy_readings': [],
            'cpu_loads': []
        }

    def record_measurement(self, profile: dict, energy_reading: float, cpu_loads: List[float]):
        """Record a single measurement"""
        profile['energy_readings'].append(energy_reading)
        profile['cpu_loads'].append(cpu_loads)

    def end_profiling(self, profile: dict, resource_id: str) -> Tuple[float, float]:
        """
        End profiling and calculate factors.
        Returns (time_factor, energy_factor)
        """
        profile['end_time'] = datetime.now()
        duration = (profile['end_time'] - profile['start_time']).total_seconds()
        
        energy_readings = np.array(profile['energy_readings'])
        total_energy = np.sum(energy_readings - self.baseline_power)
        
        cpu_loads = np.array(profile['cpu_loads'])
        avg_cpu_load = np.mean(cpu_loads)
        
        job_type = profile['job_type']
        if job_type not in self.profiles:
            self.profiles[job_type] = {}
        
        if resource_id not in self.profiles[job_type]:
            self.profiles[job_type][resource_id] = []
        
        self.profiles[job_type][resource_id].append({
            'duration': duration,
            'total_energy': total_energy,
            'avg_cpu_load': avg_cpu_load,
            'timestamp': profile['end_time']
        })
        
        profiles = self.profiles[job_type][resource_id]
        avg_duration = np.mean([p['duration'] for p in profiles])
        avg_energy = np.mean([p['total_energy'] for p in profiles])
        
        baseline_duration = profiles[0]['duration']
        baseline_energy = profiles[0]['total_energy']
        
        time_factor = avg_duration / baseline_duration
        energy_factor = avg_energy / baseline_energy
        
        return time_factor, energy_factor

    def get_historical_data(self) -> Dict:
        """Convert profiles to historical data format"""
        historical_data = {}
        for job_type, resources in self.profiles.items():
            historical_data[job_type] = {}
            for resource_id, profiles in resources.items():
                if profiles:
                    avg_duration = np.mean([p['duration'] for p in profiles])
                    avg_energy = np.mean([p['total_energy'] for p in profiles])
                    baseline_duration = profiles[0]['duration']
                    baseline_energy = profiles[0]['total_energy']
                    
                    historical_data[job_type][resource_id] = {
                        'time_factor': avg_duration / baseline_duration,
                        'energy_factor': avg_energy / baseline_energy
                    }
        return historical_data

def eec(job, resource, historical_data, current_state, data_source, network_info):
    """
    Calculate Estimated Energy Consumption (EEC) for a job on a resource.
    """
    # Create a copy of historical data with only time factors for ECT
    ect_historical_data = {}
    for job_type, resources in historical_data.items():
        ect_historical_data[job_type] = {}
        for res_id, factors in resources.items():
            if isinstance(factors, dict):
                ect_historical_data[job_type][res_id] = factors.get('time_factor', 1.0)
            else:
                ect_historical_data[job_type][res_id] = factors

    # Get time estimates
    total_time = ect(job, resource, ect_historical_data, current_state, 
                    data_source, network_info)
    
    # Calculate transfer portion
    data_ratio = job['data_size'] / (job['data_size'] + job['cpu_instructions'])
    transfer_time = total_time * data_ratio
    compute_time = total_time * (1 - data_ratio)
    
    # Calculate energy components
    transfer_energy = estimate_transfer_energy(
        transfer_time,
        network_info['network_power']
    )
    
    base_power = resource['base_power']
    load_factor = energy_load_factor(current_state)
    hist_coef = historical_energy_coefficient(job, resource, historical_data)
    compute_energy = base_power * compute_time * hist_coef * load_factor
    
    total_energy = transfer_energy + compute_energy
    average_watts = total_energy / total_time if total_time > 0 else 0
    
    return EnergyEstimate(
        energy_joules=total_energy,
        average_watts=average_watts,
        transfer_energy=transfer_energy,
        compute_energy=compute_energy,
        duration=total_time
    )

# Utility functions for energy unit conversions
def joules_to_kwh(joules):
    """Convert Joules to kilowatt-hours"""
    return joules / 3600000

def kwh_to_joules(kwh):
    """Convert kilowatt-hours to Joules"""
    return kwh * 3600000

def calculate_energy_cost(energy_joules, cost_per_kwh):
    """Calculate energy cost from Joules"""
    return joules_to_kwh(energy_joules) * cost_per_kwh

# Example usage and testing
if __name__ == "__main__":
    # Initialize profiler
    profiler = JobProfiler(baseline_power=100)  # 100W baseline
    
    # Example job for profiling
    profile = profiler.start_profiling('job1', 'matrix_multiplication')
    
    # Simulate job execution and measurements
    for _ in range(5):  # 5 second job
        energy_reading = 150  # Simulated 150W reading
        cpu_loads = [60, 70, 65, 55, 0, 0, 0, 0]  # Simulated CPU loads
        profiler.record_measurement(profile, energy_reading, cpu_loads)
        time.sleep(1)
    
    # End profiling
    time_factor, energy_factor = profiler.end_profiling(profile, 'resource1')
    print(f"Profiling Results:")
    print(f"Time Factor: {time_factor:.2f}")
    print(f"Energy Factor: {energy_factor:.2f}")
    
    # Get historical data
    historical_data = profiler.get_historical_data()
    
    # Example job for energy estimation
    job = {
        'id': 'job1',
        'type': 'matrix_multiplication',
        'cpu_instructions': 1000000000,  # 1 billion instructions
        'data_size': 1000000000  # 1 GB of data
    }

    resource = {
        'id': 'resource1',
        'mips_performance': 1000,  # 1000 MIPS
        'base_power': 100  # Base power consumption in Watts
    }

    current_state = {'cpu_load': 50}
    data_source = {'cpu_load': 30}
    network_info = {
        'bandwidth': 125000000,  # 1 Gbps = 125 MB/s
        'load': 40,
        'network_power': 20
    }

    # Calculate estimated energy consumption
    estimate = eec(
        job, resource, historical_data, current_state, 
        data_source, network_info
    )
    
    # Calculate cost (assuming $0.12 per kWh)
    cost = calculate_energy_cost(estimate.energy_joules, 0.12)
    
    print(f"\nEnergy Estimation Results:")
    print(f"Total Energy: {estimate.energy_joules:.2f} Joules")
    print(f"Average Power: {estimate.average_watts:.2f} Watts")
    print(f"Duration: {estimate.duration:.2f} seconds")
    print(f"Transfer Energy: {estimate.transfer_energy:.2f} Joules")
    print(f"Compute Energy: {estimate.compute_energy:.2f} Joules")
    print(f"Energy in kWh: {joules_to_kwh(estimate.energy_joules):.6f} kWh")
    print(f"Estimated Cost: ${cost:.6f}")