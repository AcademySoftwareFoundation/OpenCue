# Running OpenCue Hybrid RQD Setup using Sandbox

This guide shows you how to run OpenCue with CueBot and a Linux RQD in Docker, while adding your local macOS, Windows, or Linux machine as an additional render node for testing tools like CueNIMBY.

## Overview

This hybrid setup consists of:
- **CueBot** (Docker): The central controller running in a container
- **PostgreSQL Database** (Docker): Database backend for CueBot
- **Linux RQD** (Docker): A Linux render node running in a container
- **macOS/Windows/Linux RQD** (Native): Your local workstation as a render node

## Prerequisites

- Docker Desktop installed and running
- Python 3.7+ installed on your local machine
- Git (to clone OpenCue repository)
- At least 6GB of RAM allocated to Docker Desktop (on macOS/Windows)

## Part 1: Start Docker Services (CueBot + Linux RQD)

### Important Note About RQD Ports

**CueBot connects to ALL RQD instances using a single configured port (default: 8444).** This means:
- If you want your native macOS/Windows RQD to be manageable by CueBot, it MUST run on port 8444
- To avoid port conflicts, the Docker RQD port mapping can be removed from `docker-compose.yml` (see example below)
- The Docker Linux RQD will still register with CueBot using internal container networking
- Both RQD instances (Docker Linux and native macOS/Windows) can coexist and be managed by CueBot

### Step 1: Update docker-compose.yml (If Not Already Done)

Edit `docker-compose.yml` and comment out the RQD port mapping:

```yaml
  rqd:
    image: opencue/rqd
    environment:
      - PYTHONUNBUFFERED=1
      - CUEBOT_HOSTNAME=cuebot
    depends_on:
      cuebot:
        condition: service_healthy
    links:
      - cuebot
    # Port mapping removed to allow native macOS/Windows RQD to use port 8444
    # ports:
    #   - "8444:8444"
    volumes:
      - /tmp/rqd/logs:/tmp/rqd/logs
      - /tmp/rqd/shots:/tmp/rqd/shots
```

### Step 2: Start the Docker Compose Stack

From the OpenCue root directory:

```bash
docker compose up
```

This will start:
- PostgreSQL database (port 5432)
- CueBot gRPC server (port 8443)
- Linux RQD (internal container port 8444, no host port mapping)

Wait for all services to be healthy. You should see messages like:
```
cuebot_1  | Started CuebotApplication in X.XXX seconds
rqd_1     | WARNING   rqd3-rqcore     RQD Started
```

### Step 3: Verify Docker Services

Check that all services are running:

```bash
docker compose ps
```

You should see `cuebot`, `db`, and `rqd` all in "Up" state.

## Part 2: Set Up Your Local Machine as a Render Node

### For macOS

#### Step 1: Create Required Directories

```bash
mkdir -p /tmp/rqd/logs /tmp/rqd/shots
```

#### Step 2: Set Up Python Virtual Environment

```bash
# Create virtual environment if it doesn't exist
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install OpenCue client packages (including RQD)
./sandbox/install-client-sources.sh

# Install RQD specifically
pip install ./rqd
```

#### Step 3: Create RQD Configuration File

Create a file named `rqd_macos.conf` (if macOS) in the OpenCue root directory:

```ini
# RQD configuration file for macOS workstation
# This configuration is optimized for testing CueNIMBY on a development machine

[Override]
# Don't switch to job user (important for macOS workstation)
RQD_BECOME_JOB_USER = False

# Use PATH environment variable
RQD_USE_PATH_ENV_VAR = 1

# Don't use IP as hostname
RQD_USE_IP_AS_HOSTNAME = 0

# Mark this as a desktop machine (important for workstation use)
OVERRIDE_IS_DESKTOP = True

# Enable NIMBY mode for workstation protection
OVERRIDE_NIMBY = True

# Number of seconds to wait before checking if the user has become idle
CHECK_INTERVAL_LOCKED = 60

# Seconds of idle time required before nimby unlocks (15 minutes)
MINIMUM_IDLE = 900

# Logging levels
CONSOLE_LOG_LEVEL = INFO
FILE_LOG_LEVEL = ERROR

# Don't prepend timestamps (cleaner logs)
RQD_PREPEND_TIMESTAMP = 0

# Set log size limit (1GB)
JOB_LOG_MAX_SIZE_IN_BYTES = 1073741824

# Use the standard RQD port 8444 (same as CueBot expects)
# This will NOT conflict with Docker RQD if you removed the port mapping
RQD_GRPC_PORT = 8444
```

#### Step 4: Start RQD

In a new terminal window:

```bash
# Activate virtual environment
source venv/bin/activate

# Start RQD connecting to CueBot on localhost
CUEBOT_HOSTNAME=localhost rqd -c rqd_macos.conf
```

You should see output like:
```
WARNING   openrqd-__main__  : RQD Starting Up
WARNING   openrqd-rqcore    : Nimby startup has been enabled via OVERRIDE_NIMBY
WARNING   openrqd-rqcore    : RQD Started
```

**Note:** You may see some pynput errors related to input monitoring. These are non-critical and don't affect RQD's core functionality.

### For Windows

#### Step 1: Create Required Directories

In PowerShell or Command Prompt:

```powershell
# PowerShell
New-Item -ItemType Directory -Force -Path C:\tmp\rqd\logs
New-Item -ItemType Directory -Force -Path C:\tmp\rqd\shots
```

```cmd
# Command Prompt
mkdir C:\tmp\rqd\logs
mkdir C:\tmp\rqd\shots
```

#### Step 2: Set Up Python Virtual Environment

```powershell
# PowerShell - from OpenCue root directory
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install OpenCue client packages (including RQD)
.\sandbox\install-client-sources.sh

# Install RQD specifically
pip install .\rqd
```

```cmd
# Command Prompt - from OpenCue root directory
python -m venv venv
.\venv\Scripts\activate.bat

# Install OpenCue client packages (including RQD)
.\sandbox\install-client-sources.sh

# Install RQD specifically
pip install .\rqd
```

#### Step 3: Create RQD Configuration File

Create a file named `rqd_windows.conf` (if Windows) in the OpenCue root directory:

```ini
# RQD configuration file for Windows workstation
# This configuration is optimized for testing CueNIMBY on a development machine

[Override]
# Don't switch to job user (important for Windows workstation)
RQD_BECOME_JOB_USER = False

# Use PATH environment variable
RQD_USE_PATH_ENV_VAR = 1

# Don't use IP as hostname
RQD_USE_IP_AS_HOSTNAME = 0

# Mark this as a desktop machine (important for workstation use)
OVERRIDE_IS_DESKTOP = True

# Enable NIMBY mode for workstation protection
OVERRIDE_NIMBY = True

# Number of seconds to wait before checking if the user has become idle
CHECK_INTERVAL_LOCKED = 60

# Seconds of idle time required before nimby unlocks (15 minutes)
MINIMUM_IDLE = 900

# Logging levels
CONSOLE_LOG_LEVEL = INFO
FILE_LOG_LEVEL = ERROR

# Don't prepend timestamps (cleaner logs)
RQD_PREPEND_TIMESTAMP = 0

# Set log size limit (1GB)
JOB_LOG_MAX_SIZE_IN_BYTES = 1073741824

# Use the standard RQD port 8444 (same as CueBot expects)
# This will NOT conflict with Docker RQD if you removed the port mapping
RQD_GRPC_PORT = 8444

# Windows-specific: Set temp directory
RQD_TMPDIR = C:\tmp\rqd
```

#### Step 4: Start RQD

In a new terminal window:

```powershell
# PowerShell
.\venv\Scripts\Activate.ps1
$env:CUEBOT_HOSTNAME = "localhost"
rqd -c rqd_windows.conf
```

```cmd
# Command Prompt
.\venv\Scripts\activate.bat
set CUEBOT_HOSTNAME=localhost
rqd -c rqd_windows.conf
```

You should see output like:
```
WARNING   openrqd-__main__  : RQD Starting Up
WARNING   openrqd-rqcore    : Nimby startup has been enabled via OVERRIDE_NIMBY
WARNING   openrqd-rqcore    : RQD Started
```

### For Linux

#### Step 1: Create Required Directories

```bash
mkdir -p /tmp/rqd/logs /tmp/rqd/shots
```

#### Step 2: Set Up Python Virtual Environment

```bash
# Create virtual environment if it doesn't exist
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install OpenCue client packages (including RQD)
./sandbox/install-client-sources.sh

# Install RQD specifically
pip install ./rqd
```

#### Step 3: Create RQD Configuration File

Create a file named `rqd_linux.conf` in the OpenCue root directory (or use the provided `sandbox/rqd_linux.conf`):

```ini
# RQD configuration file for Linux workstation
# This configuration is optimized for testing CueNIMBY on a development machine

[Override]
# Don't switch to job user (set to True for production with proper user setup)
RQD_BECOME_JOB_USER = False

# Use PATH environment variable
RQD_USE_PATH_ENV_VAR = 1

# Don't use IP as hostname
RQD_USE_IP_AS_HOSTNAME = 0

# Mark this as a desktop machine (important for workstation use)
OVERRIDE_IS_DESKTOP = True

# Enable NIMBY mode for workstation protection
OVERRIDE_NIMBY = True

# Number of seconds to wait before checking if the user has become idle
CHECK_INTERVAL_LOCKED = 60

# Seconds of idle time required before nimby unlocks (15 minutes)
MINIMUM_IDLE = 900

# Logging levels
CONSOLE_LOG_LEVEL = INFO
FILE_LOG_LEVEL = ERROR

# Don't prepend timestamps (cleaner logs)
RQD_PREPEND_TIMESTAMP = 0

# Set log size limit (1GB)
JOB_LOG_MAX_SIZE_IN_BYTES = 1073741824

# Use the standard RQD port 8444 (same as CueBot expects)
# This will NOT conflict with Docker RQD if you removed the port mapping
RQD_GRPC_PORT = 8444

# Linux-specific: Temp directory for job data
# RQD_TMPDIR = /tmp

# Linux-specific: Default cores (leave commented to auto-detect)
# DEFAULT_CORES = 4

# Linux-specific: Default memory in MB (leave commented to auto-detect)
# DEFAULT_MEMORY = 8192
```

#### Step 4: Start RQD

In a new terminal window:

```bash
# Activate virtual environment
source venv/bin/activate

# Start RQD connecting to CueBot on localhost
CUEBOT_HOSTNAME=localhost rqd -c rqd_linux.conf
```

You should see output like:
```
WARNING   openrqd-__main__  : RQD Starting Up
WARNING   openrqd-rqcore    : Nimby startup has been enabled via OVERRIDE_NIMBY
WARNING   openrqd-rqcore    : RQD Started
```

**Note:** On some Linux distributions, you may need to grant accessibility permissions for input monitoring. Check your desktop environment's settings (e.g., GNOME Privacy settings, KDE System Settings).

## Part 3: Verify Your Setup

### Check Registered Hosts

With the virtual environment activated:

```bash
# macOS/Linux
source venv/bin/activate
cueadmin -server localhost:8443 -lh

# Windows PowerShell
.\venv\Scripts\Activate.ps1
cueadmin -server localhost:8443 -lh

# Windows Command Prompt
.\venv\Scripts\activate.bat
cueadmin -server localhost:8443 -lh
```

You should see both hosts listed:
```
Host            Load NIMBY freeMem  freeSwap freeMcp   Cores Mem   Idle             Os       Uptime   State  Locked    Alloc      Thread
123.456.789.0      275  False 4.6G     1.5G     142.0G    9.0   8.5G  [ 9.00 / 8.5G ]  Linux    08:01    UP     OPEN      local.general AUTO
your-hostname   0    True  1.1G     0K       69081.3G  1.0   12.2G [ 1.00 / 12.2G ] Darwin   20390:18 UP     OPEN      local.general ALL
```

- **123.456.789.0**: Your Docker Linux RQD
- **your-hostname**: Your local macOS/Windows machine

### Check Port Usage

Verify that your native RQD is listening on port 8444:

```bash
# macOS/Linux
lsof -i :8444  # Should show your native RQD (Python process)

# Windows PowerShell
netstat -an | Select-String "8444"

# Windows Command Prompt
netstat -an | findstr "8444"
```

Note: The Docker RQD runs on port 8444 inside its container but doesn't expose it to the host, so you won't see it in the host's port listings.

## Part 4: Run CueNIMBY

Now that your local machine is registered as a render node, you can test CueNIMBY.

### Start CueNIMBY

In a new terminal with the virtual environment activated:

```bash
# macOS/Linux
source venv/bin/activate
cuenimby --verbose

# Windows PowerShell
.\venv\Scripts\Activate.ps1
cuenimby --verbose

# Windows Command Prompt
.\venv\Scripts\activate.bat
cuenimby --verbose
```

You should see:
```
2025-10-29 10:58:09 - cuenimby.__main__ - INFO - Starting CueNIMBY v1.14.1+eaaa8689
2025-10-29 10:58:09 - cuenimby.__main__ - INFO - Connecting to Cuebot at localhost:8443
2025-10-29 10:58:09 - cuenimby.monitor - INFO - Connected to Cuebot at localhost:8443
2025-10-29 10:58:09 - cuenimby.tray - INFO - CueNIMBY tray initialized
```

CueNIMBY should now show your machine status and allow you to control NIMBY (prevent job execution when you're using your workstation).

## Part 5: Run Other OpenCue Tools

With both Docker and native RQD running, you can now test all OpenCue client tools:

### CueGUI (Graphical Interface)

```bash
# macOS/Linux
source venv/bin/activate
cuegui

# Windows
.\venv\Scripts\Activate.ps1
cuegui
```

### CueSubmit (Job Submission Tool)

```bash
# macOS/Linux
source venv/bin/activate
cuesubmit

# Windows
.\venv\Scripts\Activate.ps1
cuesubmit
```

### CueAdmin (Command-Line Administration)

```bash
# View all hosts
cueadmin -server localhost:8443 -lh

# View all shows
cueadmin -server localhost:8443 -ls

# View jobs
cueadmin -server localhost:8443 -lj
```

## Troubleshooting

### Issue: "Failed to find host" in CueNIMBY

**Cause:** RQD is not running or hasn't registered with CueBot.

**Solution:**
1. Check that your native RQD is running (`ps aux | grep rqd` on macOS/Linux or Task Manager on Windows)
2. Verify RQD is listening on port 8445
3. Check RQD logs for connection errors
4. Restart RQD if necessary

### Issue: Port 8444 Already in Use

**Cause:** Another process is using port 8444, or you didn't remove the Docker RQD port mapping.

**Solution:**
1. Ensure the Docker RQD port mapping is commented out in `docker-compose.yml` (see Part 1, Step 1)
2. Restart docker compose: `docker compose down && docker compose up`
3. If another process is using port 8444, find it: `lsof -i :8444` (macOS/Linux) or `netstat -ano | findstr 8444` (Windows)
4. Kill the conflicting process

### Issue: CueBot Can't Lock/Control the Host

**Cause:** CueBot is configured to connect to RQD instances on a specific port (default 8444). If your RQD is on a different port, CueBot can't control it.

**Solution:**
1. Ensure your native RQD is running on port 8444 (check `RQD_GRPC_PORT` in your config)
2. Verify port: `lsof -i :8444` should show your Python RQD process
3. Restart RQD if you changed the port configuration
4. Check CueBot can reach your RQD: `cueadmin -server localhost:8443 -lh` should show your hostname

### Issue: Permission Denied on macOS

**Cause:** macOS security restrictions on monitoring input devices.

**Solution:**
Grant Terminal/iTerm accessibility permissions:
1. System Preferences -> Security & Privacy -> Privacy tab
2. Select "Accessibility" from the list
3. Add your terminal application (Terminal.app or iTerm.app)
4. Restart RQD

### Issue: NIMBY Not Working

**Cause:** NIMBY requires input monitoring which may have permission issues.

**Solution:**
1. Check the RQD config has `OVERRIDE_NIMBY = True`
2. On macOS, ensure accessibility permissions are granted (see above)
3. On Windows, ensure Python has permissions to monitor input
4. The core RQD functionality works even if NIMBY monitoring has errors

## Architecture Diagram

```
┌────────────────────────────────────────────────────────┐
│                     Your Computer                      │
│                                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Docker Containers                  │   │
│  │                                                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│  │  │PostgreSQL│  │ CueBot   │  │Linux RQD │       │   │
│  │  │:5432     │◄─┤:8443     │◄─┤:8444     │       │   │
│  │  └──────────┘  └────▲─────┘  └──────────┘       │   │
│  │                     │                           │   │
│  └─────────────────────┼───────────────────────────┘   │
│                        │                               │
│                        │ gRPC                          │
│                        │                               │
│  ┌─────────────────────▼────────────────────────┐      │
│  │     Native RQD (macOS/Windows/Linux)         │      │
│  │                 :8444                        │      │
│  └───────────────────▲──────────────────────────┘      │
│                      │                                 │
│  ┌───────────────────┴───────────────────────────┐     │
│  │            CueNIMBY                           │     │
│  │         (Monitors & Controls RQD)             │     │
│  └───────────────────────────────────────────────┘     │
│                                                        │
│  ┌───────────────────────────────────────────────┐     │
│  │     Other Tools (CueGUI, CueSubmit, etc.)     │     │
│  └───────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────┘
```

## Key Configuration Files Reference

### rqd_macos.conf / rqd_windows.conf / rqd_linux.conf
- Location: OpenCue root directory (examples provided in `sandbox/` directory)
- Purpose: Configure native RQD behavior
- Key settings:
  - `RQD_GRPC_PORT`: Port for RQD gRPC server (default: 8444, same as CueBot expects)
  - `OVERRIDE_IS_DESKTOP`: Set to True for workstation use
  - `OVERRIDE_NIMBY`: Set to True to enable NIMBY protection
  - `MINIMUM_IDLE`: Seconds of idle time before NIMBY unlocks
- Platform-specific notes:
  - **macOS**: `RQD_BECOME_JOB_USER = False` required
  - **Windows**: Set `RQD_TMPDIR` to Windows path (e.g., `C:\tmp\rqd`)
  - **Linux**: Optional `RQD_TMPDIR`, `DEFAULT_CORES`, and `DEFAULT_MEMORY` settings

### docker-compose.yml
- Location: OpenCue root directory
- Purpose: Define Docker services
- Key services:
  - `db`: PostgreSQL database
  - `cuebot`: CueBot gRPC server
  - `rqd`: Linux render node

### Environment Variables

- `CUEBOT_HOSTNAME`: CueBot server address (use `localhost` for local Docker)
- `RQD_CONFIG_FILE`: Path to RQD config file (alternative to `-c` flag)

## Stopping Services

### Stop Native RQD
Press `Ctrl+C` in the terminal where RQD is running.

### Stop Docker Services
```bash
docker compose down
```

### Stop CueNIMBY
Press `Ctrl+C` in the terminal where CueNIMBY is running, or quit from the system tray icon.

## Summary

This hybrid setup allows you to:
- Run CueBot and a Linux RQD in Docker for consistent, isolated testing
- Add your local macOS, Windows, or Linux machine as a render node
- Test CueNIMBY and other client tools against a real OpenCue deployment
- Develop and test on your local machine without affecting the Docker environment

The key insight is that RQD instances are independent render nodes that connect to the same CueBot instance, allowing you to mix containerized and native RQD instances seamlessly.
