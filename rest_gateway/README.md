# OpenCue REST Gateway

OpenCue REST Gateway - a production-ready HTTP/REST interface for OpenCue's gRPC API.

## Table of Contents

1. [Overview](#overview)
   - [What is the REST Gateway](#what-is-the-rest-gateway)
   - [Key Features](#key-features)
   - [Use Cases](#use-cases)
   - [Architecture](#architecture)
2. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Quick Start](#quick-start)
   - [Docker Deployment](#docker-deployment)
   - [Local Development](#local-development)
3. [Configuration](#configuration)
   - [Environment Variables](#environment-variables)
   - [Deployment Examples](#deployment-examples)
   - [Security Configuration](#security-configuration)
4. [Authentication & Authorization](#authentication--authorization)
   - [JWT Token System](#jwt-token-system)
   - [Token Requirements](#token-requirements)
   - [Creating Tokens](#creating-tokens)
   - [Token Validation](#token-validation)
5. [API Reference](#api-reference)
   - [Endpoint Structure](#endpoint-structure)
   - [Request Format](#request-format)
   - [Response Format](#response-format)
   - [Available Interfaces](#available-interfaces)
6. [Complete Endpoint Examples](#complete-endpoint-examples)
   - [Show Interface](#show-interface)
   - [Job Interface](#job-interface)
   - [Frame Interface](#frame-interface)
   - [Layer Interface](#layer-interface)
   - [Group Interface](#group-interface)
   - [Host Interface](#host-interface)
   - [Owner Interface](#owner-interface)
   - [Proc Interface](#proc-interface)
   - [Deed Interface](#deed-interface)
7. [Testing](#testing)
   - [Unit Testing](#unit-testing)
   - [Integration Testing](#integration-testing)
   - [Load Testing](#load-testing)
   - [Testing with Live Cuebot](#testing-with-live-cuebot)
8. [Development](#development)
   - [Building from Source](#building-from-source)
   - [Code Generation](#code-generation)
   - [Adding New Interfaces](#adding-new-interfaces)
   - [Contributing](#contributing)
9. [Deployment](#deployment)
   - [Production Deployment](#production-deployment)
   - [Docker Deployment](#docker-deployment-1)
   - [Kubernetes Deployment](#kubernetes-deployment)
   - [Load Balancing](#load-balancing)
10. [Monitoring & Observability](#monitoring--observability)
    - [Health Checks](#health-checks)
    - [Metrics](#metrics)
    - [Logging](#logging)
    - [Distributed Tracing](#distributed-tracing)
11. [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)
    - [Debug Mode](#debug-mode)
    - [Performance Issues](#performance-issues)
    - [Error Codes](#error-codes)
12. [Best Practices](#best-practices)
    - [Security](#security)
    - [Performance](#performance)
    - [Error Handling](#error-handling)
    - [Rate Limiting](#rate-limiting)
13. [FAQ](#faq)
14. [Appendices](#appendices)
    - [Protocol Buffer Definitions](#protocol-buffer-definitions)
    - [gRPC Service Mapping](#grpc-service-mapping)
    - [Change Log](#change-log)


## Overview

### What is the REST Gateway

The OpenCue REST Gateway is a production-ready HTTP service that provides RESTful endpoints for OpenCue's gRPC API. It acts as a translation layer, converting HTTP requests to gRPC calls and responses back to JSON, enabling web applications and HTTP clients to interact with OpenCue's rendering infrastructure.

Built with Go and the [grpc-gateway](https://github.com/grpc-ecosystem/grpc-gateway) framework, the gateway automatically generates REST endpoints from OpenCue's Protocol Buffer definitions, ensuring API consistency and reducing maintenance overhead.

### Key Features

#### **Security & Authentication**
- JWT-based authentication with HMAC SHA256 signing
- Request validation and authorization middleware
- Secure token expiration and validation
- No API keys or passwords in transit

#### **API Coverage**
- All OpenCue interfaces supported (Show, Job, Frame, Layer, Group, Host, Owner, Proc, Deed, Allocation, Facility, Filter, Action, Matcher, Depend, Subscription, Limit, Service, ServiceOverride, Task)
- Individual endpoints covering full OpenCue functionality including multi-site management, job filtering, dependencies, and resource limits
- Direct gRPC-to-REST mapping with zero data loss
- Consistent request/response patterns

#### **Production Ready**
- Docker containerization with Rocky Linux base
- Environment-based configuration
- Comprehensive error handling and logging
- All endpoints require JWT authentication for security
- Graceful shutdown and connection management

#### **Performance Optimized**
- Direct gRPC connection pooling
- Minimal overhead HTTP-to-gRPC translation
- Concurrent request handling
- Efficient memory usage and garbage collection

#### **Developer Friendly**
- Swagger compatible
- Comprehensive documentation with examples
- Unit and integration test coverage
- Easy local development setup

### Use Cases

#### **Web Application Integration**
- **CueWeb Frontend**: Powers the OpenCue web interface
- **Custom Dashboards**: Build monitoring and reporting tools
- **Mobile Applications**: Enable mobile access to OpenCue data
- **Progressive Web Apps**: Offline-capable render farm management

#### **Automation & Integration**
- **CI/CD Pipelines**: Integrate rendering into build systems
- **Python/JavaScript Scripts**: Automate render farm operations
- **Third-party Tools**: Connect external systems (Maya, Blender, etc.)
- **Workflow Management**: Integrate with production pipelines

#### **Monitoring & Operations**
- **Health Monitoring**: Track render farm status
- **Performance Analytics**: Analyze rendering metrics
- **Alerting Systems**: Monitor job failures and bottlenecks
- **Capacity Planning**: Track resource utilization

#### **Multi-language Support**
- **Any HTTP Client**: curl, wget, Postman, Insomnia
- **Programming Languages**: Python, JavaScript, Java, C#, PHP, Ruby
- **Frameworks**: React, Angular, Vue.js, Node.js, Django, Flask
- **Mobile SDKs**: iOS, Android native applications

### Architecture

```
┌─────────────────┐    HTTP/JSON    ┌──────────────────┐    gRPC    ┌─────────────┐
│   Web Client    │◄───────────────►│   REST Gateway   │◄──────────►│   Cuebot    │
│                 │                 │                  │            │             │
│ - Browser       │                 │ - Authentication │            │ - Job Mgmt  │
│ - Mobile App    │                 │ - Request Trans. │            │ - Scheduling│
│ - curl/Scripts  │                 │ - Response Form. │            │ - Resources │
│ - Third-party   │                 │ - Error Handling │            │ - Monitoring│
└─────────────────┘                 └──────────────────┘            └─────────────┘
```

#### **Request Flow**
1. **Client Request**: HTTP POST with JSON payload and JWT token
2. **Authentication**: Validate JWT token signature and expiration
3. **Request Translation**: Convert HTTP request to gRPC call
4. **gRPC Communication**: Forward request to Cuebot service
5. **Response Translation**: Convert gRPC response to JSON
6. **HTTP Response**: Return formatted JSON to client

#### **Components**
- **HTTP Server**: Handles incoming REST requests
- **JWT Middleware**: Authenticates and authorizes requests
- **gRPC Gateway**: Translates HTTP to gRPC and back
- **Connection Pool**: Manages gRPC connections to Cuebot
- **Error Handler**: Formats errors for HTTP clients

[Back to Table of Contents](#table-of-contents)

## Getting Started

### Prerequisites

Before deploying the OpenCue REST Gateway, ensure you have:

#### **System Requirements**
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 512MB RAM, recommended 1GB+
- **CPU**: 1+ cores, 2+ cores recommended for production
- **Network**: Access to Cuebot gRPC endpoint (typically port 8443)

#### **Software Dependencies**
- **Docker** (recommended): Version 20.0+ for containerized deployment
- **Go** (for development): Version 1.21+ for building from source
- **Protocol Buffers**: protoc compiler for code generation

#### **OpenCue Environment**
- **Cuebot Instance**: Running and accessible gRPC service
- **Network Connectivity**: REST Gateway must reach Cuebot endpoint
- **Authentication Secret**: Shared JWT signing key

#### **Client Requirements**
- **HTTP Client**: Any tool supporting HTTP POST requests
- **JSON Support**: For request/response payload handling
- **Authentication**: Capability to include JWT tokens in headers

### Quick Start

#### **Option 1: Docker**

The fastest way to run the REST Gateway:

```bash
# 1. Build the image from OpenCue repository root
docker build -f rest_gateway/Dockerfile -t opencue-rest-gateway:latest .

# 2. Run with your Cuebot instance
docker run -d --name opencue-rest-gateway \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=your-cuebot-host:8443 \
  -e JWT_SECRET=your-secret-key \
  -e REST_PORT=8448 \
  opencue-rest-gateway:latest

# 3. Verify it's running
curl -f http://localhost:8448/ 2>/dev/null && echo "Gateway is accessible" || echo "Gateway not responding"
```

#### **Option 2: Local Binary**

For development and testing:

```bash
# 1. Navigate to REST Gateway directory
cd rest_gateway/opencue_gateway

# 2. Build the binary
go build -o opencue_gateway main.go

# 3. Set environment variables
export CUEBOT_ENDPOINT=localhost:8443
export JWT_SECRET=dev-secret-key
export REST_PORT=8448

# 4. Run the gateway
./opencue_gateway
```

#### **Option 3: Integration with OpenCue Stack**

The REST Gateway is **not included** in OpenCue's main docker-compose.yml and must be deployed separately:

```bash
# 1. Start OpenCue stack first
docker compose up -d

# 2. Build and run REST Gateway separately
docker build -f rest_gateway/Dockerfile -t opencue-rest-gateway:latest .
docker run -d --name opencue-rest-gateway \
  --network opencue_default \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET=your-secret-key \
  opencue-rest-gateway:latest
```

### Verification

After deployment, verify the gateway is working:

#### **Service Connectivity Check**
```bash
# Test if service is responding (expects 401 Unauthorized - this confirms service is up)
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8448/)
if [ "$response" = "401" ]; then
    echo "Gateway is running and requiring authentication (as expected)"
else
    echo "Gateway may not be running (got HTTP $response)"
fi
```

#### **Authentication Test**
```bash
# Generate a test JWT token
JWT_TOKEN=$(python3 -c "
import base64, hmac, hashlib, json, time
header = {'alg': 'HS256', 'typ': 'JWT'}
payload = {'sub': 'test-user', 'exp': int(time.time()) + 3600}
h = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
m = f'{h}.{p}'
s = base64.urlsafe_b64encode(hmac.new(b'your-secret-key', m.encode(), hashlib.sha256).digest()).decode().rstrip('=')
print(f'{m}.{s}')
")

# Test endpoint with authentication
curl -X POST http://localhost:8448/show.ShowInterface/GetShows \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### **Expected Success Response**
```json
{
  "shows": {
    "shows": [{
      "id": "...",
      "name": "...",
      "showStats": {
        "pendingJobs": 0,
        "runningFrames": 0
      }
    }]
  }
}
```

### Common Quick Start Issues

#### **Connection Refused**
```bash
# Check if Cuebot is accessible
telnet your-cuebot-host 8443
# Should connect successfully
```

#### **Authentication Failure**
```bash
# Verify JWT secret matches between token and gateway
docker logs opencue-rest-gateway | grep -i "jwt\|auth"
```

#### **Port Conflicts**
```bash
# Check if port 8448 is available
netstat -tuln | grep 8448
# Change REST_PORT if needed
```

[Back to Table of Contents](#table-of-contents)

### Quick Test

First, set up environment variables for easier testing:

```bash
# Set up environment variables
# IMPORTANT: Use the secret that matches your REST Gateway's JWT_SECRET

# For Docker Compose setup (production-secret-key):
export JWT_TOKEN=$(python3 -c "
import base64, hmac, hashlib, json, time
header = {'alg': 'HS256', 'typ': 'JWT'}
payload = {'sub': 'user', 'exp': int(time.time()) + 3600}
h = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
m = f'{h}.{p}'
s = base64.urlsafe_b64encode(hmac.new(b'production-secret-key', m.encode(), hashlib.sha256).digest()).decode().rstrip('=')
print(f'{m}.{s}')
")

# For default/development setup (default-secret-key):
# export JWT_TOKEN=$(python3 -c "
# import base64, hmac, hashlib, json, time
# header = {'alg': 'HS256', 'typ': 'JWT'}
# payload = {'sub': 'user', 'exp': int(time.time()) + 3600}
# h = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
# p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
# m = f'{h}.{p}'
# s = base64.urlsafe_b64encode(hmac.new(b'default-secret-key', m.encode(), hashlib.sha256).digest()).decode().rstrip('=')
# print(f'{m}.{s}')
# ")

export OPENCUE_REST_GATEWAY_URL=http://localhost:8448
```

**Important Notes:**
- **All endpoints require JWT authentication** - there are no public health endpoints
- The secret key must exactly match your REST Gateway's `JWT_SECRET` environment variable
- Check your container configuration: `docker inspect opencue-rest-gateway-live | grep JWT_SECRET`

## Endpoint Examples

Below are examples for all available REST endpoints. Each example uses the environment variables set above.

### Show Interface

**Get all shows:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/show.ShowInterface/GetShows \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

*Response:*
```json
{
  "shows": {
    "shows": [{
      "id": "00000000-0000-0000-0000-000000000000",
      "name": "testing",
      "defaultMinCores": 1,
      "defaultMaxCores": 2000,
      "commentEmail": "",
      "bookingEnabled": true,
      "dispatchEnabled": true,
      "active": true,
      "showStats": {
        "runningFrames": 0,
        "deadFrames": 0,
        "pendingFrames": 6,
        "pendingJobs": 1,
        "createdJobCount": "44",
        "createdFrameCount": "499",
        "renderedFrameCount": "392",
        "failedFrameCount": "164",
        "reservedCores": 0,
        "reservedGpus": 0
      },
      "defaultMinGpus": 100,
      "defaultMaxGpus": 100000
    }]
  }
}
```

**Find a specific show:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/show.ShowInterface/FindShow \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "testing"}'
```

*Response:*
```json
{
  "show": {
    "id": "00000000-0000-0000-0000-000000000000",
    "name": "testing",
    "defaultMinCores": 1,
    "defaultMaxCores": 2000,
    "commentEmail": "",
    "bookingEnabled": true,
    "dispatchEnabled": true,
    "active": true,
    "showStats": {
      "runningFrames": 0,
      "pendingFrames": 6,
      "pendingJobs": 1
    }
  }
}
```

### Job Interface

**Get jobs for a show:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/job.JobInterface/GetJobs \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"r": {"show": {"name": "testing"}}}'
```

*Response:*
```json
{
  "jobs": {
    "jobs": [{
      "id": "00000000-0000-0000-0000-000000000001",
      "name": "testing-job-001",
      "shot": "shot001",
      "show": "testing",
      "user": "artist1",
      "group": "default",
      "facility": "cloud",
      "os": "linux",
      "priority": 100,
      "minCores": 1,
      "maxCores": 10,
      "logDir": "/shots/testing/shot001/logs",
      "isPaused": false,
      "hasComment": false,
      "autoEat": false,
      "startTime": 1694000000,
      "stopTime": 0,
      "jobStats": {
        "runningFrames": 0,
        "deadFrames": 0,
        "eatenFrames": 0,
        "pendingFrames": 6,
        "succeededFrames": 0,
        "totalFrames": 6
      }
    }]
  }
}
```

**Find a specific job:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/job.JobInterface/FindJob \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "job-name"}'
```

*Response:*
```json
{
  "job": {
    "id": "00000000-0000-0000-0000-000000000001",
    "name": "testing-job-001",
    "state": "PENDING",
    "shot": "shot001",
    "show": "testing",
    "user": "artist1",
    "priority": 100,
    "minCores": 1,
    "maxCores": 10,
    "isPaused": false
  }
}
```

**Get frames for a job:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/job.JobInterface/GetFrames \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job": {"id": "job-id"}, "req": {"include_finished": true, "page": 1, "limit": 100}}'
```

*Response:*
```json
{
  "frames": {
    "frames": [{
      "id": "00000000-0000-0000-0000-000000000002",
      "name": "0001-layer_name",
      "layerName": "layer_name",
      "number": 1,
      "state": "WAITING",
      "retryCount": 0,
      "exitStatus": -1,
      "dispatchOrder": 0,
      "startTime": 0,
      "stopTime": 0,
      "maxRss": "0",
      "usedMemory": "0",
      "reservedMemory": "0",
      "lastResource": "/0.00/0",
      "checkpointState": "DISABLED",
      "checkpointCount": 0,
      "totalCoreTime": 0,
      "lluTime": 1694000000
    }]
  }
}
```

**Kill a job:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/job.JobInterface/Kill \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job": {"id": "job-id"}}'
```

*Response:*
```json
{}
```

**Pause a job:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/job.JobInterface/Pause \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job": {"id": "job-id"}}'
```

*Response:*
```json
{}
```

**Resume a job:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/job.JobInterface/Resume \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job": {"id": "job-id"}}'
```

*Response:*
```json
{}
```

### Frame Interface

**Get a specific frame:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/frame.FrameInterface/GetFrame \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": "frame-id"}'
```

*Response:*
```json
{
  "frame": {
    "id": "00000000-0000-0000-0000-000000000002",
    "name": "0001-layer_name",
    "layerName": "layer_name",
    "number": 1,
    "state": "WAITING",
    "retryCount": 0,
    "exitStatus": -1,
    "dispatchOrder": 0,
    "startTime": 0,
    "stopTime": 0,
    "maxRss": "0",
    "usedMemory": "0",
    "reservedMemory": "0",
    "lastResource": "/0.00/0",
    "checkpointState": "DISABLED",
    "totalCoreTime": 0
  }
}
```

**Retry a frame:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/frame.FrameInterface/Retry \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"frame": {"id": "frame-id"}}'
```

*Response:*
```json
{}
```

**Kill a frame:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/frame.FrameInterface/Kill \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"frame": {"id": "frame-id"}}'
```

*Response:*
```json
{}
```

**Eat a frame:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/frame.FrameInterface/Eat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"frame": {"id": "frame-id"}}'
```

*Response:*
```json
{}
```

### Layer Interface

**Get a layer:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/layer.LayerInterface/GetLayer \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": "layer-id"}'
```

*Response:*
```json
{
  "layer": {
    "id": "00000000-0000-0000-0000-000000000003",
    "name": "layer_name",
    "type": "Render",
    "isEnabled": true,
    "minimumCores": 1,
    "maximumCores": 10,
    "minimumMemory": 2147483648,
    "minimumGpus": 0,
    "maximumGpus": 0,
    "layerStats": {
      "totalFrames": 6,
      "runningFrames": 0,
      "deadFrames": 0,
      "pendingFrames": 6,
      "succeededFrames": 0
    }
  }
}
```

**Find a layer:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/layer.LayerInterface/FindLayer \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job": {"id": "job-id"}, "layer": "layer-name"}'
```

*Response:*
```json
{
  "layer": {
    "id": "00000000-0000-0000-0000-000000000003",
    "name": "layer_name",
    "type": "Render",
    "isEnabled": true,
    "minimumCores": 1,
    "maximumCores": 10
  }
}
```

**Get frames for a layer:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/layer.LayerInterface/GetFrames \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"layer": {"id": "layer-id"}, "req": {"page": 1, "limit": 100}}'
```

*Response:*
```json
{
  "frames": {
    "frames": [{
      "id": "00000000-0000-0000-0000-000000000002",
      "name": "0001-layer_name",
      "layerName": "layer_name",
      "number": 1,
      "state": "WAITING"
    }]
  }
}
```

**Kill frames in a layer:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/layer.LayerInterface/Kill \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"layer": {"id": "layer-id"}}'
```

*Response:*
```json
{}
```

### Group Interface

**Find a group:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/group.GroupInterface/FindGroup \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"show": {"name": "testing"}, "name": "group-name"}'
```

*Response:*
```json
{
  "group": {
    "id": "00000000-0000-0000-0000-000000000004",
    "name": "default",
    "department": "lighting",
    "defaultJobPriority": 100
  }
}
```

**Get a group:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/group.GroupInterface/GetGroup \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": "group-id"}'
```

*Response:*
```json
{
  "group": {
    "id": "00000000-0000-0000-0000-000000000004",
    "name": "default",
    "department": "lighting",
    "defaultJobPriority": 100,
    "defaultJobMinCores": 1,
    "defaultJobMaxCores": 10,
    "parentId": "",
    "groupStats": {
      "runningFrames": 0,
      "deadFrames": 0,
      "pendingFrames": 6,
      "pendingJobs": 1
    }
  }
}
```

**Set minimum cores for a group:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/group.GroupInterface/SetMinCores \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"group": {"id": "group-id"}, "cores": 10}'
```

*Response:*
```json
{}
```

**Set maximum cores for a group:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/group.GroupInterface/SetMaxCores \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"group": {"id": "group-id"}, "cores": 100}'
```

*Response:*
```json
{}
```

### Host Interface

**Get all hosts:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/host.HostInterface/GetHosts \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

*Response:*
```json
{
  "hosts": {
    "hosts": [{
      "id": "00000000-0000-0000-0000-000000000005",
      "name": "render-host-001",
      "lockState": "OPEN",
      "bootTime": 1694000000,
      "pingTime": 1694001000,
      "os": "linux",
      "totalCores": 16,
      "idleCores": 16,
      "totalMemory": 68719476736,
      "freeMemory": 34359738368,
      "totalGpus": 1,
      "freeGpus": 1,
      "totalGpuMemory": 8589934592,
      "freeGpuMemory": 8589934592,
      "hostStats": {
        "totalFrames": 0,
        "runningFrames": 0
      }
    }]
  }
}
```

**Find a specific host:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/host.HostInterface/FindHost \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "hostname"}'
```

*Response:*
```json
{
  "host": {
    "id": "00000000-0000-0000-0000-000000000005",
    "name": "render-host-001",
    "lockState": "OPEN",
    "bootTime": 1694000000,
    "pingTime": 1694001000,
    "os": "linux",
    "totalCores": 16,
    "idleCores": 16,
    "totalMemory": 68719476736,
    "freeMemory": 34359738368
  }
}
```

**Get a host by ID:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/host.HostInterface/GetHost \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": "host-id"}'
```

*Response:*
```json
{
  "host": {
    "id": "00000000-0000-0000-0000-000000000005",
    "name": "render-host-001",
    "lockState": "OPEN",
    "totalCores": 16,
    "idleCores": 16
  }
}
```

**Lock a host:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/host.HostInterface/Lock \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"host": {"id": "host-id"}}'
```

*Response:*
```json
{}
```

**Unlock a host:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/host.HostInterface/Unlock \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"host": {"id": "host-id"}}'
```

*Response:*
```json
{}
```

### Owner Interface

**Get an owner:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/owner.OwnerInterface/GetOwner \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "owner-name"}'
```

*Response:*
```json
{
  "owner": {
    "name": "artist1",
    "maxCores": 50,
    "minCores": 1,
    "maxGpus": 2,
    "minGpus": 0,
    "ownerStats": {
      "runningFrames": 0,
      "maxFrames": 100
    }
  }
}
```

**Set maximum cores for an owner:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/owner.OwnerInterface/SetMaxCores \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"owner": {"name": "owner-name"}, "cores": 50}'
```

*Response:*
```json
{}
```

**Take ownership of a host:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/owner.OwnerInterface/TakeOwnership \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"host": {"id": "host-id"}, "owner": {"name": "owner-name"}}'
```

*Response:*
```json
{}
```

### Proc Interface

**Get a process:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/proc.ProcInterface/GetProc \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": "proc-id"}'
```

*Response:*
```json
{
  "proc": {
    "id": "00000000-0000-0000-0000-000000000006",
    "name": "proc-001",
    "logPath": "/tmp/rqd/logs/proc-001.log",
    "unbooked": false,
    "reserved": true,
    "bookedCores": 4,
    "virtualMemory": 8589934592,
    "usedMemory": 2147483648,
    "bookedGpus": 0,
    "usedGpuMemory": 0
  }
}
```

**Kill a process:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/proc.ProcInterface/Kill \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"proc": {"id": "proc-id"}}'
```

*Response:*
```json
{}
```

**Unbook a process:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/proc.ProcInterface/Unbook \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"proc": {"id": "proc-id"}}'
```

*Response:*
```json
{}
```

### Deed Interface

**Get deed owner:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/deed.DeedInterface/GetOwner \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"deed": {"id": "deed-id"}}'
```

*Response:*
```json
{
  "owner": {
    "name": "artist1",
    "maxCores": 50,
    "minCores": 1
  }
}
```

**Get deed host:**
```bash
curl -X POST $OPENCUE_REST_GATEWAY_URL/deed.DeedInterface/GetHost \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"deed": {"id": "deed-id"}}'
```

*Response:*
```json
{
  "host": {
    "id": "00000000-0000-0000-0000-000000000005",
    "name": "render-host-001",
    "lockState": "OPEN",
    "totalCores": 16,
    "idleCores": 12
  }
}
```

### Common Error Responses

**Success Response (for Kill/Pause/Resume operations):**
```json
{}
```

**Error Response:**
```json
{
  "error": "rpc error: code = NotFound desc = Job not found",
  "code": 5,
  "message": "Job not found"
}
```

[Back to Contents](#contents)

## Available Interfaces

The REST Gateway exposes all major OpenCue interfaces:

### Core Interfaces

| Interface | Endpoints | Description |
|-----------|-----------|-------------|
| **ShowInterface** | `FindShow`, `GetShows`, `CreateShow` | Show/project management |
| **JobInterface** | `FindJob`, `GetJobs`, `GetComments`, `Kill`, `Pause`, `Resume` | Job lifecycle management |
| **FrameInterface** | `GetFrame`, `Retry`, `Kill`, `Eat` | Frame-level operations |
| **LayerInterface** | `GetLayer`, `FindLayer`, `GetFrames`, `Kill` | Layer management |
| **GroupInterface** | `FindGroup`, `GetGroup`, `SetMinCores`, `SetMaxCores` | Resource group management |
| **HostInterface** | `FindHost`, `GetHost`, `GetComments`, `Lock`, `Unlock`, `AddTags`, `RemoveTags` | Host/machine management |
| **OwnerInterface** | `GetOwner`, `SetMaxCores`, `TakeOwnership` | Resource ownership |
| **ProcInterface** | `GetProc`, `Kill`, `Unbook` | Process management |
| **DeedInterface** | `GetOwner`, `GetHost` | Resource deed management |

### Management Interfaces

| Interface | Endpoints | Description |
|-----------|-----------|-------------|
| **AllocationInterface** | `GetAll`, `Get`, `Find`, `GetHosts`, `SetBillable` | Resource allocation across facilities |
| **FacilityInterface** | `Get`, `Create`, `Delete`, `GetAllocations` | Multi-site render farm facilities |
| **FilterInterface** | `FindFilter`, `GetActions`, `GetMatchers`, `SetEnabled`, `Delete` | Job filtering and routing |
| **ActionInterface** | `Delete`, `Commit`, `GetParentFilter` | Filter action management |
| **MatcherInterface** | `Delete`, `Commit`, `GetParentFilter` | Filter matcher management |
| **DependInterface** | `GetDepend`, `Satisfy`, `Unsatisfy` | Job and frame dependencies |
| **SubscriptionInterface** | `Get`, `Find`, `Delete`, `SetSize`, `SetBurst` | Show subscription to allocations |
| **LimitInterface** | `GetAll`, `Get`, `Find`, `Create`, `Delete`, `SetMaxValue` | Resource limits (licenses, etc.) |
| **ServiceInterface** | `GetService`, `GetDefaultServices`, `CreateService`, `Update`, `Delete` | Service definitions |
| **ServiceOverrideInterface** | `Update`, `Delete` | Show-specific service overrides |
| **TaskInterface** | `Delete`, `SetMinCores`, `ClearAdjustments` | Task and priority management |

All endpoints follow the pattern: `POST /{interface}/{method}`

[Back to Contents](#contents)


## How Does It Work

The Opencue Rest Gateway operates as a translator and secure access point between the RESTful world and the gRPC services provided by Opencue. Built on top of Go and the [grpc-gateway project](https://github.com/grpc-ecosystem/grpc-gateway), the gateway automatically converts Opencue's protocol buffer (proto) definitions into REST endpoints.

Here’s a step-by-step breakdown of how it works:

1. **Request Conversion**: When a client sends an HTTP request to the gateway, the request is matched against the predefined RESTful routes generated from the proto files. The gateway then converts this HTTP request into the corresponding gRPC call.

2. **gRPC Communication**: The converted request is sent to the appropriate Opencue gRPC service, where it is processed just like any other gRPC request.

3. **Response Handling**: After the gRPC service processes the request, the response is returned to the gateway, which then converts the gRPC response into a JSON format suitable for HTTP.

4. **Security Enforcement**: Before any request is processed, the gateway enforces security by requiring a JSON Web Token (JWT) in the `Authorization header`. This token is validated to ensure that the request is authenticated and authorized to access the requested resources.

5. **Final Response**: The formatted JSON response is sent back to the client via HTTP, completing the request-response cycle.

This seamless conversion and security process allows the Opencue Rest Gateway to provide a robust, secure, and user-friendly interface to Opencue's gRPC services, making it accessible to a wide range of clients and applications.

**Note:** In the examples below, the REST gateway is running on `http://localhost:8448`. Replace this with your actual gateway URL if running elsewhere.

[Back to Contents](#contents)

## Configuration

The OpenCue REST Gateway is configured entirely through environment variables, making it suitable for containerized deployments and different environments.

### Environment Variables

#### **Required Configuration**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CUEBOT_ENDPOINT` | Yes | `localhost:8443` | Cuebot gRPC server address (host:port) |
| `REST_PORT` | Yes | `8448` | HTTP port for REST Gateway server |
| `JWT_SECRET` | Yes | `default-secret-key` | Secret key for JWT token validation |

#### **Optional Configuration**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `info` | Logging level (debug, info, warn, error) |
| `GRPC_TIMEOUT` | No | `30s` | Timeout for gRPC calls to Cuebot |
| `HTTP_TIMEOUT` | No | `60s` | HTTP request timeout |
| `MAX_CONCURRENT_STREAMS` | No | `100` | Maximum concurrent gRPC streams |
| `KEEPALIVE_TIME` | No | `30s` | gRPC keepalive time |
| `KEEPALIVE_TIMEOUT` | No | `5s` | gRPC keepalive timeout |

#### **Security Configuration**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TLS_CERT_FILE` | No | - | Path to TLS certificate file |
| `TLS_KEY_FILE` | No | - | Path to TLS private key file |
| `CORS_ORIGINS` | No | `*` | Allowed CORS origins (comma-separated) |
| `CORS_HEADERS` | No | `*` | Allowed CORS headers (comma-separated) |
| `RATE_LIMIT_RPS` | No | `100` | Rate limit requests per second |

### Deployment Examples

#### **Standalone Docker Deployment**
**Note:** The REST Gateway is not included in OpenCue's main docker-compose.yml and must be deployed separately.

```bash
# Build the image
docker build -f rest_gateway/Dockerfile -t opencue-rest-gateway:latest .

# Run as standalone container
docker run -d --name opencue-rest-gateway \
  --network opencue_default \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET=${JWT_SECRET} \
  -e REST_PORT=8448 \
  -e LOG_LEVEL=info \
  -e GRPC_TIMEOUT=30s \
  -e CORS_ORIGINS=https://cueweb.example.com,https://dashboard.example.com \
  -e RATE_LIMIT_RPS=200 \
  --restart unless-stopped \
  opencue-rest-gateway:latest
```

#### **Custom Docker Compose (Separate File)**
If you prefer using Docker Compose, create a separate `rest-gateway-compose.yml`:

```yaml
version: '3.8'
services:
  rest-gateway:
    image: opencue-rest-gateway:latest
    ports:
      - "8448:8448"
    environment:
      - CUEBOT_ENDPOINT=cuebot:8443
      - JWT_SECRET=${JWT_SECRET}
      - REST_PORT=8448
      - LOG_LEVEL=info
      - GRPC_TIMEOUT=30s
      - CORS_ORIGINS=https://cueweb.example.com,https://dashboard.example.com
      - RATE_LIMIT_RPS=200
    networks:
      - opencue_default
    restart: unless-stopped

networks:
  opencue_default:
    external: true
```

```bash
# Deploy with separate compose file
docker compose -f rest-gateway-compose.yml up -d
```

#### **Kubernetes Deployment**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opencue-rest-gateway
  labels:
    app: opencue-rest-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: opencue-rest-gateway
  template:
    metadata:
      labels:
        app: opencue-rest-gateway
    spec:
      containers:
      - name: gateway
        image: opencue-rest-gateway:latest
        ports:
        - containerPort: 8448
        env:
        - name: CUEBOT_ENDPOINT
          value: "opencue-cuebot:8443"
        - name: REST_PORT
          value: "8448"
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: opencue-secrets
              key: jwt-secret
        - name: LOG_LEVEL
          value: "info"
        - name: CORS_ORIGINS
          value: "https://cueweb.production.com"
        
        # Resource management
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        
        # Health checks (using TCP check since all HTTP endpoints require authentication)
        livenessProbe:
          tcpSocket:
            port: 8448
          initialDelaySeconds: 30
          periodSeconds: 10
        
        readinessProbe:
          tcpSocket:
            port: 8448
          initialDelaySeconds: 5
          periodSeconds: 5
        
        # Security
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
---
apiVersion: v1
kind: Service
metadata:
  name: opencue-rest-gateway
spec:
  selector:
    app: opencue-rest-gateway
  ports:
  - port: 8448
    targetPort: 8448
  type: ClusterIP
```

#### **Docker Swarm**
```yaml
version: '3.8'
services:
  rest-gateway:
    image: opencue-rest-gateway:latest
    ports:
      - "8448:8448"
    environment:
      - CUEBOT_ENDPOINT=opencue-cuebot:8443
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
      - REST_PORT=8448
      - LOG_LEVEL=info
    
    secrets:
      - jwt_secret
    
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    
    networks:
      - opencue

secrets:
  jwt_secret:
    external: true

networks:
  opencue:
    external: true
```

### Security Configuration

#### **JWT Token Security**
```bash
# Generate a strong JWT secret
JWT_SECRET=$(openssl rand -base64 32)
echo "Generated JWT secret: $JWT_SECRET"

# Store securely
echo "$JWT_SECRET" | docker secret create jwt_secret -
```

#### **TLS/HTTPS Configuration**
```bash
# Generate self-signed certificate for development
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Set environment variables
export TLS_CERT_FILE=/path/to/cert.pem
export TLS_KEY_FILE=/path/to/key.pem
```

#### **CORS Configuration**
```bash
# Production CORS setup
export CORS_ORIGINS="https://cueweb.company.com,https://dashboard.company.com"
export CORS_HEADERS="Authorization,Content-Type,X-Requested-With"
```

### Configuration Validation

#### **Startup Validation**
The gateway validates configuration on startup:

```bash
# Check configuration
docker logs opencue-rest-gateway 2>&1 | grep -E "(config|error|warning)"
```

#### **Runtime Configuration Check**
```bash
# Get current configuration
curl -s http://localhost:8448/config | jq '.'
```

### Environment-Specific Examples

#### **Development**
```bash
export CUEBOT_ENDPOINT=localhost:8443
export JWT_SECRET=dev-secret-key-not-for-production
export REST_PORT=8448
export LOG_LEVEL=debug
export CORS_ORIGINS=*
```

#### **Staging**
```bash
export CUEBOT_ENDPOINT=cuebot-staging:8443
export JWT_SECRET=$(cat /etc/secrets/jwt-secret)
export REST_PORT=8448
export LOG_LEVEL=info
export CORS_ORIGINS=https://staging.cueweb.company.com
export RATE_LIMIT_RPS=50
```

#### **Production**
```bash
export CUEBOT_ENDPOINT=cuebot-prod:8443
export JWT_SECRET=$(cat /run/secrets/jwt_secret)
export REST_PORT=8448
export LOG_LEVEL=warn
export CORS_ORIGINS=https://cueweb.company.com
export RATE_LIMIT_RPS=500
export GRPC_TIMEOUT=60s
export TLS_CERT_FILE=/etc/ssl/certs/gateway.crt
export TLS_KEY_FILE=/etc/ssl/private/gateway.key
```

[Back to Table of Contents](#table-of-contents)

## REST Interface

### Endpoint Structure

All service RPC calls are accessible via the REST interface:

 * **HTTP method:** POST
 * **URI path:** Built from the service's name and method: `/<fully qualified service name>/<method name>` (e.g., `/show.ShowInterface/FindShow`)
 * **Authorization header:** Must include a JWT token as the bearer.
    ```json
    headers: {
            "Authorization": `Bearer ${jwtToken}`,
        },
    ```
 * **HTTP body:** A JSON object with the request data.
    ```proto
        message ShowFindShowRequest {
            string name = 1;
        }
    ``` 
    Becomes:
    ```json
    {
        "name": "value for name"
    }
    ```
 * **HTTP response:** A JSON object with the formatted response.

Go back to [Contents](#contents).


### Example: Getting a show

Given the following proto definition in `show.proto`:

```proto
service ShowInterface {
    // Find a show with the specified name.
    rpc FindShow(ShowFindShowRequest) returns (ShowFindShowResponse);
}

message ShowFindShowRequest {
    string name = 1;
}
message ShowFindShowResponse {
    Show show = 1;
}
message Show {
    string id = 1;
    string name = 2;
    float default_min_cores = 3;
    float default_max_cores = 4;
    string comment_email = 5;
    bool booking_enabled = 6;
    bool dispatch_enabled = 7;
    bool active = 8;
    ShowStats show_stats = 9;
    float default_min_gpus = 10;
    float default_max_gpus = 11;
}
```

You can send a request to the REST gateway:

```bash
curl -i -H "Authorization: Bearer $JWT_TOKEN" -X POST $OPENCUE_REST_GATEWAY_URL/show.ShowInterface/FindShow -d '{"name": "testing"}'
```

The response might look like this:

```bash
HTTP/1.1 200 OK
Content-Type: application/json
Grpc-Metadata-Content-Type: application/grpc
Grpc-Metadata-Grpc-Accept-Encoding: gzip
Date: Tue, 16 Sep 2025 00:47:28 GMT
Content-Length: 453

{"show":{"id":"00000000-0000-0000-0000-000000000000","name":"testing","defaultMinCores":1,"defaultMaxCores":2000,"commentEmail":"","bookingEnabled":true,"dispatchEnabled":true,"active":true,"showStats":{"runningFrames":0,"deadFrames":0,"pendingFrames":6,"pendingJobs":1,"createdJobCount":"44","createdFrameCount":"499","renderedFrameCount":"392","failedFrameCount":"164","reservedCores":0,"reservedGpus":0},"defaultMinGpus":100,"defaultMaxGpus":100000}}
```

Go back to [Contents](#contents).


### Example: Getting frames for a job

Given the following proto definition in `job.proto`:

```proto
service JobInterface {
    // Returns all frame objects that match FrameSearchCriteria
    rpc GetFrames(JobGetFramesRequest) returns (JobGetFramesResponse);
}

message JobGetFramesRequest {
    Job job = 1;
    FrameSearchCriteria req = 2;
}

message Job {
    string id = 1;
    JobState state = 2;
    string name = 3;
    string shot = 4;
    string show = 5;
    string user = 6;
    string group = 7;
    string facility = 8;
    string os = 9;
    oneof uid_optional {
        int32 uid = 10;
    }
    int32 priority = 11;
    float min_cores = 12;
    float max_cores = 13;
    string log_dir = 14;
    bool is_paused = 15;
    bool has_comment = 16;
    bool auto_eat = 17;
    int32 start_time = 18;
    int32 stop_time = 19;
    JobStats job_stats = 20;
    float min_gpus = 21;
    float max_gpus = 22;
}

// Object for frame searching
message FrameSearchCriteria {
    repeated string ids = 1;
    repeated string frames = 2;
    repeated string layers = 3;
    FrameStateSeq states = 4;
    string frame_range = 5;
    string memory_range = 6;
    string duration_range = 7;
    int32 page = 8;
    int32 limit = 9;
    int32 change_date = 10;
    int32 max_results = 11;
    int32 offset = 12;
    bool include_finished = 13;
}

message JobGetFramesResponse {
    FrameSeq frames = 1;
}

// A sequence of Frames
message FrameSeq {
    repeated Frame frames = 1;
}
```

You can send a request to the REST gateway:

**Note:** It is important to include 'page' and 'limit' when getting frames for a job.

```bash
curl -i -H "Authorization: Bearer $JWT_TOKEN" -X POST $OPENCUE_REST_GATEWAY_URL/job.JobInterface/GetFrames -d '{"job":{"id":"00000000-0000-0000-0000-000000000001"}, "req": {"include_finished":true,"page":1,"limit":100}}'
```

The response might look like this:

```bash
HTTP/1.1 200 OK
content-type: application/json
grpc-metadata-content-type: application/grpc
grpc-metadata-grpc-accept-encoding: gzip
date: Tue, 13 Feb 2024 17:15:49 GMT
transfer-encoding: chunked
set-cookie: 01234567890123456789012345678901234567890123456789012345678901234; path=/; HttpOnly


{"frames":{"frames":[{"id":"00000000-0000-0000-0000-000000000002", "name":"0001-bty_tp_3d_123456", "layerName":"bty_tp_3d_123456", "number":1, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":0, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"00000000-0000-0000-0000-000000000003", "name":"0002-bty_tp_3d_123456", "layerName":"bty_tp_3d_123456", "number":2, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":1, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"00000000-0000-0000-0000-000000000004", "name":"0003-bty_tp_3d_083540", "layerName":"bty_tp_3d_123456", "number":3, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":2, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"00000000-0000-0000-0000-000000000005", "name":"0004-bty_tp_3d_083540", "layerName":"bty_tp_3d_123456", "number":4, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":3, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"00000000-0000-0000-0000-000000000006", "name":"0005-bty_tp_3d_083540", "layerName":"bty_tp_3d_123456", "number":5, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":4, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}]}}
```

Go back to [Contents](#contents).


## Authentication

The REST Gateway uses JSON Web Tokens (JWT) for secure authentication. All endpoints require a valid JWT token in the Authorization header.

### JWT Token Requirements

- **Algorithm**: HMAC SHA256 (HS256)
- **Header**: `Authorization: Bearer <token>`
- **Expiration**: Tokens must include an `exp` claim
- **Secret**: Must match the `JWT_SECRET` environment variable

### Creating JWT Tokens

**Python Example:**
```python
import base64
import hmac
import hashlib
import json
import time

def create_jwt_token(secret, user_id, expiry_hours=1):
    # Header
    header = {
        "alg": "HS256",
        "typ": "JWT"
    }
    
    # Payload
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + (expiry_hours * 3600)
    }
    
    # Encode
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header).encode()
    ).decode().rstrip('=')
    
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip('=')
    
    # Sign
    message = f"{header_b64}.{payload_b64}"
    signature = base64.urlsafe_b64encode(
        hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
    ).decode().rstrip('=')
    
    return f"{message}.{signature}"

# Usage
token = create_jwt_token("your-secret-key", "user123")
```

**JavaScript Example:**
```javascript
const crypto = require('crypto');

function createJWTToken(secret, userId, expiryHours = 1) {
    const header = {
        alg: 'HS256',
        typ: 'JWT'
    };
    
    const payload = {
        sub: userId,
        exp: Math.floor(Date.now() / 1000) + (expiryHours * 3600)
    };
    
    const headerB64 = Buffer.from(JSON.stringify(header))
        .toString('base64')
        .replace(/=/g, '');
    
    const payloadB64 = Buffer.from(JSON.stringify(payload))
        .toString('base64')
        .replace(/=/g, '');
    
    const message = `${headerB64}.${payloadB64}`;
    const signature = crypto
        .createHmac('sha256', secret)
        .update(message)
        .digest('base64')
        .replace(/=/g, '');
    
    return `${message}.${signature}`;
}

// Usage
const token = createJWTToken('your-secret-key', 'user123');
```

[Back to Contents](#contents)


### What are JSON Web Tokens?

The gRPC REST gateway implements JSON Web Tokens (JWT) for authentication. JWTs are a compact, URL-safe means of representing claims to be transferred between two parties. The claims in a JWT are encoded as a JSON object and are digitally signed for verification and security. In the gRPC REST gateway, all JWTs are signed using a secret. A JWT consists of the following three parts separated by dots:

1. **Header:** Contains the type of token (usually `JWT`) and the signing algorithm (like `SHA256`)

- Example:

```json
{
    "alg": "HS256",
    "typ": "JWT"
}
```

2. **Payload:** Contains the claims, which are statements about an entity (user) and additional data.

- Example:

```json
{
    "sub": "user-id-123",
    "role": "admin",
    "iat": 1609459200,  // Example timestamp (Jan 1, 2021)
    "exp": 1609462800   // Example expiration (1 hour later)
}

```
3. **Signature:** Created from the encoded header, the encoded payload, a secret, the algorithm specified in the header, and signed.

- The signature also verifies that the original message was not altered and can verify that the sender of the JWT is who they say they are (when signed with a private key).

- Example:

```
HMACSHA256(
    base64UrlEncode(header) + "." +
    base64UrlEncode(payload),
    secret
)
```
Together, these three parts form a token like `xxxxx.yyyyy.zzzzz`, which is three Base64-URL strings separated by dots that can be passed in HTML environments.

Go back to [Contents](#contents).


### JSON Web Tokens in a web system and the Rest Gateway

In a web system and Rest Gateway, the secret for the JWT must be defined and match. In Rest Gateway, the secret is defined as an environment variable called `JWT_SECRET`.

Go back to [Contents](#contents).


#### Web system

When a web system accesses the gRPC REST gateway, `fetchObjectFromRestGateway()` will be called, which initializes a JWT with an expiration time (e.g. 1 hour). This JWT is then passed on every request to the gRPC REST gateway as the authorization bearer in the header. If this JWT is successfully authenticated by the Rest Gateway, the gRPC endpoint will be reached. If the JWT is invalid, an error will be returned, and the gRPC endpoint will not be reached.

Go back to [Contents](#contents).


#### Rest Gateway

When the gRPC REST gateway receives a request, it must first verify and authenticate it using middleware (`jwtMiddleware()`). The following requirements are checked before the gRPC REST gateway complies with the request:
- The request contains an `Authorization header` with a `Bearer token`.
- The token's signing method is Hash-based message authentication code (or HMAC).
- The token is valid.
- The token is not expired.
- The token's secret matches the Rest Gateway's secret.

Go back to [Contents](#contents).


## Testing

### Overview

The REST Gateway has two types of tests:

1. **Unit Tests** (`main_test.go`) - Fast tests that verify endpoint registration and authentication without requiring a running Cuebot
2. **Integration Tests** (`integration_test.go`) - Comprehensive tests that verify actual API functionality with a running OpenCue system

---

### Unit Tests

Unit tests verify that all endpoints are properly registered and that basic authentication works.

#### Running Unit Tests

**Option 1: Docker (Recommended)**

```bash
# From OpenCue repository root
docker build -f rest_gateway/Dockerfile --target build -t opencue-gateway-test .
docker run --rm opencue-gateway-test sh -c "cd /app/opencue_gateway && go test -v"
```

**Option 2: Local Go**

```bash
# From rest_gateway/opencue_gateway directory
cd rest_gateway/opencue_gateway

# Run tests
go test -v

# Run with coverage
go test -v -cover

# Generate coverage report
go test -coverprofile=coverage.out
go tool cover -html=coverage.out -o coverage.html
```

**Option 3: Using Test Script**

```bash
cd rest_gateway/opencue_gateway
./run_tests.sh
# Select option 1 (Docker) or 2 (Local)
```

#### Expected Output

```
=== RUN   TestRegisteredEndpoints
=== RUN   TestRegisteredEndpoints/ShowInterface-GetShows
=== RUN   TestRegisteredEndpoints/JobInterface-GetJobs
...
=== RUN   TestJWTAuthentication
=== RUN   TestJWTAuthentication/ValidToken
=== RUN   TestJWTAuthentication/InvalidToken
...
--- PASS: TestRegisteredEndpoints (0.00s)
--- PASS: TestJWTAuthentication (0.01s)
PASS
ok      opencue_gateway    0.234s
```

---

### Integration Tests

Integration tests verify actual API functionality by making HTTP requests to a running REST Gateway connected to Cuebot.

#### Prerequisites

1. **Running OpenCue stack** (Cuebot, PostgreSQL)
2. **Running REST Gateway**
3. **Test show** with optional test jobs

#### Running Integration Tests

**Option 1: Automated Docker Script (Recommended)**

```bash
# From rest_gateway/opencue_gateway directory
./run_docker_integration_tests.sh
```

This script automatically:
- Starts the OpenCue stack
- Generates a JWT secret
- Builds and starts the REST Gateway
- Runs all integration tests
- Shows test results

**Option 2: Manual Setup**

```bash
# Step 1: Start OpenCue Stack
docker compose up -d

# Step 2: Generate JWT secret
export JWT_SECRET=$(openssl rand -base64 32)

# Step 3: Build and run REST Gateway
docker build -f rest_gateway/Dockerfile -t opencue-rest-gateway:latest .
docker run -d --name opencue-rest-gateway \
  --network opencue_default \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET="$JWT_SECRET" \
  -e LOG_LEVEL=info \
  opencue-rest-gateway:latest

# Step 4: Run integration tests
cd rest_gateway/opencue_gateway
go test -v -tags=integration
```

**Option 3: Specific Test**

```bash
# Run specific integration test
go test -v -tags=integration -run TestIntegration_ShowInterface

# Run with custom configuration
GATEWAY_URL=http://localhost:8448 \
JWT_SECRET=your-secret-key \
TEST_SHOW=testing \
go test -v -tags=integration
```

#### Integration Tests via Docker

```bash
# From OpenCue repository root

# Build test image
docker build -f rest_gateway/Dockerfile --target build -t opencue-gateway-test .

# Run integration tests in container
docker run --rm \
  --network opencue_default \
  -e GATEWAY_URL=http://opencue-rest-gateway:8448 \
  -e JWT_SECRET="$JWT_SECRET" \
  -e TEST_SHOW=testing \
  opencue-gateway-test \
  sh -c "cd /app/opencue_gateway && go test -v -tags=integration"
```

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_URL` | `http://localhost:8448` | REST Gateway endpoint URL |
| `JWT_SECRET` | `dev-secret-key-change-in-production` | JWT signing secret (must match gateway) |
| `TEST_SHOW` | `testing` | Show name to use for tests |

#### Integration Test Coverage

**Core Interfaces:**
- **ShowInterface** - GetShows, FindShow, GetActiveShows
- **JobInterface** - GetJobs
- **FrameInterface** - GetFrames (requires existing jobs)
- **LayerInterface** - GetLayers (requires existing jobs)
- **GroupInterface** - GetGroups
- **HostInterface** - GetHosts
- **OwnerInterface** - GetOwners
- **ProcInterface** - GetProcs
- **CommentInterface** - GetComments (requires existing jobs)

**Management Interfaces:**
- **AllocationInterface** - GetAll (#1908)
- **FacilityInterface** - Get (#1916)
- **FilterInterface** - GetFilters (#1909)
- **SubscriptionInterface** - GetSubscriptions (#1911)
- **LimitInterface** - GetAll (#1912)
- **ServiceInterface** - GetDefaultServices (#1913)

**Additional Tests:**
- **JWT Authentication** - Valid token, invalid token, missing token
- **Error Handling** - Invalid endpoints, malformed JSON, invalid data
- **Response Format** - Valid JSON, content-type headers
- **Performance** - Response time, concurrent requests
- **CORS** - CORS headers

---

### Benchmark Tests

Run performance benchmarks:

```bash
cd rest_gateway/opencue_gateway

# Run all benchmarks
go test -bench=. -tags=integration

# Run specific benchmark
go test -bench=BenchmarkIntegration_GetShows -tags=integration

# With memory allocation stats
go test -bench=. -benchmem -tags=integration

# Custom benchmark time
go test -bench=. -benchtime=10s -tags=integration
```

#### Example Benchmark Output

```
BenchmarkIntegration_GetShows-8         100    10234567 ns/op    2048 B/op    32 allocs/op
BenchmarkIntegration_GetJobs-8           50    23456789 ns/op    4096 B/op    64 allocs/op
BenchmarkIntegration_JWTGeneration-8   5000      234567 ns/op     512 B/op     8 allocs/op
```

---

### Continuous Integration

#### GitHub Actions Example

```yaml
name: REST Gateway Integration Tests

on: [push, pull_request]

jobs:
  integration-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:12
        env:
          POSTGRES_DB: cuebot
          POSTGRES_USER: cuebot
          POSTGRES_PASSWORD: cuebot
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Start OpenCue Stack
        run: |
          docker compose up -d
          sleep 30  # Wait for services to be ready

      - name: Build REST Gateway
        run: |
          docker build -f rest_gateway/Dockerfile -t opencue-rest-gateway .

      - name: Start REST Gateway
        run: |
          docker run -d --name opencue-rest-gateway \
            --network opencue_default \
            -p 8448:8448 \
            -e CUEBOT_ENDPOINT=cuebot:8443 \
            -e JWT_SECRET=test-secret-key \
            opencue-rest-gateway
          sleep 5

      - name: Run Integration Tests
        run: |
          cd rest_gateway/opencue_gateway
          JWT_SECRET=test-secret-key go test -v -tags=integration
```

---

### Troubleshooting

#### Unit Tests Fail

**Issue**: `package opencue_gateway/gen/go is not in std`

**Solution**: Run tests via Docker (includes protobuf generation) or generate protobuf code locally:

```bash
cd rest_gateway/opencue_gateway
./run_tests.sh
# Select option 1 (Docker)
```

#### Integration Tests Can't Connect

**Issue**: `failed to send request: connection refused`

**Solution**: Verify REST Gateway is running and accessible:

```bash
# Check gateway is running
curl -s -o /dev/null -w "%{http_code}" http://localhost:8448/
# Should return 401

# Check Docker containers
docker ps | grep opencue

# Check gateway logs
docker logs opencue-rest-gateway
```

#### JWT Authentication Fails

**Issue**: `401 Unauthorized` in integration tests

**Solution**: Ensure JWT_SECRET matches between gateway and tests:

```bash
# Use same secret for gateway and tests
export JWT_SECRET=$(openssl rand -base64 32)

# Restart gateway with this secret
docker rm -f opencue-rest-gateway
docker run -d --name opencue-rest-gateway \
  --network opencue_default \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET="$JWT_SECRET" \
  opencue-rest-gateway

# Run tests with same secret
JWT_SECRET="$JWT_SECRET" go test -v -tags=integration
```

#### Tests Skip Due to No Data

**Issue**: Many tests skip with "no jobs available"

**Solution**: This is expected if your OpenCue system has no jobs. Tests will skip gracefully. To run all tests, submit test jobs using OpenCue's Python API or CueGUI.

#### Performance Tests Timeout

**Issue**: Performance tests timeout or take too long

**Solution**: Skip performance tests in short mode:

```bash
go test -v -short -tags=integration
```

---

### Test Metrics

#### Coverage Goals

- **Unit Tests**: > 80% statement coverage
- **Integration Tests**: All 20 interfaces tested
- **Error Handling**: All error paths covered

#### Current Coverage

Check current coverage:

```bash
# Unit test coverage
go test -cover

# Integration test coverage
go test -tags=integration -cover

# Generate detailed coverage report
go test -coverprofile=coverage.out -tags=integration
go tool cover -func=coverage.out
go tool cover -html=coverage.out -o coverage.html
```

---

### Best Practices

#### Writing New Tests

1. **Unit tests** - Add to `main_test.go` for new endpoint registrations
2. **Integration tests** - Add to `integration_test.go` for new interfaces
3. **Use table-driven tests** for multiple similar test cases
4. **Use t.Skip()** for tests requiring specific setup
5. **Use subtests** with `t.Run()` for organization
6. **Clean up resources** in test cleanup functions

#### Example Test Pattern

```go
func TestIntegration_NewInterface(t *testing.T) {
    t.Run("GetSomething", func(t *testing.T) {
        payload := map[string]interface{}{
            "param": "value",
        }
        result, status, err := makeAuthenticatedRequest(t,
            "new.NewInterface/GetSomething", payload)

        assert.NoError(t, err)
        assert.Equal(t, http.StatusOK, status)
        assert.NotNil(t, result)
        assert.Contains(t, result, "expected_field")
    })
}
```

---

### Shell-Based Test Scripts

The REST Gateway also includes shell-based test scripts for comprehensive testing:

```bash
# Test with Docker Compose (comprehensive)
cd rest_gateway
./test_rest_gateway_docker_compose.sh

# Test local build and all endpoints
./test_gateway.sh

# Test Docker container
./test_docker_gateway.sh

# Test with live Cuebot instance
./test_live_cuebot.sh
```

**Test Scripts:**
- `opencue_gateway/run_docker_integration_tests.sh` - **Automated Docker-based integration tests covering all interfaces (recommended)**
- `opencue_gateway/run_tests.sh` - Interactive unit test runner
- `test_rest_gateway_docker_compose.sh` - Shell-based comprehensive testing with Docker Compose
- `test_gateway.sh` - Build validation and endpoint verification
- `test_docker_gateway.sh` - Docker container testing
- `test_live_cuebot.sh` - End-to-end testing with real Cuebot

---

### Additional Resources

- [Go Testing Documentation](https://golang.org/pkg/testing/)
- [Testify Documentation](https://github.com/stretchr/testify)
- [gRPC-Gateway Documentation](https://grpc-ecosystem.github.io/grpc-gateway/)

[Back to Contents](#contents)

## Development

### Building from Source

```bash
# Prerequisites
go version  # Go 1.21+ required
protoc --version  # Protocol Buffers compiler

# Clone and build
git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
cd OpenCue/rest_gateway/opencue_gateway

# Initialize module and install dependencies
go mod init opencue_gateway
go mod tidy

# Install protoc plugins
go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway@latest
go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2@latest
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Generate gRPC code
mkdir -p gen/go
protoc -I ../../proto/src/ \
    --go_out ./gen/go/ \
    --go_opt paths=source_relative \
    --go-grpc_out ./gen/go/ \
    --go-grpc_opt paths=source_relative \
    ../../proto/src/*.proto

# Generate REST gateway handlers
protoc -I ../../proto/src/ \
    --grpc-gateway_out ./gen/go \
    --grpc-gateway_opt paths=source_relative \
    --grpc-gateway_opt generate_unbound_methods=true \
    ../../proto/src/*.proto

# Build
go build -o opencue_gateway main.go

# Run
export CUEBOT_ENDPOINT=localhost:8443
export JWT_SECRET=dev-secret
export REST_PORT=8448
./opencue_gateway
```

### Adding New Interfaces

To add a new gRPC interface to the REST Gateway:

1. **Add the interface to `main.go`:**
```go
handlers := []func(context.Context, *runtime.ServeMux, string, []grpc.DialOption) error{
    // ... existing handlers
    gw.RegisterYourNewInterfaceHandlerFromEndpoint,
}
```

2. **Regenerate gRPC code:**
```bash
# Generate new .pb.go and .pb.gw.go files
protoc -I ../../proto/src/ \
    --go_out ./gen/go/ \
    --go_opt paths=source_relative \
    --go-grpc_out ./gen/go/ \
    --go-grpc_opt paths=source_relative \
    ../../proto/src/*.proto

protoc -I ../../proto/src/ \
    --grpc-gateway_out ./gen/go \
    --grpc-gateway_opt paths=source_relative \
    --grpc-gateway_opt generate_unbound_methods=true \
    ../../proto/src/*.proto
```

3. **Add tests:**
```go
// Add to main_test.go
{"YourInterface-Method", "your.YourInterface", "Method", map[string]interface{}{"param": "value"}},
```

4. **Update documentation:**
   - Add interface to README.md table
   - Add example endpoints
   - Update test scripts

[Back to Contents](#contents)

## Troubleshooting

### Common Issues

**1. "No Health Endpoint" - Expected Behavior**
```
curl http://localhost:8448/health
# Response: Authorization header required
```
- **This is NORMAL**: The REST Gateway has no unauthenticated endpoints
- **For health checks**: Use TCP checks or authenticated endpoint requests
- **Expected response**: 401 Unauthorized means the service is running correctly

**2. Connection Refused Error**
```
connection error: desc = "transport: Error while dialing: dial tcp [...]:8443: connect: connection refused"
```
- **Cause**: Cuebot server not accessible
- **Solution**: Verify `CUEBOT_ENDPOINT` and ensure Cuebot is running

**3. JWT Authentication Failures**
```
Authorization header required
Token validation error: token signature is invalid
```
- **Cause**: Missing, invalid, or incorrectly signed JWT token
- **Solution**: Verify `JWT_SECRET` matches between token creation and gateway

**4. Endpoint Not Found (404)**
```
404 Not Found
```
- **Cause**: Interface not registered or incorrect URL
- **Solution**: Check endpoint URL format: `/interface.InterfaceName/MethodName`

**5. Build Failures**
```
protoc-gen-go: program not found or is not executable
```
- **Cause**: Missing protoc plugins
- **Solution**: Install required tools and ensure they're in PATH

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=debug
./opencue_gateway
```

### Service Health Checks

**Important:** The OpenCue REST Gateway has NO unauthenticated endpoints. All endpoints require JWT authentication.

```bash
# Check if gateway is responding (expects 401 - this means service is up)
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8448/)
if [ "$response" = "401" ]; then
    echo "✓ Gateway is running and requiring authentication (as expected)"
else
    echo "✗ Gateway may not be running (got HTTP $response)"
fi

# For authenticated health check, use a valid endpoint with JWT
JWT_TOKEN=$(python3 -c "
import jwt, datetime
secret = 'default-secret-key'  # Use your actual JWT_SECRET
payload = {'user': 'health-check', 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}
print(jwt.encode(payload, secret, algorithm='HS256'))
")

curl -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "http://localhost:8448/show.ShowInterface/GetShows" \
     -d '{}'
# Should return actual shows data if Cuebot is connected and functioning
```
