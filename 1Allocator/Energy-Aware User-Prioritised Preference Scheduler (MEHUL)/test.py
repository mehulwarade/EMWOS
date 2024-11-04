import dataclasses
from typing import List, Dict, Tuple
from enum import Enum
import heapq

class PreferenceType(Enum):
    PERFORMANCE = "performance"
    ENERGY = "energy"

@dataclasses.dataclass
class Task:
    id: str
    runtime: float
    dependencies: List[str]
    processor_requirements: Dict[str, float]  # processor_id -> execution_time

@dataclasses.dataclass
class Workflow:
    id: str
    tasks: List[Task]
    preference_type: PreferenceType
    preference_weight: float  # 0-10 scale

@dataclasses.dataclass
class Processor:
    id: str
    power_consumption: float  # watts
    available_time: float = 0

class MEHULScheduler:
    def __init__(self, processors: List[Processor]):
        self.processors = {p.id: p for p in processors}
        
    def calculate_est(self, task: Task, processor: Processor, 
                     task_assignments: Dict[str, Tuple[str, float]]) -> float:
        """Calculate Earliest Start Time for a task on a processor."""
        # Maximum finish time of all dependencies
        max_finish_time = 0
        for dep_id in task.dependencies:
            if dep_id in task_assignments:
                dep_proc_id, dep_finish_time = task_assignments[dep_id]
                # Add communication cost if dependent task is on different processor
                comm_cost = 0 if dep_proc_id == processor.id else 1  # Simplified
                max_finish_time = max(max_finish_time, dep_finish_time + comm_cost)
        
        return max(max_finish_time, processor.available_time)

    def schedule_workflow(self, workflow: Workflow) -> Dict[str, Tuple[str, float, float]]:
        """Schedule a single workflow. Returns {task_id: (processor_id, start_time, finish_time)}"""
        ready_tasks = []
        scheduled_tasks = {}
        task_dependencies = {task.id: set(task.dependencies) for task in workflow.tasks}
        
        # Initialize with tasks that have no dependencies
        for task in workflow.tasks:
            if not task.dependencies:
                priority = self._calculate_priority(task, workflow)
                heapq.heappush(ready_tasks, (-priority, task))

        while ready_tasks:
            _, task = heapq.heappop(ready_tasks)
            
            # Find best processor assignment
            best_assignment = self._find_best_processor(task, workflow, scheduled_tasks)
            if not best_assignment:
                continue
                
            processor_id, start_time = best_assignment
            finish_time = start_time + task.processor_requirements[processor_id]
            
            # Update processor availability
            self.processors[processor_id].available_time = finish_time
            scheduled_tasks[task.id] = (processor_id, start_time, finish_time)
            
            # Add newly ready tasks to queue
            for t in workflow.tasks:
                if t.id not in scheduled_tasks:
                    deps = task_dependencies[t.id]
                    deps.discard(task.id)
                    if not deps:
                        priority = self._calculate_priority(t, workflow)
                        heapq.heappush(ready_tasks, (-priority, t))
        
        return scheduled_tasks

    def _calculate_priority(self, task: Task, workflow: Workflow) -> float:
        """Calculate task priority based on workflow preference."""
        base_priority = sum(task.processor_requirements.values()) / len(task.processor_requirements)
        
        if workflow.preference_type == PreferenceType.PERFORMANCE:
            return base_priority * (1 + workflow.preference_weight / 10)
        else:  # ENERGY preference
            return base_priority * (1 - workflow.preference_weight / 20)

    def _find_best_processor(self, task: Task, workflow: Workflow, 
                           scheduled_tasks: Dict[str, Tuple[str, float, float]]) -> Tuple[str, float]:
        """Find the best processor assignment based on workflow preference."""
        best_processor = None
        best_start_time = float('inf')
        best_energy = float('inf')
        
        for proc_id, processor in self.processors.items():
            if proc_id not in task.processor_requirements:
                continue
                
            est = self.calculate_est(task, processor, 
                                   {t: (p, f) for t, (p, _, f) in scheduled_tasks.items()})
            energy = processor.power_consumption * task.processor_requirements[proc_id]
            
            if workflow.preference_type == PreferenceType.PERFORMANCE:
                if est < best_start_time:
                    best_start_time = est
                    best_processor = proc_id
            else:  # ENERGY preference
                if energy < best_energy:
                    best_energy = energy
                    best_processor = proc_id
                    best_start_time = est
        
        return (best_processor, best_start_time) if best_processor else None

    def calculate_total_energy(self, schedule: Dict[str, Tuple[str, float, float]]) -> float:
        """Calculate total energy consumption for a schedule."""
        total_energy = 0
        for task_id, (proc_id, start_time, finish_time) in schedule.items():
            duration = finish_time - start_time
            power = self.processors[proc_id].power_consumption
            total_energy += duration * power
        return total_energy

def create_sample_workflow() -> Workflow:
    """Create a sample workflow for testing."""
    tasks = [
        Task("T1", 10, [], {"P1": 10, "P2": 15}),
        Task("T2", 8, ["T1"], {"P1": 8, "P2": 12}),
        Task("T3", 12, ["T1"], {"P1": 12, "P2": 9}),
        Task("T4", 15, ["T2", "T3"], {"P1": 15, "P2": 18})
    ]
    return Workflow("W1", tasks, PreferenceType.PERFORMANCE, 8)

def main():
    # Create sample processors
    processors = [
        Processor("P1", power_consumption=100),
        Processor("P2", power_consumption=150)
    ]
    
    # Create scheduler
    scheduler = MEHULScheduler(processors)
    
    # Create and schedule a sample workflow
    workflow = create_sample_workflow()
    schedule = scheduler.schedule_workflow(workflow)
    
    # Print results
    print(f"\nSchedule for workflow {workflow.id}:")
    for task_id, (proc_id, start, finish) in schedule.items():
        print(f"Task {task_id}: Processor {proc_id}, Start: {start}, Finish: {finish}")
    
    total_energy = scheduler.calculate_total_energy(schedule)
    print(f"\nTotal energy consumption: {total_energy} Joules")

if __name__ == "__main__":
    main()