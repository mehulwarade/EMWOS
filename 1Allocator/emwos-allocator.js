const http = require('http');
const fs = require('fs');
const url = require('url');
const path = require('path');

const PORT = 8000;
const RESOURCES_FILE = 'resources.txt';
// Generate unique log file name with timestamp
const LOG_FILE = `server_${new Date().toISOString().replace(/[:.]/g, '-')}.log`;
const LOG_DIR = 'logs';

// Create logs directory if it doesn't exist
if (!fs.existsSync(LOG_DIR)) {
    fs.mkdirSync(LOG_DIR);
}

let resources = [];
let allocatedResources = new Map(); // Map<resource, {name: string, executionNumber: number}>
let jobQueue = [];
let pendingRequests = new Map();

// Logging function
function log(message) {
    const now = new Date();
    const humanReadableTime = now.toLocaleString();
    const unixTimestamp = Math.floor(now.getTime() / 1000);
    const logMessage = `[${humanReadableTime}] [${unixTimestamp}] ${message}\n`;
    console.log(logMessage.trim());
    fs.appendFileSync(path.join(LOG_DIR, LOG_FILE), logMessage);
}

// Log server start with log file information
log(`Server starting - logging to ${LOG_FILE}`);

function getServerState() {
    const availableResources = resources.filter(r => !allocatedResources.has(r));
    const allocatedResourcesObj = Object.fromEntries(
        Array.from(allocatedResources.entries()).map(([resource, jobInfo]) => [
            resource,
            { job: jobInfo.name, executionNumber: jobInfo.executionNumber }
        ])
    );
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

function NextJobToSchedule() {
    if (jobQueue.length === 0) return null;

    let smallestExecJob = jobQueue[0];
    let smallestExecIndex = 0;

    for (let i = 1; i < jobQueue.length; i++) {
        if (jobQueue[i].executionNumber < smallestExecJob.executionNumber) {
            smallestExecJob = jobQueue[i];
            smallestExecIndex = i;
        }
    }

    if (smallestExecIndex !== 0) {
        log(`Note: Job ${jobQueue[0].name} is next in queue, but scheduling ${smallestExecJob.name} first as it has lower execution number (${smallestExecJob.executionNumber} vs ${jobQueue[0].executionNumber})`);
    }

    jobQueue.splice(smallestExecIndex, 1);
    return smallestExecJob;
}

function NextResourceAvailable(jobPreference) {
    return resources.find(resource => !allocatedResources.has(resource));
}

function isJobAllocated(jobName, executionNumber) {
    for (const [_, jobInfo] of allocatedResources) {
        if (jobInfo.name === jobName && jobInfo.executionNumber === executionNumber) {
            return true;
        }
    }
    return false;
}

function processQueue() {
    let processedJobs = new Set();
    let allocatedThisRound = false;

    while (jobQueue.length > 0) {
        const initialQueueLength = jobQueue.length;
        allocatedThisRound = false;

        for (let i = 0; i < initialQueueLength; i++) {
            const nextJob = NextJobToSchedule();
            if (!nextJob) break;

            const availableResource = NextResourceAvailable(nextJob.preference);

            if (availableResource) {
                allocatedResources.set(availableResource, {
                    name: nextJob.name,
                    executionNumber: nextJob.executionNumber
                });
                const res = pendingRequests.get(`${nextJob.name}-${nextJob.executionNumber}`);
                if (res) {
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        resource: availableResource,
                        job: nextJob.name,
                        executionNumber: nextJob.executionNumber
                    }));
                    pendingRequests.delete(`${nextJob.name}-${nextJob.executionNumber}`);
                    log(`Resource ${availableResource} allocated to job ${nextJob.name} (execution number: ${nextJob.executionNumber})`);
                }
                processedJobs.add(`${nextJob.name}-${nextJob.executionNumber}`);
                allocatedThisRound = true;
            } else {
                jobQueue.push(nextJob);
                log(`No suitable resources available for job ${nextJob.name} (execution number: ${nextJob.executionNumber}). Moved to end of queue.`);
            }
        }

        if (!allocatedThisRound) {
            log("No more allocations possible. Ending queue processing.");
            break;
        }
    }

    log(`Current server state: ${getServerState()}`);
}

function releaseResource(jobName, executionNumber) {
    for (let [resource, jobInfo] of allocatedResources) {
        if (jobInfo.name === jobName && jobInfo.executionNumber === executionNumber) {
            allocatedResources.delete(resource);
            log(`Resource ${resource} released from job ${jobName} (execution number: ${executionNumber})`);
            processQueue();
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
        const executionNumber = parseInt(path[3]);

        if (isNaN(executionNumber)) {
            log(`Error: Invalid execution number for job ${jobName}`);
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: `Invalid execution number for job ${jobName}` }));
            return;
        }

        log(`Received allocation request for job ${jobName} with execution number ${executionNumber}`);

        if (isJobAllocated(jobName, executionNumber)) {
            log(`Error: Job ${jobName} with execution number ${executionNumber} is already allocated a resource`);
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                error: `Job ${jobName} with execution number ${executionNumber} is already allocated a resource`
            }));
        } else {
            jobQueue.push({ name: jobName, executionNumber: executionNumber });
            pendingRequests.set(`${jobName}-${executionNumber}`, res);
            log(`Job ${jobName} added to queue with execution number ${executionNumber}`);
            processQueue();
        }
    } else if (path[1] === 'release' && path[2]) {
        const jobName = path[2];
        const executionNumber = parseInt(path[3]);

        if (isNaN(executionNumber)) {
            log(`Error: Invalid execution number for release of job ${jobName}`);
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: `Invalid execution number for job ${jobName}` }));
            return;
        }

        log(`Received release request for job ${jobName} with execution number ${executionNumber}`);
        const releasedResource = releaseResource(jobName, executionNumber);
        if (releasedResource) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                resource: releasedResource,
                job: jobName,
                executionNumber: executionNumber,
                status: 'released'
            }));
        } else {
            log(`Error: Job ${jobName} with execution number ${executionNumber} not found or already released`);
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

process.on('uncaughtException', (error) => {
    log(`Uncaught Exception: ${error.message}`);
    log(error.stack);
});