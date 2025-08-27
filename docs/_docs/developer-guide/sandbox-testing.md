---
title: "Using the OpenCue Sandbox for Testing"
nav_order: 57
parent: "Developer Guide"
layout: default
date: 2025-08-06
description: >
  Learn how to quickly set up and use the OpenCue sandbox environment
  for local testing and development with Cuebot, RQD, CueGUI, and CueSubmit.
---

# Using the OpenCue Sandbox for Testing

The OpenCue sandbox provides a quick way to run Cuebot, RQD, CueGUI, and CueSubmit locally for testing. This environment is ideal for developers who want to test changes, experiment with features, or learn how OpenCue works without setting up a full production environment.

## Prerequisites

Before starting, ensure you have:
- Python 3.7 or higher
- Docker and Docker Compose installed ([Get Docker](https://docs.docker.com/get-docker/))
- Git for cloning the repository

## Installation Steps

### 1. Install the OpenCue Client Packages

First, create and activate a Python virtual environment for the sandbox:

```bash
cd OpenCue
# Create a virtual environment
python3 -m venv sandbox-venv
# Activate the virtual environment
source sandbox-venv/bin/activate  # On Windows: sandbox-venv\Scripts\activate
```

### 2. Install from Source

This is recommended for developers who want to test the latest OpenCue changes:

```bash
./sandbox/install-client-sources.sh
```

This script will:
- Install all OpenCue Python packages from source
- Set up PyCue, PyOutline, CueGUI, and CueSubmit
- Configure dependencies required for local development

### 3. Start the Sandbox

You'll need to run services in multiple terminal windows:

**Terminal 1 — Start services:**

```bash
docker compose up
```

This command starts:
- PostgreSQL database
- Cuebot (the central scheduling service)
- RQD (the render host daemon)

Wait for the services to fully start. You should see log messages indicating that Cuebot and RQD are ready.

**Terminal 2 — Launch CueGUI:**

```bash
# Make sure your virtual environment is activated
source sandbox-venv/bin/activate  # On Windows: sandbox-venv\Scripts\activate
cuegui &
```

CueGUI is the graphical interface for monitoring and managing jobs, hosts, and the render farm.

**Terminal 3 — Launch CueSubmit:**

```bash
# Make sure your virtual environment is activated
source sandbox-venv/bin/activate  # On Windows: sandbox-venv\Scripts\activate
cuesubmit &
```

CueSubmit is the job submission interface where you can create and submit render jobs to the farm.

### 4. Submit a Test Job

To verify your sandbox is working correctly:

1. In CueSubmit, create a simple test job:
   - **Job Name:** test_job
   - **Layer Type:** Shell
   - **Command:** `sleep 5`
   - **Frame Range:** 1-10

2. Click "Submit" to send the job to Cuebot

3. Switch to CueGUI to monitor the job:
   - You should see your job appear in the Jobs panel
   - The frames should begin processing on the RQD host
   - Each frame will sleep for 5 seconds then complete

## Verifying the Installation

Your sandbox is working correctly if:
- Docker containers are running without errors
- CueGUI connects to Cuebot and shows the RQD host
- CueSubmit can submit jobs successfully
- Jobs appear in CueGUI and frames complete

## Common Use Cases

### Testing Code Changes

After making changes to OpenCue source code:

```bash
# Reinstall the modified packages
./sandbox/install-client-sources.sh
# Restart the affected components
```

### Debugging Issues

To see detailed logs:

```bash
# View Cuebot logs
docker compose logs -f cuebot

# View RQD logs
docker compose logs -f rqd
```

## Stopping the Sandbox

To shut down the sandbox environment:

1. Stop the Docker containers:
   ```bash
   docker compose down
   ```

2. Deactivate the virtual environment:
   ```bash
   deactivate
   ```

## Troubleshooting

### Port Conflicts

If you encounter port conflicts:
- Cuebot uses port 8443 (gRPC)
- PostgreSQL uses port 5432
- Ensure these ports are not in use by other applications

### Database Connection Issues

If Cuebot cannot connect to the database:
```bash
# Reset the database
docker compose down -v
docker compose up
```

### GUI Connection Problems

If CueGUI cannot connect to Cuebot:
- Verify Cuebot is running: `docker compose ps`
- Check the Cuebot logs for errors
- Ensure you're using the correct config file

## Additional Resources

For more detailed information about the sandbox environment, including advanced configuration options and troubleshooting, see the full [sandbox guide](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/sandbox/README.md).

For general OpenCue documentation, visit the [quick start guides](/OpenCue/docs/quick-starts/) for platform-specific instructions.