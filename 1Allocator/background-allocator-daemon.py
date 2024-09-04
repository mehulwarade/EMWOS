#!/usr/bin/env python3

import http.server
import socketserver
import json
import threading
import os
import signal
import sys
import time
import logging
from multiprocessing import Process, Manager, Lock

RESOURCES_FILE = "resources.txt"
PID_FILE = "emwos_resource_allocator.pid"
PORT = 8000
SAVE_INTERVAL = 5  # Interval in seconds for saving resources

# Set up logging to console
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class ResourceManager:
    def __init__(self, shared_resources, lock):
        self.resources = shared_resources
        self.lock = lock
        self.load_resources()
        logging.info("ResourceManager initialized")

    def load_resources(self):
        with self.lock:
            self.resources.clear()
            with open(RESOURCES_FILE, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    resource = parts[0]
                    processor = parts[1]
                    job = parts[2] if len(parts) > 2 else None
                    self.resources[resource] = {"processor": processor, "job": job}
        logging.info(f"Resources loaded: {len(self.resources)} resources")

    def allocate_resource(self, job):
        with self.lock:
            for resource in self.resources.keys():
                if self.resources[resource]["job"] is None:
                    updated_resource = dict(self.resources[resource])
                    updated_resource["job"] = job
                    self.resources[resource] = updated_resource
                    logging.info(f"Resource {resource} allocated to job {job}")
                    return resource
        logging.warning("No available resources for allocation")
        return None

    def release_resource(self, job):
        with self.lock:
            for resource, info in self.resources.items():
                if info["job"] == job:
                    updated_resource = dict(info)
                    updated_resource["job"] = None
                    self.resources[resource] = updated_resource
                    logging.info(f"Resource {resource} released from job {job}")
                    return True
        logging.warning(f"No resource found allocated to job {job}")
        return False

    def get_resource_status(self):
        with self.lock:
            total = len(self.resources)
            used = sum(1 for info in self.resources.values() if info["job"] is not None)
            available = total - used
            return total, used, available

def save_resources(shared_resources, lock):
    while True:
        time.sleep(SAVE_INTERVAL)
        try:
            with lock:
                with open(RESOURCES_FILE, 'w') as f:
                    for resource, info in shared_resources.items():
                        line = f"{resource},{info['processor']}"
                        if info["job"]:
                            line += f",{info['job']}"
                        f.write(line + "\n")
            total, used, available = ResourceManager(shared_resources, lock).get_resource_status()
            logging.info(f"Resources saved to {RESOURCES_FILE}. Total: {total}, Used: {used}, Available: {available}")
        except Exception as e:
            logging.error(f"Error in periodic save: {str(e)}")

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, resource_manager, *args, **kwargs):
        self.resource_manager = resource_manager
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        logging.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        logging.info(f"Received POST request: {self.path}")
        logging.info(f"Request data: {data}")

        if self.path == '/allocate':
            job = data.get('job')
            if not job:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"error": "Job not specified"})
                self.wfile.write(response.encode('utf-8'))
                logging.error("Allocation request received without job specified")
                return
            
            resource = self.resource_manager.allocate_resource(job)
            if resource:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"resource": resource})
                self.wfile.write(response.encode('utf-8'))
            else:
                self.send_response(503)  # 503 Service Unavailable
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"error": "No resources available"})
                self.wfile.write(response.encode('utf-8'))
                logging.info("No resources available. Sent 503 response.")

        elif self.path == '/release':
            job = data.get('job')
            if job:
                success = self.resource_manager.release_resource(job)
                if success:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = json.dumps({"status": "released"})
                    self.wfile.write(response.encode('utf-8'))
                else:
                    self.send_response(400)  # Changed from 404 to 400
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = json.dumps({"error": "No resource found for the specified job"})
                    self.wfile.write(response.encode('utf-8'))
                    logging.warning(f"Attempt to release non-existent job: {job}")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"error": "Job not specified"})
                self.wfile.write(response.encode('utf-8'))
                logging.error("Release request received without job specified")
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = json.dumps({"error": "Endpoint not found"})
            self.wfile.write(response.encode('utf-8'))
            logging.warning(f"Request to unknown endpoint: {self.path}")

        total, used, available = self.resource_manager.get_resource_status()
        logging.info(f"Current resource status - Total: {total}, Used: {used}, Available: {available}")

def run_server(resource_manager):
    handler = lambda *args: RequestHandler(resource_manager, *args)
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        logging.info(f"Server started on port {PORT}")
        httpd.serve_forever()

def signal_handler(signum, frame):
    logging.info(f"Received signal {signum}. Cleaning up...")
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    logging.info("Server stopped")
    sys.exit(0)

def sanity_check():
    with open(RESOURCES_FILE, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) > 2 and parts[2]:  # If there's a job allocated
                logging.error("Sanity check failed: Jobs are already allocated in resources.txt")
                print("ERROR: Jobs are already allocated in resources.txt. Please check and clear any allocated jobs before starting the server.")
                sys.exit(1)
    logging.info("Sanity check passed: No jobs allocated in resources.txt")

if __name__ == "__main__":
    logging.info("Starting EMWOS Resource Allocation Server")

    # Perform sanity check
    sanity_check()

    # Write PID to file
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    logging.info(f"PID {os.getpid()} written to {PID_FILE}")

    # Set up signal handling
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)
    logging.info("Signal handlers set up")

    # Set up shared resources
    manager = Manager()
    shared_resources = manager.dict()
    lock = manager.Lock()

    resource_manager = ResourceManager(shared_resources, lock)
    
    # Start periodic save process
    save_process = Process(target=save_resources, args=(shared_resources, lock))
    save_process.start()
    logging.info("Periodic save process started")

    logging.info(f"Save interval set to {SAVE_INTERVAL} seconds")

    try:
        run_server(resource_manager)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Cleaning up...")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        save_process.terminate()
        logging.info("Server stopped")