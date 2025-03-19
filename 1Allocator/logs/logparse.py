import re
import json
import csv
from datetime import datetime
import pytz

def parse_log_file(input_file_path, output_file_path):
    timestamp_pattern = r'\[(.*?)\]'
    state_pattern = r'Overall State: ({.*?})'
    
    metrics_data = []
    current_timestamp = None
    
    with open(input_file_path, 'r') as file:
        lines = file.readlines()
        for i in range(len(lines)):
            print(f"Parsing line: '{i}'")
            current_line = lines[i]
            
            # Store timestamp when we find it
            timestamp_match = re.search(timestamp_pattern, current_line)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                try:
                    # Updated datetime format to match your log format
                    dt = datetime.strptime(timestamp_str, '%m/%d/%Y, %H:%M:%S %p')
                    if not dt.tzinfo:
                        dt = pytz.timezone('UTC').localize(dt)
                    current_timestamp = int(dt.timestamp())
                except ValueError as e:
                    # print(f"Error parsing timestamp '{timestamp_str}': {e}")
                    continue
            
            # Look for metrics on the next line if we have a timestamp
            if current_timestamp and i + 1 < len(lines):
                next_line = lines[i + 1]
                if 'Overall State:' in next_line:
                    state_match = re.search(state_pattern, next_line)
                    if state_match:
                        try:
                            metrics = json.loads(state_match.group(1))
                            metrics_data.append({
                                'timestamp': current_timestamp,
                                'totalResources': metrics['totalResources'],
                                'freeResources': metrics['freeResources'],
                                'busyResources': metrics['busyResources'],
                                'jobsInQueue': metrics['jobsInQueue'],
                                'pendingJobs': metrics['pendingJobs']
                            })
                        except json.JSONDecodeError:
                            print(f"Error parsing JSON at timestamp {timestamp_str}")
                        except KeyError as e:
                            print(f"Missing key in metrics at timestamp {timestamp_str}: {e}")
                    current_timestamp = None  # Reset timestamp after using it
    
    # Write to CSV
    if metrics_data:
        fieldnames = ['timestamp', 'totalResources', 'freeResources', 
                     'busyResources', 'jobsInQueue', 'pendingJobs']
        
        with open(output_file_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(metrics_data)
        
        print(f"Successfully wrote {len(metrics_data)} records to {output_file_path}")
        print(f"First timestamp parsed: {metrics_data[0]['timestamp']}")
        print(f"Last timestamp parsed: {metrics_data[-1]['timestamp']}")
    else:
        print("No metrics data found in the log file")

# Example usage
if __name__ == "__main__":
    input_file = "mwf3-server_2024-11-10T14-33-21-818Z.log"  # Replace with your log file path
    output_file = "cluster_metrics.csv"  # Output CSV file name
    parse_log_file(input_file, output_file)