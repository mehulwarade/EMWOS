import json
from datetime import datetime
import numpy as np
from typing import Dict, List, Tuple, Optional
import time
from models import EnergyProfile

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                          np.int16, np.int32, np.int64, np.uint8,
                          np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

class JobProfiler:
    def __init__(self, baseline_power: Dict[str, float]):
        """
        Initialize the job profiler
        
        :param baseline_power: Dictionary of resource_id to baseline power consumption in Watts
        """
        self.baseline_power = {k: float(v) for k, v in baseline_power.items()}
        self.profiles = {}
        
    def start_profiling(self, job_id: str, job_type: str, resource_id: str) -> dict:
        """
        Start profiling a job
        
        :param job_id: Unique identifier for the job
        :param job_type: Type/category of the job
        :param resource_id: ID of the resource being used
        :return: Profile dictionary for tracking measurements
        """
        return {
            'job_id': job_id,
            'job_type': job_type,
            'resource_id': resource_id,
            'start_time': datetime.now(),
            'energy_readings': [],
            'cpu_loads': []
        }

    def record_measurement(self, profile: dict, energy_reading: float, cpu_loads: List[float]):
        """Record a single measurement"""
        profile['energy_readings'].append(float(energy_reading))
        profile['cpu_loads'].append([float(x) for x in cpu_loads])

    def end_profiling(self, profile: dict) -> Tuple[float, float]:
        """End profiling and calculate factors"""
        profile['end_time'] = datetime.now()
        duration = (profile['end_time'] - profile['start_time']).total_seconds()
        resource_id = profile['resource_id']
        
        energy_readings = np.array(profile['energy_readings'])
        baseline = self.baseline_power.get(resource_id, 0)
        total_energy = float(np.sum(energy_readings - baseline))
        
        cpu_loads = np.array(profile['cpu_loads'])
        avg_cpu_load = float(np.mean(cpu_loads))
        
        job_type = profile['job_type']
        if job_type not in self.profiles:
            self.profiles[job_type] = {}
        
        if resource_id not in self.profiles[job_type]:
            self.profiles[job_type][resource_id] = []
            time_factor = 1.0
            energy_factor = 1.0
        else:
            # Calculate factors based on first run as baseline
            baseline_profile = self.profiles[job_type][resource_id][0]
            time_factor = duration / baseline_profile['duration']
            energy_factor = total_energy / baseline_profile['total_energy']
        
        self.profiles[job_type][resource_id].append({
            'duration': float(duration),
            'total_energy': float(total_energy),
            'avg_cpu_load': float(avg_cpu_load),
            'timestamp': profile['end_time'].isoformat()
        })
        
        return time_factor, energy_factor

    def get_historical_data(self) -> Dict:
        """Convert profiles to format matching ECT usage"""
        historical_data = {}
        for job_type, resources in self.profiles.items():
            historical_data[job_type] = {}
            for resource_id, profiles in resources.items():
                if profiles:
                    # Use the average time factor relative to first run
                    baseline_duration = profiles[0]['duration']
                    avg_duration = np.mean([p['duration'] for p in profiles])
                    historical_data[job_type][resource_id] = float(avg_duration / baseline_duration)
        return historical_data

    def get_energy_factors(self) -> Dict:
        """Get energy factors for all profiled jobs and resources"""
        energy_factors = {}
        for job_type, resources in self.profiles.items():
            energy_factors[job_type] = {}
            for resource_id, profiles in resources.items():
                if profiles:
                    baseline_energy = profiles[0]['total_energy']
                    avg_energy = np.mean([p['total_energy'] for p in profiles])
                    energy_factors[job_type][resource_id] = float(avg_energy / baseline_energy)
        return energy_factors

    def save_profiles(self, filename: str):
        """Save profiles to a JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.profiles, f, cls=NumpyEncoder, indent=2)

    def load_profiles(self, filename: str):
        """Load profiles from a JSON file"""
        with open(filename, 'r') as f:
            self.profiles = json.load(f)

# Example usage
if __name__ == "__main__":
    # Example resources matching the ECT usage
    resources = [
        {'id': 'alphai7', 'base_power': 65},  # Example base power values
        {'id': 'romeoi5', 'base_power': 55},
        {'id': 'rpi4', 'base_power': 15},
        {'id': 'master', 'base_power': 45}
    ]
    
    # Initialize profiler with baseline power for each resource
    baseline_power = {r['id']: r['base_power'] for r in resources}
    profiler = JobProfiler(baseline_power)
    
    # Example profiling for mProject on different resources
    for resource in resources:
        profile = profiler.start_profiling('mProject_1', 'mProject', resource['id'])
        
        # Simulate job execution and measurements
        for _ in range(5):  # 5 second job
            # Simulate energy reading (base power + load)
            energy_reading = resource['base_power'] * 1.5  # 50% above baseline
            cpu_loads = [60, 70, 65, 55, 0, 0, 0, 0]
            
            profiler.record_measurement(profile, energy_reading, cpu_loads)
            time.sleep(1)
        
        time_factor, energy_factor = profiler.end_profiling(profile)
        print(f"\nResource {resource['id']}:")
        print(f"Time Factor: {time_factor:.2f}")
        print(f"Energy Factor: {energy_factor:.2f}")
    
    # Save profiles
    profiler.save_profiles('historical_profiles.json')
    
    # Get historical data in ECT format
    historical_data = profiler.get_historical_data()
    print("\nHistorical Data (ECT format):")
    print(json.dumps(historical_data, indent=2))
    
    # Get energy factors
    energy_factors = profiler.get_energy_factors()
    print("\nEnergy Factors:")
    print(json.dumps(energy_factors, indent=2))