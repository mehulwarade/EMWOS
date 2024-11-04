import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import json
import datetime
import warnings
from sklearn.exceptions import DataConversionWarning

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DataConversionWarning)

@dataclass
class HardwareProfile:
    cpu_model: str
    generation: int
    base_clock: float
    max_clock: float
    cores: int
    threads: int
    cache_size: int

@dataclass
class SoftwareConfig:
    threads_allocated: int
    cpu_affinity: List[int]
    memory_limit: int
    disk_quota: int
    network_limit: int
    priority: int

@dataclass
class WorkloadProfile:
    app_name: str
    version: str
    input_size: str
    operation: str
    output_mode: str

class PerformanceMetrics:
    def __init__(self):
        self.metrics = {
            'execution_time': 0.0,
            'cpu_migrations': 0,
            'context_switches': 0,
            'page_faults': 0,
            'cycles': 0,
            'instructions': 0,
            'branches': 0,
            'branch_misses': 0,
            'l1_dcache_loads': 0,
            'l1_dcache_load_misses': 0,
            'llc_loads': 0,
            'llc_load_misses': 0,
            'effective_clock': 0.0,
            'ipc': 0.0,
            'llc_miss_rate': 0.0
        }
    
    def update_from_dict(self, metrics_dict: Dict[str, float]):
        for key, value in metrics_dict.items():
            if key in self.metrics:
                self.metrics[key] = value

class PerformancePredictor:
    def __init__(self):
        self.label_encoders = {}
        self.models = {
            'execution_time': RandomForestRegressor(n_estimators=100, random_state=42),
            'cpu_migrations': RandomForestRegressor(n_estimators=100, random_state=42),
            'context_switches': RandomForestRegressor(n_estimators=100, random_state=42),
            'llc_miss_rate': RandomForestRegressor(n_estimators=100, random_state=42),
            'effective_clock': RandomForestRegressor(n_estimators=100, random_state=42)
        }
        self.history = []
        self.feature_importance = {}
        self.feature_columns = None

    def _encode_categorical(self, data: Dict) -> pd.Series:
        encoded = {}
        for key, value in data.items():
            if isinstance(value, str):
                if key not in self.label_encoders:
                    self.label_encoders[key] = LabelEncoder()
                all_values = set([value])
                for h in self.history:
                    if key in h['features']:
                        all_values.add(h['features'][key])
                self.label_encoders[key].fit(list(all_values))
                encoded[key] = self.label_encoders[key].transform([value])[0]
            else:
                encoded[key] = value
        return encoded

    def _prepare_features(self, 
                         hardware: HardwareProfile,
                         software: SoftwareConfig,
                         workload: WorkloadProfile,
                         background_processes: int) -> pd.DataFrame:
        features = {
            'cpu_model': hardware.cpu_model,
            'generation': hardware.generation,
            'base_clock': hardware.base_clock,
            'max_clock': hardware.max_clock,
            'cores': hardware.cores,
            'threads': hardware.threads,
            'cache_size': hardware.cache_size,
            'threads_allocated': software.threads_allocated,
            'cpu_affinity_count': len(software.cpu_affinity),
            'memory_limit': software.memory_limit,
            'disk_quota': software.disk_quota,
            'network_limit': software.network_limit,
            'priority': software.priority,
            'app_name': workload.app_name,
            'version': workload.version,
            'input_size': workload.input_size,
            'operation': workload.operation,
            'output_mode': workload.output_mode,
            'background_processes': background_processes
        }
        
        encoded = self._encode_categorical(features)
        df = pd.DataFrame([encoded])
        
        if self.feature_columns is None:
            self.feature_columns = df.columns
        else:
            df = df.reindex(columns=self.feature_columns, fill_value=0)
        
        return df

    def train(self, 
              hardware: HardwareProfile,
              software: SoftwareConfig,
              workload: WorkloadProfile,
              background_processes: int,
              performance: PerformanceMetrics):
        
        features_df = self._prepare_features(hardware, software, workload, background_processes)
        
        self.history.append({
            'timestamp': datetime.datetime.now().isoformat(),
            'features': features_df.iloc[0].to_dict(),
            'metrics': performance.metrics
        })
        
        X = pd.DataFrame([h['features'] for h in self.history])
        if self.feature_columns is None:
            self.feature_columns = X.columns
        
        X = X.reindex(columns=self.feature_columns, fill_value=0)
        
        for metric_name, model in self.models.items():
            y = [h['metrics'][metric_name] for h in self.history]
            model.fit(X, y)
            
            self.feature_importance[metric_name] = dict(zip(
                self.feature_columns,
                model.feature_importances_
            ))

    def predict(self,
                hardware: HardwareProfile,
                software: SoftwareConfig,
                workload: WorkloadProfile,
                background_processes: int) -> Dict[str, float]:
        
        if not self.history:
            raise ValueError("No training data available for prediction")
            
        features_df = self._prepare_features(hardware, software, workload, background_processes)
        
        predictions = {}
        prediction_bounds = {}
        
        for metric_name, model in self.models.items():
            pred = model.predict(features_df)[0]
            predictions[metric_name] = pred
            
            tree_predictions = np.array([tree.predict(features_df) for tree in model.estimators_])
            std_dev = np.std(tree_predictions, axis=0)[0]
            prediction_bounds[metric_name] = {
                'lower': pred - 2 * std_dev,
                'upper': pred + 2 * std_dev
            }
            
        return {
            'predictions': predictions,
            'bounds': prediction_bounds,
            'confidence_factors': self._calculate_confidence(features_df.iloc[0].to_dict())
        }

    def _calculate_confidence(self, features: Dict) -> Dict[str, float]:
        confidence_scores = {}
        
        for metric_name, importance in self.feature_importance.items():
            similar_cases = 0
            for hist in self.history:
                similarity = sum(
                    imp * (hist['features'][feat] == features[feat])
                    for feat, imp in importance.items()
                )
                if similarity > 0.8:
                    similar_cases += 1
                    
            confidence_scores[metric_name] = min(1.0, similar_cases / 10)
        
        return confidence_scores

    def analyze_trends(self) -> Dict:
        trends = {}
        df = pd.DataFrame([h['metrics'] for h in self.history])
        
        for metric in df.columns:
            trends[metric] = {
                'mean': df[metric].mean(),
                'std': df[metric].std(),
                'trend': 'increasing' if df[metric].is_monotonic_increasing 
                        else 'decreasing' if df[metric].is_monotonic_decreasing 
                        else 'fluctuating'
            }
            
        return trends

def create_example_data():
    hardware = HardwareProfile(
        cpu_model="test-cpu",
        generation=12,
        base_clock=3.6,
        max_clock=5.0,
        cores=12,
        threads=20,
        cache_size=25
    )

    software = SoftwareConfig(
        threads_allocated=8,
        cpu_affinity=list(range(8)),
        memory_limit=16384,
        disk_quota=1024000,
        network_limit=1000,
        priority=0
    )

    workload = WorkloadProfile(
        app_name="montage",
        version="1.5",
        input_size="blue_001_002",
        operation="mProject",
        output_mode="stdout"
    )

    historical_runs = [
        # Run 1 (Clean run)
        {
            'background_processes': 0,
            'metrics': {
                'execution_time': 351.03,
                'cpu_migrations': 160,
                'context_switches': 2495,
                'cycles': 978149994336,
                'instructions': 2997234631314,
                'effective_clock': 2.793,
                'llc_miss_rate': 48.62,
                'ipc': 3.06
            }
        },
        # Run 2 (Clean run, different conditions)
        {
            'background_processes': 0,
            'metrics': {
                'execution_time': 223.47,
                'cpu_migrations': 47,
                'context_switches': 4170,
                'cycles': 962804580263,
                'instructions': 2997045681937,
                'effective_clock': 4.326,
                'llc_miss_rate': 49.10,
                'ipc': 3.11
            }
        },
        # Run 3 (Clean run, best performance)
        {
            'background_processes': 0,
            'metrics': {
                'execution_time': 216.87,
                'cpu_migrations': 26,
                'context_switches': 5408,
                'cycles': 964823026671,
                'instructions': 2997043178714,
                'effective_clock': 4.469,
                'llc_miss_rate': 44.63,
                'ipc': 3.11
            }
        },
        # Run 4 (With interference)
        {
            'background_processes': 1,
            'metrics': {
                'execution_time': 229.18,
                'cpu_migrations': 166,
                'context_switches': 3461,
                'cycles': 978382507576,
                'instructions': 2997012383524,
                'effective_clock': 4.288,
                'llc_miss_rate': 52.00,
                'ipc': 3.06
            }
        },
        # Run 5 (With 2 background processes)
        {
            'background_processes': 2,
            'metrics': {
                'execution_time': 240.13,
                'cpu_migrations': 183,
                'context_switches': 5619,
                'cycles': 962803590647,
                'instructions': 2997075560206,
                'effective_clock': 4.025,
                'llc_miss_rate': 52.82,
                'ipc': 3.11
            }
        }
    ]

    return hardware, software, workload, historical_runs

def main():
    print("Initializing Performance Predictor...")
    predictor = PerformancePredictor()
    
    print("\nLoading example data...")
    hardware, software, workload, historical_runs = create_example_data()
    
    print("\nTraining model with historical data...")
    for run in historical_runs:
        metrics = PerformanceMetrics()
        metrics.update_from_dict(run['metrics'])
        predictor.train(
            hardware,
            software,
            workload,
            run['background_processes'],
            metrics
        )
    
    print("\nMaking predictions for different scenarios...")
    test_scenarios = [
        {'background_processes': 0, 'description': 'Clean run'},
        {'background_processes': 1, 'description': 'With 1 background process'},
        {'background_processes': 2, 'description': 'With 2 background processes'},
        {'background_processes': 3, 'description': 'With 3 background processes (extrapolation)'}
    ]
    
    for scenario in test_scenarios:
        print(f"\n{'-'*60}")
        print(f"\nScenario: {scenario['description']}")
        print(f"Background Processes: {scenario['background_processes']}")
        
        prediction = predictor.predict(
            hardware,
            software,
            workload,
            scenario['background_processes']
        )
        
        print("\nPredicted Metrics:")
        print(f"  Execution Time: {prediction['predictions']['execution_time']:.2f}s")
        print(f"    Confidence Bounds: {prediction['bounds']['execution_time']['lower']:.2f}s - "
              f"{prediction['bounds']['execution_time']['upper']:.2f}s")
        print(f"  Effective Clock: {prediction['predictions']['effective_clock']:.3f} GHz")
        print(f"  CPU Migrations: {prediction['predictions']['cpu_migrations']:.0f}")
        print(f"  LLC Miss Rate: {prediction['predictions']['llc_miss_rate']:.2f}%")
        
        print("\nConfidence Scores:")
        for metric, confidence in prediction['confidence_factors'].items():
            print(f"  {metric}: {confidence:.2f}")

    print(f"\n{'-'*60}")
    print("\nAnalyzing performance trends...")
    trends = predictor.analyze_trends()
    
    print("\nPerformance Trends:")
    for metric, trend_data in trends.items():
        if metric in ['execution_time', 'effective_clock', 'llc_miss_rate', 'cpu_migrations']:
            print(f"\n{metric}:")
            print(f"  Mean: {trend_data['mean']:.2f}")
            print(f"  Std Dev: {trend_data['std']:.2f}")
            print(f"  Trend: {trend_data['trend']}")

if __name__ == "__main__":
    main()
