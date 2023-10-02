# EMWOS
EMWOS: Energy Monitoring and Workflow Optimization Scheduler system

This is the system developed during my PhD. This stores values coming from the smart plugs and store it into the database.

The time stored in database is in miliseconds.

Features:
- caching of the hostname by using IP (error handling for non-identifyable IP with hosts)
- dynamic options for mysql connection and port for the server
- logging to a file

# Energy Monitoring
This needs the library mysql-connector-python for python in order to work.

Install with:
<!-- https://askubuntu.com/a/754389 -->

APT: ```sudo apt install python3-mysql.connector```

PIP3: ```pip3 install mysql-connector-python```

Test with: ```import mysql.connector``` in python3 env


### Test with ThunderClient

URL: http://localhost:8443

Body (JSON):

```json
{
  "value": 4256456312168532
}
```