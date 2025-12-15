---
title: "Using the OpenCue Sandbox for Testing"
nav_order: 90
parent: "Developer Guide"
layout: default
date: 2025-08-06
description: >
  Learn how to quickly set up and use the OpenCue sandbox environment
  for local testing and development with Cuebot, RQD, CueGUI, CueSubmit, CueWeb, REST Gateway,
  CueAdmin, CueCmd, CueMan, CueNimby, PyCue, and PyOutline.
---

# Using the OpenCue Sandbox for Testing

The OpenCue sandbox provides a quick way to run the complete OpenCue stack locally for testing. This environment is ideal for developers who want to test changes, experiment with features, or learn how OpenCue works without setting up a full production environment.

## Prerequisites

Before starting, ensure you have:
- Python 3.7 or higher
- Docker and Docker Compose installed ([Get Docker](https://docs.docker.com/get-docker/))
- Git for cloning the repository

## Deployment Options

The sandbox supports two deployment modes:

| Mode | Services | Use Case |
|------|----------|----------|
| **Basic** | db, flyway, cuebot, rqd | Quick testing with desktop GUI clients |
| **Full Stack** | db, flyway, cuebot, rqd, rest-gateway, cueweb | Complete deployment including web UI |

## Basic Sandbox Setup

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

### 3. Start the Basic Sandbox

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

## Full Stack Deployment

For a complete sandbox deployment (Cuebot, DB, Flyway, RQD, REST Gateway, and CueWeb), use the full stack deployment script.

### Quick Start

The easiest way to deploy the full stack:

```bash
# From the OpenCue root directory
./sandbox/deploy_opencue_full.sh
```

This script will:
- Build all required Docker images (Cuebot, REST Gateway, CueWeb)
- Generate a JWT secret for authentication
- Start all services (db, flyway, cuebot, rqd, rest-gateway, cueweb)
- Display access URLs

### Services Deployed

The full stack deployment includes:

| Service | Port | Description |
|---------|------|-------------|
| **db** | 5432 | PostgreSQL database for storing OpenCue data |
| **flyway** | - | Database migration tool for schema management |
| **cuebot** | 8443 | The OpenCue server that manages jobs, frames, and hosts |
| **rqd** | 8444 | The render queue daemon that runs on render hosts |
| **rest-gateway** | 8448 | HTTP/REST API gateway for web access |
| **cueweb** | 3000 | Web UI for monitoring and managing OpenCue |

### Access Services

Once deployed, access the services at:

- **CueWeb UI**: [http://localhost:3000](http://localhost:3000)
- **REST Gateway**: [http://localhost:8448](http://localhost:8448)
- **Cuebot gRPC**: localhost:8443
- **PostgreSQL**: localhost:5432

**Note:** Replace `localhost` with the correct hostname or IP address if accessing from a different machine.

### Using Desktop Client Tools

The full stack deployment works with all OpenCue desktop client tools. To use them alongside CueWeb, install the client packages in a Python virtual environment:

```bash
# Create and activate virtual environment
python3 -m venv sandbox-venv
source sandbox-venv/bin/activate  # On Windows: sandbox-venv\Scripts\activate

# Install all OpenCue client packages from source
./sandbox/install-client-sources.sh
```

This installs the following tools:

| Tool | Description |
|------|-------------|
| **CueGUI** | Desktop GUI for monitoring and managing jobs, hosts, and the render farm |
| **CueSubmit** | Desktop GUI for submitting render jobs |
| **CueAdmin** | CLI tool for system administrators managing render farm infrastructure |
| **CueCmd** | CLI tool for job management operations |
| **CueMan** | Advanced CLI tool for batch job management and control |
| **CueNimby** | Tool for managing host availability (Not In My Back Yard) |
| **PyCue** | Python API library for programmatic OpenCue access |
| **PyOutline** | Python library for building job outlines programmatically |

Once installed, launch the desktop tools:

```bash
# Launch CueGUI for job monitoring
cuegui &

# Launch CueSubmit for job submission
cuesubmit &

# Use CLI tools
cueadmin -lh          # List hosts
cuecmd -h             # Show available commands
cueman -h             # Show cueman help
```

### Managing the Full Stack

```bash
# Check service status
./sandbox/deploy_opencue_full.sh status

# View logs
./sandbox/deploy_opencue_full.sh logs

# View specific service logs
./sandbox/deploy_opencue_full.sh logs cuebot
./sandbox/deploy_opencue_full.sh logs rqd
./sandbox/deploy_opencue_full.sh logs cueweb
./sandbox/deploy_opencue_full.sh logs rest-gateway

# Stop all services
./sandbox/deploy_opencue_full.sh down

# Rebuild and restart
./sandbox/deploy_opencue_full.sh build
./sandbox/deploy_opencue_full.sh up

# Clean up everything (removes volumes and images)
./sandbox/deploy_opencue_full.sh clean
```

### Manual Full Stack Deployment

If you prefer manual deployment:

```bash
# 1. Create required directories
mkdir -p /tmp/rqd/logs /tmp/rqd/shots

# 2. Generate a JWT secret
export JWT_SECRET=$(openssl rand -base64 32)

# 3. Build the images
docker build -t opencue/cuebot -f cuebot/Dockerfile .
docker build -t opencue/rest-gateway:latest -f rest_gateway/Dockerfile .
docker build -t opencue/cueweb:latest ./cueweb

# 4. Start the full stack
docker compose -f sandbox/docker-compose.full.yml up -d
```

## Testing the REST Gateway

To test the REST Gateway API, you need to generate a JWT token:

**Note:** Install `PyJWT` to generate JWT tokens:

```bash
pip install PyJWT
```

**Important:** Do not install the `jwt` package - it's a different library and won't work.

```bash
# Get the JWT secret from the running container
export JWT_SECRET=$(docker exec opencue-rest-gateway printenv JWT_SECRET)

# Generate a JWT token
export JWT_TOKEN=$(python3 -c "import jwt, datetime; payload = {'user': 'test', 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}; print(jwt.encode(payload, '$JWT_SECRET', algorithm='HS256'))")

# Test API access
curl -X POST http://localhost:8448/show.ShowInterface/GetShows \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Submit a Test Job

To verify your sandbox is working correctly:

1. In CueSubmit, create a simple test job:
   - **Job Name:** test_job
   - **Layer Type:** Shell
   - **Command:** `sleep 5`
   - **Frame Range:** 1-10

2. Click "Submit" to send the job to Cuebot

3. Monitor the job in CueGUI or CueWeb:
   - You should see your job appear in the Jobs panel
   - The frames should begin processing on the RQD host
   - Each frame will sleep for 5 seconds then complete

## Verifying the Installation

Your sandbox is working correctly if:
- Docker containers are running without errors
- CueGUI/CueWeb connects to Cuebot and shows the RQD host
- CueSubmit can submit jobs successfully
- Jobs appear in CueGUI/CueWeb and frames complete

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

# For full stack deployment
./sandbox/deploy_opencue_full.sh logs cuebot
./sandbox/deploy_opencue_full.sh logs rqd
```

## Stopping the Sandbox

### Basic Sandbox

```bash
# Stop the Docker containers
docker compose down

# Deactivate the virtual environment
deactivate
```

### Full Stack Deployment

```bash
# Stop all services
./sandbox/deploy_opencue_full.sh down

# Or clean up everything (removes volumes and images)
./sandbox/deploy_opencue_full.sh clean
```

## Troubleshooting

### Port Conflicts

If you encounter port conflicts, check these default ports:

| Service | Port |
|---------|------|
| Cuebot gRPC | 8443 |
| PostgreSQL | 5432 |
| RQD | 8444 |
| REST Gateway | 8448 |
| CueWeb | 3000 |

Ensure these ports are not in use by other applications.

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

### CueWeb Not Loading

If CueWeb is not responding:
- Check that rest-gateway is healthy: `./sandbox/deploy_opencue_full.sh status`
- Verify the JWT secret is set correctly
- Check CueWeb logs: `./sandbox/deploy_opencue_full.sh logs cueweb`

### REST Gateway Authentication Errors

If you get 401 Unauthorized errors:
- Make sure you're using `PyJWT` (not `jwt` package)
- Get the JWT secret from the running container, not from your shell
- Verify the token hasn't expired
