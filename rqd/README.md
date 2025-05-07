# RQD

RQD is a software client that runs on all hosts doing work for an OpenCue
deployment.

RQD's responsibilities include:

- Registering the host with Cuebot.
- Receiving instructions about what work to do.
- Monitoring the worker processes it launches and reporting on results.

RQD uses [gRPC](https://grpc.io/) to communicate with Cuebot. It also runs its
own gRPC server, which is called by the Cuebot client to send instructions to
RQD.

## How to start rqd from source

### Setup python environment
```bash
# Create virtual environment
python3 -m venv OpenCue-venv
# Activate virtual environment
source OpenCue-venv/bin/activate
# Change directory to Opencue source
cd <OpenCueSourceDir>

# Install compiled proto files which is needed by RQD into the virtual environment
pip install ./proto

# Install RQD into the virtual environment
pip install ./rqd
```

### Create rqd.conf
Example `rqd.conf` file :

```ini
[Override]
# Variable that decided if RQD should switch to the user of the job running. Requires root
RQD_BECOME_JOB_USER = False

# Log levels for RQD
CONSOLE_LOG_LEVEL = INFO
FILE_LOG_LEVEL = ERROR

# Number of seconds to wait before checking if the user has become idle.
CHECK_INTERVAL_LOCKED = 60
# Seconds of idle time required before NIMBY (Not In My BackYard) unlocks.
MINIMUM_IDLE = 900

# Whether or not to prefix each line in the log with a timestamp
RQD_PREPEND_TIMESTAMP = 0
```

### Run rqd
(using the above virtual environment)
```bash
rqd -c <path to rqd.conf>
```
