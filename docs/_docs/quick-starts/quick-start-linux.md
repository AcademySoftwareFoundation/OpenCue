---
title: "Quick start for Linux"
nav_order: 3
parent: Quick Starts
layout: default
linkTitle: "Quick start for Linux"
date: 2023-01-13
description: >
  Try OpenCue in the sandbox environment on Linux
---

# Quick start for Linux

### Try OpenCue in the sandbox environment on Linux

---

OpenCue is an open source render management system used in visual effects and animation production. It breaks down complex rendering jobs into individual tasks, manages a queue that allocates rendering resources, and allows you to monitor jobs from your workstation.

The sandbox environment provides a quick way to test OpenCue locally using Docker containers. This setup is ideal for small tests, development work, or learning OpenCue.

**Time required:** Approximately 20 minutes

## Before you begin

Ensure you have the following software installed:

**Required software:**
- Python 3.7 or later
- pip (Python package installer)
  - On some systems, this may be `pip3`
- Python development headers:
  - **Ubuntu/Debian:** `python3-dev` package
  - **Fedora/CentOS/RHEL:** `python3-devel` package
- [Docker](https://docs.docker.com/install/) (with Docker Engine running)
- [Docker Compose v2](https://docs.docker.com/compose/install/) or later

**Get the source code:**

Choose one of these methods:

1. **Download ZIP:**
   Download and extract the [OpenCue source code](https://github.com/AcademySoftwareFoundation/OpenCue/archive/master.zip)

2. **Clone with Git:**
   ```bash
   git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
   ```

## Step-by-step installation

### Step 1: Prepare your system

1. **Add your user to the docker group** (if not already done):
   ```bash
   sudo gpasswd -a $USER docker
   ```
   Log out and back in for this change to take effect.

2. **Create mount directories for RQD:**
   ```bash
   mkdir -p /tmp/rqd/logs /tmp/rqd/shots
   ```
   These directories store rendering logs and job output.

### Step 2: Deploy the sandbox environment

The sandbox deploys three main components via Docker:
- PostgreSQL database
- Cuebot server (render farm manager)
- RQD (rendering host daemon)

1. **Navigate to the OpenCue directory:**
   ```bash
   cd OpenCue
   ```

2. **Build the Cuebot container:**
   ```bash
   docker build -t opencue/cuebot -f cuebot/Dockerfile .
   ```

3. **Start the sandbox services:**
   ```bash
   docker compose up
   ```
   
   Wait for startup to complete. You'll see output like:
   ```
   rqd-1     | WARNING   openrqd-__main__  : RQD Starting Up
   rqd-1     | WARNING   openrqd-rqcore    : RQD Started
   ```
   
   **Keep this terminal running** - it displays service logs.

### Step 3: Install OpenCue client tools

OpenCue provides several client tools:
- **PyCue:** Python API for OpenCue
- **PyOutline:** Python library for job specifications  
- **CueSubmit:** GUI for submitting rendering jobs
- **CueGUI:** GUI for monitoring and managing jobs
- **cueadmin:** Command-line administration tool
- **cueman:** Job management and batch control CLI tool
- **pycuerun:** Command-line job submission tool

**In a new terminal window:**

1. **Navigate to OpenCue directory:**
   ```bash
   cd OpenCue
   ```

2. **Create a Python virtual environment:**
   ```bash
   python3 -m venv sandbox-venv
   ```

3. **Activate the virtual environment:**
   ```bash
   source sandbox-venv/bin/activate
   ```

4. **Install client packages from source:**
   ```bash
   sandbox/install-client-sources.sh
   ```
   
   This script installs all OpenCue Python client libraries directly from the source code, including:
   - Protocol buffers package (proto/)
   - PyCue, PyOutline, cueadmin, cueman, cuesubmit, and cuegui
   
   This is the most stable installation method and works well with the main codebase.

### Step 4: Verify the installation

1. **Check connection to sandbox:**
   ```bash
   cueadmin -lh
   ```
   
   Expected output:
   ```
   Host            Load NIMBY freeMem  freeSwap freeMcp   Cores Mem   Idle             Os       Uptime   State  Locked    Alloc      Thread 
   123.456.789.0      275  False 4.1G     1.5G     154.4G    9.0   8.5G  [ 9.00 / 8.5G ]  Linux    08:08    UP     OPEN      local.general AUTO 
   ```

2. **Submit a test job:**
   
   Launch CueSubmit:
   ```bash
   cuesubmit &
   ```
   
   ![The default CueSubmit window](/assets/images/cuesubmit/cuesubmit_quick_starts.png)
   
   Enter these values:
   - **Job Name:** `HelloWorld`
   - **Shot:** `test-shot`
   - **User Name:** Use a valid username here
   - **Layer Name:** `test-layer`
   - **Command To Run:** 
     ```bash
     echo "Output from frame: #IFRAME#; layer: #LAYER#; job: #JOB#"
     ```
   - **Frame Spec:** `1-10`
   
   Click **Submit**.

3. **Monitor the job:**
   
   Launch CueGUI:
   ```bash
   cuegui &
   ```
   
   ![The default CueGUI Cuetopia window](/assets/images/cuegui_quickstart.png)
   
   - Click **Load** to see your job
   - Double-click the job to view frames
   - Check the LogView for output like:
     ```
     Output from frame: 9; layer: test_layer; job: testing-test_shot-username_helloworld
     ```

## Cleaning up

To remove the sandbox environment:

1. **Stop services:**
   ```bash
   docker compose stop
   ```

2. **Remove containers:**
   ```bash
   docker compose rm
   ```

3. **Delete database data:**
   ```bash
   rm -rf sandbox/db-data
   ```

4. **Remove Python virtual environment:**
   ```bash
   rm -rf sandbox-venv
   ```

## Next steps

- [Customize RQD for Blender rendering](/docs/other-guides/customizing-rqd)
- [Learn OpenCue concepts and terminology](/docs/concepts/)
- [Deploy production OpenCue infrastructure](/docs/getting-started/)