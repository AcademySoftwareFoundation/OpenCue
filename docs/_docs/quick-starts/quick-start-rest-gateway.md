---
layout: default
title: REST Gateway Quick Start
parent: Quick Starts
nav_order: 9
---

# REST Gateway Quick Start
{: .no_toc }

Get up and running with the OpenCue REST Gateway for HTTP/REST API access to your render farm.

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## Overview

The OpenCue REST Gateway provides HTTP/REST endpoints for OpenCue's gRPC API. It enables web applications, scripts, and HTTP clients to interact with your render farm without requiring gRPC clients.

### What you'll learn

- How to deploy the REST Gateway
- How to authenticate with JWT tokens
- How to make your first API calls
- Basic job and show operations

### Prerequisites

Before you begin, ensure you have:

- **OpenCue stack running** (Cuebot and PostgreSQL)
- **Docker** installed on your system
- **curl** for testing API calls
- **Python 3** (optional, for JWT token generation)

---

## Step 1: Start the OpenCue Stack

If you don't have OpenCue running yet, start it from the repository root:

```bash
# Clone OpenCue if needed
git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
cd OpenCue

# Create required directories
mkdir -p /tmp/rqd/logs /tmp/rqd/shots

# Start OpenCue stack
docker compose up -d

# Verify services are running
docker compose ps
```

Wait for the services to be healthy before proceeding.

---

## Step 2: Deploy the REST Gateway

The REST Gateway is deployed separately from the main OpenCue stack.

### Generate a JWT Secret

```bash
# Generate a secure JWT secret
export JWT_SECRET=$(openssl rand -base64 32)
echo "Your JWT_SECRET: $JWT_SECRET"
echo "Save this - you'll need it for API authentication"
```

### Build the REST Gateway Image

```bash
# From OpenCue root directory
docker build -f rest_gateway/Dockerfile -t opencue/rest-gateway:latest .
```

### Run the REST Gateway

```bash
docker run -d --name opencue-rest-gateway \
  --network opencue_default \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET="$JWT_SECRET" \
  -e REST_PORT=8448 \
  -e LOG_LEVEL=info \
  opencue/rest-gateway:latest
```

### Verify the Gateway is Running

```bash
# Test connectivity (expects 401 - this confirms the service is up)
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8448/)
if [ "$response" = "401" ]; then
    echo "REST Gateway is running (401 expected without auth)"
else
    echo "REST Gateway may not be running (got HTTP $response)"
fi
```

---

## Step 3: Generate a JWT Token

All REST Gateway endpoints require JWT authentication. Generate a token using Python:

### Using Python (Recommended)

```bash
# Install PyJWT if needed
pip install PyJWT

# Generate token
export JWT_TOKEN=$(python3 -c "
import jwt
import datetime
import os

secret = os.getenv('JWT_SECRET')
payload = {
    'user': 'quickstart',
    'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
}
print(jwt.encode(payload, secret, algorithm='HS256'))
")

echo "Your JWT_TOKEN: $JWT_TOKEN"
```

### Using Pure Bash (Alternative)

```bash
# Generate a simple test token
export JWT_TOKEN=$(python3 -c "
import base64, hmac, hashlib, json, time, os

secret = os.getenv('JWT_SECRET', 'test-secret')
header = {'alg': 'HS256', 'typ': 'JWT'}
payload = {'sub': 'quickstart', 'exp': int(time.time()) + 86400}

h = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
m = f'{h}.{p}'
s = base64.urlsafe_b64encode(hmac.new(secret.encode(), m.encode(), hashlib.sha256).digest()).decode().rstrip('=')
print(f'{m}.{s}')
")
```

---

## Step 4: Make Your First API Call

### Get All Shows

```bash
curl -X POST http://localhost:8448/show.ShowInterface/GetShows \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected response:
```json
{
  "shows": {
    "shows": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "name": "testing",
        "active": true,
        "bookingEnabled": true,
        "dispatchEnabled": true
      }
    ]
  }
}
```

### Get Jobs for a Show

```bash
curl -X POST http://localhost:8448/job.JobInterface/GetJobs \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"r": {"show": {"name": "testing"}}}'
```

### Get Available Hosts

```bash
curl -X POST http://localhost:8448/host.HostInterface/GetHosts \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Step 5: Basic Operations

### Find a Specific Show

```bash
curl -X POST http://localhost:8448/show.ShowInterface/FindShow \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "testing"}'
```

### Find a Specific Job

```bash
curl -X POST http://localhost:8448/job.JobInterface/FindJob \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "testing-job-name"}'
```

### Pause a Job

```bash
JOB_ID="your-job-id-here"

curl -X POST http://localhost:8448/job.JobInterface/Pause \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"job\": {\"id\": \"$JOB_ID\"}}"
```

### Resume a Job

```bash
curl -X POST http://localhost:8448/job.JobInterface/Resume \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"job\": {\"id\": \"$JOB_ID\"}}"
```

### Get Frames for a Job

```bash
curl -X POST http://localhost:8448/job.JobInterface/GetFrames \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"job\": {\"id\": \"$JOB_ID\"}, \"req\": {\"include_finished\": true, \"page\": 1, \"limit\": 100}}"
```

### Retry a Failed Frame

```bash
FRAME_ID="your-frame-id-here"

curl -X POST http://localhost:8448/frame.FrameInterface/Retry \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"frame\": {\"id\": \"$FRAME_ID\"}}"
```

---

## Quick Reference

### Environment Setup

```bash
# Set these variables for easier testing
export GATEWAY_URL="http://localhost:8448"
export JWT_SECRET="your-jwt-secret"
export JWT_TOKEN="your-generated-token"
```

### Common Endpoints

| Operation | Endpoint | Method |
|-----------|----------|--------|
| List shows | `show.ShowInterface/GetShows` | POST |
| Find show | `show.ShowInterface/FindShow` | POST |
| List jobs | `job.JobInterface/GetJobs` | POST |
| Find job | `job.JobInterface/FindJob` | POST |
| Pause job | `job.JobInterface/Pause` | POST |
| Resume job | `job.JobInterface/Resume` | POST |
| Kill job | `job.JobInterface/Kill` | POST |
| Get frames | `job.JobInterface/GetFrames` | POST |
| Retry frame | `frame.FrameInterface/Retry` | POST |
| Kill frame | `frame.FrameInterface/Kill` | POST |
| List hosts | `host.HostInterface/GetHosts` | POST |
| Find host | `host.HostInterface/FindHost` | POST |

### URL Pattern

All endpoints follow this pattern:
```
POST http://<gateway-host>:8448/<interface>/<method>
```

---

## Troubleshooting

### 401 Unauthorized

**Problem**: API returns 401 error

**Solutions**:
1. Verify JWT token is not expired
2. Check `JWT_SECRET` matches between token and gateway
3. Ensure `Authorization: Bearer <token>` header is correct

```bash
# Verify your secret matches
docker logs opencue-rest-gateway | grep -i jwt
```

### Connection Refused

**Problem**: Cannot connect to gateway

**Solutions**:
1. Check gateway container is running:
   ```bash
   docker ps | grep rest-gateway
   ```
2. Verify port mapping:
   ```bash
   docker port opencue-rest-gateway
   ```
3. Check gateway logs:
   ```bash
   docker logs opencue-rest-gateway
   ```

### 502 Bad Gateway

**Problem**: Gateway cannot connect to Cuebot

**Solutions**:
1. Verify Cuebot is running and healthy
2. Check `CUEBOT_ENDPOINT` environment variable
3. Ensure containers are on same network:
   ```bash
   docker network inspect opencue_default
   ```

### Empty Response

**Problem**: API returns empty data

**Solutions**:
1. Check if data exists (e.g., shows created, jobs submitted)
2. Verify filter parameters are correct
3. Try without filters first

---

## Using with Scripts

### Bash Script Example

```bash
#!/bin/bash
# list_jobs.sh - List all jobs for a show

SHOW_NAME="${1:-testing}"

curl -s -X POST http://localhost:8448/job.JobInterface/GetJobs \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"r\": {\"show\": {\"name\": \"$SHOW_NAME\"}}}" | jq '.jobs.jobs[] | {name, state, user}'
```

### Python Script Example

**Note:** `pip install requests` required to run the script below!

```python
#!/usr/bin/env python3
# list_shows.py - List all shows

import requests
import os

GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://localhost:8448')
JWT_TOKEN = os.getenv('JWT_TOKEN')

headers = {
    'Authorization': f'Bearer {JWT_TOKEN}',
    'Content-Type': 'application/json'
}

response = requests.post(
    f'{GATEWAY_URL}/show.ShowInterface/GetShows',
    headers=headers,
    json={}
)

shows = response.json().get('shows', {}).get('shows', [])
for show in shows:
    print(f"Show: {show['name']} (active: {show.get('active', False)})")
```

---

## Deploy with CueWeb

For a complete web interface, deploy CueWeb alongside the REST Gateway using the full stack deployment:

```bash
# Use the convenience script (builds all images and starts all services)
./sandbox/deploy_opencue_full.sh

# Or manually with docker compose
docker compose -f sandbox/docker-compose.full.yml up -d
```

This deploys:
- **CueWeb**: http://localhost:3000
- **REST Gateway**: http://localhost:8448
- **Cuebot**: localhost:8443
- **RQD**: localhost:8444
- **PostgreSQL**: localhost:5432

---

## Next Steps

Now that the REST Gateway is running:

1. **Explore the API**: Try different endpoints from the [REST API Reference](/docs/reference/rest-api-reference/)
2. **Build integrations**: Create scripts or applications using the API
3. **Deploy CueWeb**: Set up the web interface for browser access
4. **Production setup**: Review [Deploying REST Gateway](/docs/getting-started/deploying-rest-gateway/) for production configuration

---

## Related Documentation

- [REST API Reference](/docs/reference/rest-api-reference/) - Complete API documentation
- [REST API Tutorial](/docs/tutorials/rest-api-tutorial/) - Step-by-step tutorial
- [Deploying REST Gateway](/docs/getting-started/deploying-rest-gateway/) - Production deployment
- [Using the REST API](/docs/user-guides/using-rest-api/) - User guide
- [CueWeb Quick Start](/docs/quick-starts/quick-start-cueweb/) - Web interface setup
