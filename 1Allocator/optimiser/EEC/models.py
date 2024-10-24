from datetime import datetime
from typing import Dict, List, NamedTuple
from dataclasses import dataclass

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

def joules_to_kwh(joules: float) -> float:
    """Convert Joules to kilowatt-hours"""
    return joules / 3600000

def kwh_to_joules(kwh: float) -> float:
    """Convert kilowatt-hours to Joules"""
    return kwh * 3600000

def calculate_energy_cost(energy_joules: float, cost_per_kwh: float) -> float:
    """Calculate energy cost from Joules"""
    return joules_to_kwh(energy_joules) * cost_per_kwh