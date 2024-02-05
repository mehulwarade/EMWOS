# EMWOS
EMWOS: Energy Monitoring and Workflow Optimization Scheduler system

This is the system developed during my PhD. This stores values coming from the smart plugs and store it into the database.

The time stored in database is in miliseconds.

Features:
- caching of the hostname by using IP (error handling for non-identifyable IP with hosts)
- dynamic options for mysql connection and port for the server
- logging to a file

# Energy Monitoring