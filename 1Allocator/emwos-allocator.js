// Started using from 25 March 2025


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

// Util to compress the available resources list.
const compressResources = (resources) => {
    // Group by base name (alpha, bravo, etc.)
    const groups = resources.reduce((acc, resource) => {
        const [slot, group] = resource.split('@');
        const slotNum = parseInt(slot.replace('slot', ''));
        if (!acc[group]) acc[group] = [];
        acc[group].push(slotNum);
        return acc;
    }, {});

    // Convert each group's numbers into ranges
    return Object.entries(groups).map(([group, slots]) => {
        slots.sort((a, b) => a - b);
        const ranges = [];
        let start = slots[0];
        let prev = slots[0];

        for (let i = 1; i <= slots.length; i++) {
            if (i === slots.length || slots[i] !== prev + 1) {
                ranges.push(start === prev ? start : `${start}-${prev}`);
                if (i < slots.length) {
                    start = slots[i];
                    prev = slots[i];
                }
            } else {
                prev = slots[i];
            }
        }

        return `${group}@${ranges.join(',')}`;
    }).join(' ');
}

const getServerState = () => {
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
        Overall State: ${JSON.stringify(overallState)}
        Available Resources: ${compressResources(availableResources)}
        Allocated Resources: ${JSON.stringify(allocatedResourcesObj)}
        Job Queue: ${JSON.stringify(jobQueue)}
        Pending Requests: ${JSON.stringify(pendingRequestsArray)}`;
}

const FindNextJobToScheduleBasedOnLowestExecutionNumber = () => {
    if (jobQueue.length === 0) return null; // redundant as we have while loop in process queue checking the same thing. keeping for sanity.
    let smallestExecJob = jobQueue[0];
    let smallestExecIndex = 0;
    for (let i = 1; i < jobQueue.length; i++) {
        if (jobQueue[i].executionNumber < smallestExecJob.executionNumber) {
            smallestExecJob = jobQueue[i];
            smallestExecIndex = i;
        }
    }
    if (smallestExecIndex !== 0) {
        log(`Note: Job ${jobQueue[0].name} (execution number ${jobQueue[0].executionNumber}) is next in queue, but scheduling ${smallestExecJob.name} first as it has lower execution number ${smallestExecJob.executionNumber}`);
    }
    // return the job with lease execution number and its index
    return { nextJob: smallestExecJob, nextJobIndex: smallestExecIndex };
}

// Updated to handle preference-based resource allocation
const FindNextResourceToScheduleTheJobOn = (preference = 'performance') => {
    // Get available resources (not allocated)
    const availableResources = resources.filter(resource => !allocatedResources.has(resource));

    if (availableResources.length === 0) {
        return null;
    }

    // Normalize preference to lowercase for case-insensitive comparison
    preference = preference.toLowerCase();

    // Log the preference being used for allocation
    log(`Allocating resource based on preference: ${preference}`);

    switch (preference) {
        case 'performance':
            // For performance, use any available resource (same as before)
            return availableResources[0];

        case 'balanced':
            // todo: can calculate this once so we don't have to calculate everytime when we get a request. like list of allowed nodes for different preferences.
            // For balanced, use only the first half of resource types (nodes)
            // First, identify all unique resource types (nodes)
            const uniqueNodes = [...new Set(resources.map(r => r.split('@')[1]))];
            const halfNodeCount = Math.ceil(uniqueNodes.length / 2);
            const allowedNodes = uniqueNodes.slice(0, halfNodeCount);

            log(`Balanced preference: Using only nodes ${allowedNodes.join(', ')}`);

            // Find first available resource from the allowed nodes
            const balancedResource = availableResources.find(r => {
                const node = r.split('@')[1];
                return allowedNodes.includes(node);
            });

            // If no resources available in allowed nodes, return null (wait until one becomes available)
            if (!balancedResource) {
                log(`No resources available for balanced preference, job will wait in queue`);
            }
            return balancedResource;

        case 'energy':
            // For energy, use only resources from the first node (alpha)
            const firstNode = resources[0].split('@')[1]; // Assuming first resource is from node 'alpha'
            log(`Energy preference: Using only node ${firstNode}`);

            // Find first available resource from the first node
            const energyResource = availableResources.find(r => r.includes(`@${firstNode}`));

            // If no resources available in first node, return null (wait until one becomes available)
            if (!energyResource) {
                log(`No resources available for energy preference, job will wait in queue`);
            }
            return energyResource;

        default:
            // For unknown preferences, default to performance behavior
            log(`Unknown preference: ${preference}, defaulting to performance mode`);
            return availableResources[0];
    }
}

const processQueue = () => {
    while (jobQueue.length > 0) {
        for (let i = 0; i < jobQueue.length; i++) {
            // get the next job to schedule and its index so that we can remove it once allocated.
            const { nextJob, nextJobIndex } = FindNextJobToScheduleBasedOnLowestExecutionNumber();

            // No job in queue, break
            if (!nextJob) {
                log('Warning: No next Job found in queue. This is unexpected.');
                break;
            }

            // Use the job's preference to find appropriate resource
            const resource = FindNextResourceToScheduleTheJobOn(nextJob.preference);

            // No resource available, no allocation needed. break.
            if (!resource) {
                log('Warning: No resource available. Job stored in queue and pendingRequests queue');
                break;
            }

            //* if job and resource both are available then proceed with allocation.
            allocatedResources.set(resource, {
                name: nextJob.name,
                executionNumber: nextJob.executionNumber
            });

            const res = pendingRequests.get(`${nextJob.name}-${nextJob.executionNumber}`);
            if (res) {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    resource: resource,
                    job: nextJob.name,
                    executionNumber: nextJob.executionNumber,
                    preference: nextJob.preference
                }));
                pendingRequests.delete(`${nextJob.name}-${nextJob.executionNumber}`);
                log(`Resource ${resource} allocated to job ${nextJob.name} (execution number: ${nextJob.executionNumber}, preference: ${nextJob.preference})`);
                // now remove the job from the jobQueue as we have allocated it.
                jobQueue.splice(nextJobIndex, 1);
            }
        }
        break;
    }
    log(`Current server state: ${getServerState()}`);
}

const server = http.createServer((req, res) => {
    const parsedUrl = url.parse(req.url, true);
    const path = parsedUrl.pathname.split('/');

    /* 
        Request at `/allocate/${jobName}/${executionNumber}/${preference}`
        For allocate:
    */
    if (path[1] === 'allocate' && path[2]) {
        const jobName = path[2];
        const executionNumber = parseInt(path[3]);
        const preference = path[4] || 'performance'; // Default to performance if not specified

        if (isNaN(executionNumber)) {
            // if execution number is null/ undefined then just log the warning but still schedule it. Don't crash or reject the request.
            log(`Warning: Received allocation request for job ${jobName} with invalid execution number ${executionNumber}.`);
        }
        else {
            log(`Received allocation request for job ${jobName} with execution number ${executionNumber} and preference ${preference}`);
        }

        //* sub-utility to find if the job is already allocated or not.
        const isJobAllocated = (jobName, executionNumber) => {
            // ! update 10/11/2024: cannot have unique job name checks in the both if statement below as multiple workflow can have the same job name. let's check for unique execution number.
            for (const [_, jobInfoInAllocated] of allocatedResources) {
                // if job is already allocated or if the same execution is already allocated then return true.
                // Originally: if (jobInfoInAllocated.name === jobName || jobInfoInAllocated.executionNumber === executionNumber)
                if (jobInfoInAllocated.executionNumber === executionNumber) {
                    return true;
                }
            }
            // todo: if we get a post request while the job is not allocated, should we remove from the queue? currently it is leaving it as it is.
            for (const jobInfoInQueue of jobQueue) {
                // if job is in queue then return true.
                // Originally: if (jobInfoInQueue.name === jobName || jobInfoInQueue.executionNumber === executionNumber)
                if (jobInfoInQueue.executionNumber === executionNumber) {
                    return true;
                }
            }
            return false;
        }

        if (isJobAllocated(jobName, executionNumber)) {
            log(`warning: Requested for Job ${jobName} with execution number ${executionNumber} is already allocated a resource or already queued for allocation. Do not send request again.`);
            // still do not crash. send a warning and let the pre scrip complete successfully.
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                warning: `Requested for Job ${jobName} with execution number ${executionNumber} is already allocated a resource or already queued for allocation. Do not send request again.`
            }));
        } else {
            // if job is not already allocated or execution number is unique or has been released before: add to the queue to be scheduled.
            jobQueue.push({ name: jobName, executionNumber: executionNumber, preference: preference });
            pendingRequests.set(`${jobName}-${executionNumber}`, res);
            log(`Job ${jobName} added to queue with execution number ${executionNumber} and preference ${preference}`);
            processQueue();
        }
    }
    /*
        Request at `/release/${jobName}`
        No need for execution number here.
        For release:
    */
    else if (path[1] === 'release' && path[2]) {
        const jobName = path[2];
        log(`Received release request for job ${jobName}`);

        //* sub-utility to find the resource for the job
        const FindAndReleaseResource = (jobName) => {
            for (let [resource, jobInfo] of allocatedResources) {
                if (jobInfo.name === jobName) {
                    allocatedResources.delete(resource);
                    log(`Resource ${resource} released from job ${jobName}`);
                    // process job queue as we have a resource available now.
                    processQueue();
                    return resource;
                }
            }
            return null;
        }

        const releasedResource = FindAndReleaseResource(jobName);
        if (releasedResource) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                resource: releasedResource,
                job: jobName,
                status: 'released'
            }));
        } else {
            log(`Error: Job ${jobName} not found, already released or not in allocated resources queue`);
            // do not crash. we received a request to release a job but could not find it. No harm done. Just let the post request complete.
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ warning: 'Job not found or already released' }));
        }
    } else {
        log(`Error: Invalid endpoint requested: ${req.url}`);
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Not Found' }));
    }
});

function initializeResources() {
    try {
        const data = fs.readFileSync(RESOURCES_FILE, 'utf8');
        resources = data.split('\n').filter(line => line.trim() !== '');
        // log(`Resources loaded: ${resources.join(', ')}`);
        log(`Resources loaded: ${resources.length}`);
    } catch (err) {
        log(`Error reading resources file: ${err}`);
        process.exit(1);
    }
}

initializeResources();

server.listen(PORT, () => {
    log(`Server running on port ${PORT}`);
});

// Important. Without this the server will send a socket hangup after 2min to requests.
// Ref: https://stackoverflow.com/a/58372968
server.timeout = 0;

process.on('uncaughtException', (error) => {
    log(`Uncaught Exception: ${error.message}`);
    log(error.stack);
});