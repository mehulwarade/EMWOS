const http = require('http');
const fs = require('fs');
const url = require('url');

const PORT = 8000;
const RESOURCES_FILE = 'resources.txt';
const LOG_FILE = 'server.log';

let resources = [];
let allocatedResources = new Map();
let jobQueue = [];
let pendingRequests = new Map();

// Logging function
function log(message) {
    const now = new Date();
    const humanReadableTime = now.toLocaleString();
    const unixTimestamp = Math.floor(now.getTime() / 1000);
    const logMessage = `[${humanReadableTime}] [${unixTimestamp}] ${message}\n`;
    console.log(logMessage.trim());
    fs.appendFileSync(LOG_FILE, logMessage);
}

// Function to get current server state with improved formatting and overall state
function getServerState() {
    const availableResources = resources.filter(r => !allocatedResources.has(r));
    const allocatedResourcesObj = Object.fromEntries(allocatedResources);
    const pendingRequestsArray = Array.from(pendingRequests.keys());

    const overallState = {
        totalResources: resources.length,
        freeResources: availableResources.length,
        busyResources: allocatedResources.size,
        jobsInQueue: jobQueue.length,
        pendingJobs: pendingRequests.size
    };

    return `
        Overall State:
        ${JSON.stringify(overallState)}
        Available Resources:
        ${JSON.stringify(availableResources)}
        Allocated Resources:
        ${JSON.stringify(allocatedResourcesObj)}
        Job Queue:
        ${JSON.stringify(jobQueue)}
        Pending Requests:
        ${JSON.stringify(pendingRequestsArray)}`;
}

// Read resources from file
function initializeResources() {
    try {
        const data = fs.readFileSync(RESOURCES_FILE, 'utf8');
        resources = data.split('\n').filter(line => line.trim() !== '');
        log(`Resources loaded: ${resources.join(', ')}`);
    } catch (err) {
        log(`Error reading resources file: ${err}`);
        process.exit(1);
    }
}

// Function to find the next job to schedule
function NextJobToSchedule() {
    if (jobQueue.length === 0) return null;
    return jobQueue.shift();
}

// Function to find an available resource based on job preference
function NextResourceAvailable(jobPreference) {
    return resources.find(resource => !allocatedResources.has(resource));
    if (jobPreference === 'performance') {
        // Allocate resources with 'alpha' for performance
        return resources.find(resource => !allocatedResources.has(resource) && resource.includes('alpha'));
    } else if (jobPreference === 'energy') {
        // Allocate resources with 'charlie' for energy efficiency
        return resources.find(resource => !allocatedResources.has(resource) && resource.includes('charlie'));
    } else {
        // For 'balanced' or no preference, use any available resource
        return resources.find(resource => !allocatedResources.has(resource));
    }
}

// Todo: Function - Next schedule. return the next job and resource pair for scheduling. can implement optimisation here. initially return the next job and the next available resource.
function nextSchedule(){
    
}

// Function to process the job queue
function processQueue() {
    let processedJobs = new Set();
    let allocatedThisRound = false;

    while (jobQueue.length > 0) {
        const initialQueueLength = jobQueue.length;
        allocatedThisRound = false;

        for (let i = 0; i < initialQueueLength; i++) {
            // TODO: in future instead of next job, we can find the job and resource simultaneously.
            const nextJob = NextJobToSchedule();
            if (!nextJob) break;

            const availableResource = NextResourceAvailable(nextJob.preference);

            if (availableResource) {
                allocatedResources.set(availableResource, nextJob.name);
                const res = pendingRequests.get(nextJob.name);
                if (res) {
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ resource: availableResource, job: nextJob.name, preference: nextJob.preference || 'none' }));
                    pendingRequests.delete(nextJob.name);
                    log(`Resource ${availableResource} allocated to job ${nextJob.name}${nextJob.preference ? ` with preference ${nextJob.preference}` : ''}`);
                }
                processedJobs.add(nextJob.name);
                allocatedThisRound = true;
            } else {
                // If no suitable resource, put the job back at the end of the queue
                jobQueue.push(nextJob);
                log(`No suitable resources available for job ${nextJob.name}${nextJob.preference ? ` with preference ${nextJob.preference}` : ''}. Moved to end of queue.`);
            }
        }

        // If we've gone through the entire queue without making any allocations, break the loop
        if (!allocatedThisRound) {
            log("No more allocations possible. Ending queue processing.");
            break;
        }
    }

    log(`Current server state: ${getServerState()}`);
}

// Function to release a resource
function releaseResource(jobName) {
    for (let [resource, job] of allocatedResources) {
        if (job === jobName) {
            allocatedResources.delete(resource);
            log(`Resource ${resource} released from job ${jobName}`);
            processQueue(); // Try to allocate resources to queued jobs
            return resource;
        }
    }
    return null;
}

const server = http.createServer((req, res) => {
    const parsedUrl = url.parse(req.url, true);
    const path = parsedUrl.pathname.split('/');

    if (path[1] === 'allocate' && path[2]) {
        const jobName = path[2];
        const preference = path[3];
        log(`Received allocation request for job ${jobName}${preference ? ` with preference ${preference}` : ''}`);

        // Check if job is already allocated
        if (Array.from(allocatedResources.values()).includes(jobName)) {
            log(`Error: Job ${jobName} is already allocated a resource`);
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: `Job ${jobName} is already allocated a resource` }));
        } else if (preference && !['energy', 'performance', 'balanced'].includes(preference)) {
            log(`Error: Invalid preference ${preference} for job ${jobName}`);
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: `Invalid preference ${preference}` }));
        } else {
            jobQueue.push({ name: jobName, preference: preference });
            pendingRequests.set(jobName, res);
            log(`Job ${jobName} added to queue${preference ? ` with preference ${preference}` : ''}`);
            processQueue();
        }
    } else if (path[1] === 'release' && path[2]) {
        const jobName = path[2];
        log(`Received release request for job ${jobName}`);
        const releasedResource = releaseResource(jobName);
        if (releasedResource) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ resource: releasedResource, job: jobName, status: 'released' }));
        } else {
            log(`Error: Job ${jobName} not found or already released`);
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Job not found or already released' }));
        }
    } else {
        log(`Error: Invalid endpoint requested: ${req.url}`);
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Not Found' }));
    }
});

initializeResources();

server.listen(PORT, () => {
    log(`Server running on port ${PORT}`);
});

// Error handling for uncaught exceptions
process.on('uncaughtException', (error) => {
    log(`Uncaught Exception: ${error.message}`);
    log(error.stack);
});