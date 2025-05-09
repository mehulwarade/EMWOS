// 25 March 2025 decomissioned

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

// ! just returning the NOT allocated resource. Can add logic for smartly providing the resource in future
const FindNextResourceToScheduleTheJobOn = () => {
    return resources.find(resource => !allocatedResources.has(resource));
}

const processQueue = () => {
    while (jobQueue.length > 0) {
        for (let i = 0; i < jobQueue.length; i++) {
            // get the next job to schedule and its index so that we can remove it once allocated.

            const { nextJob, nextJobIndex } = FindNextJobToScheduleBasedOnLowestExecutionNumber();
            // todo: can add logic here. for example: pass the tags for the job or the name or the execution number. smartly return the resource based on some logic.
            const resource = FindNextResourceToScheduleTheJobOn();
            // no job in queue or no resource available, no allocation needed. break.
            // todo: might be redundant as if there is no next job then the while loop will never be entered as this means there are no jobs in queue.
            if (!nextJob || !resource) {
                log('Warning: No next Job or No resource available. Job stored in queue and pendingRequests queue');
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
                    executionNumber: nextJob.executionNumber
                }));
                pendingRequests.delete(`${nextJob.name}-${nextJob.executionNumber}`);
                log(`Resource ${resource} allocated to job ${nextJob.name} (execution number: ${nextJob.executionNumber})`);
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
        Request at `/allocate/${jobName}/${executionNumber}`
        For allocate:
    */
    if (path[1] === 'allocate' && path[2]) {
        const jobName = path[2];
        const executionNumber = parseInt(path[3]);
        if (isNaN(executionNumber)) {
            // if execution number is null/ undefined then just log the warning but still scehdule it. Don't crash or reject the request.
            log(`Warning: Received allocation request for job ${jobName} with invalid execution number ${executionNumber}.`);
        }
        else {
            log(`Received allocation request for job ${jobName} with execution number ${executionNumber}`);
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
            jobQueue.push({ name: jobName, executionNumber: executionNumber });
            pendingRequests.set(`${jobName}-${executionNumber}`, res);
            log(`Job ${jobName} added to queue with execution number ${executionNumber}`);
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