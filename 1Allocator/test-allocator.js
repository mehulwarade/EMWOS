const http = require('http');

const SERVER_HOST = 'localhost';
const SERVER_PORT = 8000;
const TOTAL_JOBS = 180;
const REQUEST_TIMEOUT = 5000; // 5 seconds timeout for each request

const preferences = ['performance', 'energy', 'balanced'];
let allocateQueue = [];
let releaseQueue = [];
let activeJobs = new Set();
let pendingJobs = new Set();

function getRandomPreference() {
    return preferences[Math.floor(Math.random() * preferences.length)];
}

function generateJobs() {
    for (let i = 0; i < TOTAL_JOBS; i++) {
        allocateQueue.push({
            name: `job${i}`,
            preference: getRandomPreference(),
            operation: 'allocate'
        });
    }
}

function sendRequest(job) {
    return new Promise((resolve, reject) => {
        const path = job.operation === 'allocate'
            ? `/allocate/${job.name}/${job.preference}`
            : `/release/${job.name}`;

        const options = {
            hostname: SERVER_HOST,
            port: SERVER_PORT,
            path: path,
            method: 'GET'
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                if (res.statusCode === 202) {
                    // Job is pending
                    pendingJobs.add(job.name);
                    resolve({ job, response: { status: 'pending' }, statusCode: res.statusCode });
                } else {
                    resolve({ job, response: JSON.parse(data), statusCode: res.statusCode });
                }
            });
        });

        req.on('error', (error) => {
            reject(error);
        });

        req.setTimeout(REQUEST_TIMEOUT, () => {
            req.abort();
            resolve({ job, response: { error: 'Request timed out' }, statusCode: 408 });
        });

        req.end();
    });
}

async function runTest() {
    generateJobs();
    console.log(`Generated ${TOTAL_JOBS} jobs for allocation`);

    let requestOrder = [];
    let responseOrder = [];

    // Phase 1: Allocate jobs
    while (allocateQueue.length > 0 || releaseQueue.length > 0) {
        let job;
        if (allocateQueue.length > 0 && (releaseQueue.length === 0 || Math.random() < 0.7)) {
            // 70% chance to allocate when both queues have jobs
            job = allocateQueue.shift();
        } else if (releaseQueue.length > 0) {
            job = releaseQueue.shift();
        } else {
            continue; // This should never happen, but just in case
        }

        requestOrder.push(job.name);
        try {
            const result = await sendRequest(job);
            responseOrder.push(job.name);

            if (result.statusCode === 200) {
                if (job.operation === 'allocate') {
                    activeJobs.add(job.name);
                    console.log(`Job ${job.name} allocated to resource ${result.response.resource}`);
                    // Add to release queue with 50% probability
                    if (Math.random() < 0.5) {
                        releaseQueue.push({ name: job.name, operation: 'release' });
                    }
                } else { // release
                    activeJobs.delete(job.name);
                    console.log(`Job ${job.name} released resource ${result.response.resource}`);
                }
            } else if (result.statusCode === 202) {
                console.log(`Job ${job.name} is pending allocation`);
                pendingJobs.add(job.name);
            } else if (result.statusCode === 408) {
                console.log(`Request for job ${job.name} timed out`);
            } else {
                console.log(`Request for job ${job.name} failed with status ${result.statusCode}: ${result.response.error}`);
            }
        } catch (error) {
            console.error(`Error processing job ${job.name}:`, error);
        }
    }

    console.log('\nTest Summary:');
    console.log(`Total jobs processed: ${TOTAL_JOBS}`);
    console.log(`Active jobs at end of test: ${activeJobs.size}`);
    console.log(`Pending jobs at end of test: ${pendingJobs.size}`);

    // Check if the response order matches the request order
    const orderCorrect = requestOrder.every((job, index) => job === responseOrder[index]);
    console.log(`Requests processed in correct order: ${orderCorrect ? 'Yes' : 'No'}`);

    if (!orderCorrect) {
        console.log('Mismatched order detected:');
        requestOrder.forEach((job, index) => {
            if (job !== responseOrder[index]) {
                console.log(`Position ${index}: Expected ${job}, Got ${responseOrder[index]}`);
            }
        });
    }
}

runTest().catch(console.error);