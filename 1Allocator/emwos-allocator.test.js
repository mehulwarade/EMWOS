#!/usr/bin/env node

const http = require('http');

const SERVER_HOST = 'localhost';
const SERVER_PORT = 8000;
const REQUEST_TIMEOUT = 5000; // 5 seconds timeout

// Configuration for stress testing
const TEST_CONFIG = {
    TOTAL_JOBS: 180,
    CONCURRENT_REQUESTS: 10,  // Number of concurrent requests
    DELAY_BETWEEN_BATCHES: 1000, // ms delay between batches
    RANDOM_DELAY_MAX: 500,    // Maximum random delay between requests (ms)
    OUT_OF_ORDER_PROBABILITY: 0.3 // Probability of sending jobs out of execution order
};

class JobTest {
    constructor() {
        this.allocateQueue = [];
        this.releaseQueue = [];
        this.activeJobs = new Set();
        this.pendingJobs = new Set();
        this.jobResults = new Map(); // Track results for each job
        this.startTime = null;
        this.metrics = {
            totalRequests: 0,
            successfulAllocations: 0,
            failedAllocations: 0,
            successfulReleases: 0,
            failedReleases: 0,
            timeouts: 0,
            averageResponseTime: 0,
            totalResponseTime: 0
        };
    }

    generateJobs() {
        // Generate jobs with execution numbers
        for (let i = 0; i < TEST_CONFIG.TOTAL_JOBS; i++) {
            const executionNumber = i + 1;
            // Sometimes assign out-of-order execution numbers to test scheduling
            const actualExecutionNumber = Math.random() < TEST_CONFIG.OUT_OF_ORDER_PROBABILITY
                ? Math.floor(Math.random() * TEST_CONFIG.TOTAL_JOBS) + 1
                : executionNumber;

            this.allocateQueue.push({
                name: `job${i}`,
                executionNumber: actualExecutionNumber,
                operation: 'allocate',
                requestTime: null,
                responseTime: null
            });
        }
        console.log(`Generated ${TEST_CONFIG.TOTAL_JOBS} jobs for testing`);
    }

    sendRequest(job) {
        return new Promise((resolve, reject) => {
            const path = job.operation === 'allocate'
                ? `/allocate/${job.name}/${job.executionNumber}`
                : `/release/${job.name}`;

            const options = {
                hostname: SERVER_HOST,
                port: SERVER_PORT,
                path: path,
                method: 'GET'
            };

            job.requestTime = Date.now();

            const req = http.request(options, (res) => {
                let data = '';
                res.on('data', (chunk) => data += chunk);
                res.on('end', () => {
                    job.responseTime = Date.now();
                    const responseTime = job.responseTime - job.requestTime;

                    this.metrics.totalResponseTime += responseTime;
                    this.metrics.totalRequests++;

                    try {
                        const response = JSON.parse(data);
                        resolve({
                            job,
                            response,
                            statusCode: res.statusCode,
                            responseTime
                        });
                    } catch (e) {
                        resolve({
                            job,
                            response: { error: 'Invalid JSON response' },
                            statusCode: res.statusCode,
                            responseTime
                        });
                    }
                });
            });

            req.on('error', (error) => {
                job.responseTime = Date.now();
                this.metrics.totalRequests++;
                reject(error);
            });

            req.setTimeout(REQUEST_TIMEOUT, () => {
                req.abort();
                job.responseTime = Date.now();
                this.metrics.timeouts++;
                this.metrics.totalRequests++;
                resolve({
                    job,
                    response: { error: 'Request timed out' },
                    statusCode: 408,
                    responseTime: REQUEST_TIMEOUT
                });
            });

            req.end();
        });
    }

    async processBatch(jobs) {
        const results = await Promise.all(jobs.map(job =>
            this.sendRequest(job).catch(error => ({
                job,
                response: { error: error.message },
                statusCode: 500,
                responseTime: Date.now() - job.requestTime
            }))
        ));

        results.forEach(result => {
            if (result.statusCode === 200) {
                if (result.job.operation === 'allocate') {
                    this.metrics.successfulAllocations++;
                    this.activeJobs.add(result.job.name);
                    this.releaseQueue.push({
                        ...result.job,
                        operation: 'release'
                    });
                } else {
                    this.metrics.successfulReleases++;
                    this.activeJobs.delete(result.job.name);
                }
            } else {
                if (result.job.operation === 'allocate') {
                    this.metrics.failedAllocations++;
                } else {
                    this.metrics.failedReleases++;
                }
            }
            this.jobResults.set(result.job.name, result);
        });
    }

    printProgress() {
        const elapsed = Date.now() - this.startTime;
        const progress = ((this.metrics.totalRequests / (TEST_CONFIG.TOTAL_JOBS * 2)) * 100).toFixed(2);

        console.clear();
        console.log(`Progress: ${progress}%`);
        console.log(`Elapsed Time: ${(elapsed / 1000).toFixed(2)}s`);
        console.log(`Active Jobs: ${this.activeJobs.size}`);
        console.log(`Pending Jobs: ${this.pendingJobs.size}`);
        console.log(`Successful Allocations: ${this.metrics.successfulAllocations}`);
        console.log(`Failed Allocations: ${this.metrics.failedAllocations}`);
        console.log(`Successful Releases: ${this.metrics.successfulReleases}`);
        console.log(`Failed Releases: ${this.metrics.failedReleases}`);
        console.log(`Timeouts: ${this.metrics.timeouts}`);
        console.log(`Average Response Time: ${(this.metrics.totalResponseTime / this.metrics.totalRequests).toFixed(2)}ms`);
    }

    printFinalReport() {
        console.log('\n=== Final Test Report ===');
        console.log(`Total Jobs: ${TEST_CONFIG.TOTAL_JOBS}`);
        console.log(`Total Requests: ${this.metrics.totalRequests}`);
        console.log(`Total Time: ${((Date.now() - this.startTime) / 1000).toFixed(2)}s`);
        console.log('\nMetrics:');
        console.log(`- Successful Allocations: ${this.metrics.successfulAllocations}`);
        console.log(`- Failed Allocations: ${this.metrics.failedAllocations}`);
        console.log(`- Successful Releases: ${this.metrics.successfulReleases}`);
        console.log(`- Failed Releases: ${this.metrics.failedReleases}`);
        console.log(`- Timeouts: ${this.metrics.timeouts}`);
        console.log(`- Average Response Time: ${(this.metrics.totalResponseTime / this.metrics.totalRequests).toFixed(2)}ms`);

        // Analyze execution order
        console.log('\nExecution Order Analysis:');
        const orderedResults = Array.from(this.jobResults.values())
            .filter(r => r.statusCode === 200)
            .sort((a, b) => a.job.executionNumber - b.job.executionNumber);

        let orderViolations = 0;
        for (let i = 1; i < orderedResults.length; i++) {
            if (orderedResults[i].responseTime < orderedResults[i - 1].responseTime) {
                orderViolations++;
            }
        }
        console.log(`- Execution Order Violations: ${orderViolations}`);
    }

    async runTest() {
        this.generateJobs();
        this.startTime = Date.now();

        // Process allocations
        while (this.allocateQueue.length > 0) {
            const batch = this.allocateQueue.splice(0, TEST_CONFIG.CONCURRENT_REQUESTS);
            await this.processBatch(batch);
            this.printProgress();
            if (this.allocateQueue.length > 0) {
                await new Promise(r => setTimeout(r, TEST_CONFIG.DELAY_BETWEEN_BATCHES));
            }
        }

        // Process releases
        while (this.releaseQueue.length > 0) {
            const batch = this.releaseQueue.splice(0, TEST_CONFIG.CONCURRENT_REQUESTS);
            await this.processBatch(batch);
            this.printProgress();
            if (this.releaseQueue.length > 0) {
                await new Promise(r => setTimeout(r, TEST_CONFIG.DELAY_BETWEEN_BATCHES));
            }
        }

        this.printFinalReport();
    }
}

// Run the test
const tester = new JobTest();
tester.runTest().catch(console.error);