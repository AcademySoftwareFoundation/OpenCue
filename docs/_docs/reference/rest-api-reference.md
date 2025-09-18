---
layout: default
title: OpenCue REST API Reference
parent: Reference
nav_order: 53
---

# OpenCue REST API Reference
{: .no_toc }

Complete API reference for the OpenCue REST Gateway endpoints, authentication, and data formats.

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

The OpenCue REST Gateway provides HTTP/REST endpoints for all OpenCue gRPC interfaces. It converts HTTP requests to gRPC calls and returns JSON responses, enabling web applications and HTTP clients to interact with OpenCue services.

### Base Information

- **Base URL**: `http://your-gateway:8448` (configurable)
- **Protocol**: HTTP/HTTPS
- **Authentication**: JWT Bearer tokens
- **Request Method**: POST (for all endpoints)
- **Content Type**: `application/json`
- **Response Format**: JSON

### Authentication

All endpoints require JWT authentication:

```http
POST /interface.Interface/Method
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

---

## Authentication

### JWT Token Requirements

- **Algorithm**: HMAC SHA256 (HS256)
- **Required Claims**: `sub` (subject), `exp` (expiration)
- **Header Format**: `Authorization: Bearer <token>`

### Token Creation Example

```python
import jwt
import time

def create_token(secret, user_id):
    payload = {
        'sub': user_id,
        'exp': int(time.time()) + 3600  # 1 hour
    }
    return jwt.encode(payload, secret, algorithm='HS256')
```

### Error Responses

| Status Code | Description |
|-------------|-------------|
| `401` | Missing or invalid Authorization header |
| `403` | Token validation failed or expired |
| `500` | Internal server error |

---

## Interface Overview

The REST API provides access to 9 core OpenCue interfaces:

| Interface | Purpose | Key Endpoints |
|-----------|---------|---------------|
| [Show Interface](#show-interface) | Show management | GetShows, FindShow, CreateShow |
| [Job Interface](#job-interface) | Job operations | GetJobs, FindJob, Kill, Pause, Resume |
| [Frame Interface](#frame-interface) | Frame management | GetFrame, Kill, Retry, Eat |
| [Layer Interface](#layer-interface) | Layer operations | GetLayer, FindLayer, Kill |
| [Group Interface](#group-interface) | Host groups | FindGroup, GetGroup, SetMinCores, SetMaxCores |
| [Host Interface](#host-interface) | Host management | GetHosts, FindHost, Lock, Unlock |
| [Owner Interface](#owner-interface) | Ownership | GetOwner, SetMaxCores, TakeOwnership |
| [Proc Interface](#proc-interface) | Process monitoring | GetProc, Kill, Unbook |
| [Deed Interface](#deed-interface) | Resource deeds | GetOwner, GetHost |

---

## Show Interface

Manage shows (projects) in OpenCue.

### Get All Shows

Get a list of all shows in the system.

```http
POST /show.ShowInterface/GetShows
```

**Request Body:**
```json
{}
```

**Response:**
```json
{
  "shows": {
    "shows": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "name": "myshow",
        "defaultMinCores": 1,
        "defaultMaxCores": 100,
        "commentEmail": "",
        "bookingEnabled": true,
        "dispatchEnabled": true,
        "active": true,
        "showStats": {
          "runningFrames": 5,
          "deadFrames": 0,
          "pendingFrames": 10,
          "pendingJobs": 2
        },
        "defaultMinGpus": 0,
        "defaultMaxGpus": 10
      }
    ]
  }
}
```

### Find Show

Find a specific show by name.

```http
POST /show.ShowInterface/FindShow
```

**Request Body:**
```json
{
  "name": "myshow"
}
```

**Response:**
```json
{
  "show": {
    "id": "00000000-0000-0000-0000-000000000000",
    "name": "myshow",
    "defaultMinCores": 1,
    "defaultMaxCores": 100,
    "active": true
  }
}
```

### Create Show

Create a new show.

```http
POST /show.ShowInterface/CreateShow
```

**Request Body:**
```json
{
  "name": "newshow",
  "defaultMinCores": 1,
  "defaultMaxCores": 50
}
```

**Response:**
```json
{
  "show": {
    "id": "new-show-id",
    "name": "newshow",
    "defaultMinCores": 1,
    "defaultMaxCores": 50,
    "active": true
  }
}
```

---

## Job Interface

Manage rendering jobs and their lifecycle.

### Get Jobs

Retrieve jobs for a show with optional filtering.

```http
POST /job.JobInterface/GetJobs
```

**Request Body:**
```json
{
  "r": {
    "show": {
      "name": "myshow"
    },
    "includeFinished": false,
    "maxResults": 100
  }
}
```

**Response:**
```json
{
  "jobs": {
    "jobs": [
      {
        "id": "job-id-123",
        "name": "myshow-shot001-comp",
        "state": "PENDING",
        "shot": "shot001",
        "show": "myshow",
        "user": "artist1",
        "group": "comp",
        "facility": "cloud",
        "priority": 100,
        "minCores": 1,
        "maxCores": 10,
        "isPaused": false,
        "hasComment": false,
        "startTime": 1694000000,
        "stopTime": 0,
        "jobStats": {
          "runningFrames": 0,
          "deadFrames": 0,
          "pendingFrames": 25,
          "succeededFrames": 0,
          "totalFrames": 25
        }
      }
    ]
  }
}
```

### Find Job

Find a specific job by name.

```http
POST /job.JobInterface/FindJob
```

**Request Body:**
```json
{
  "name": "myshow-shot001-comp"
}
```

### Get Job Frames

Retrieve frames for a specific job.

```http
POST /job.JobInterface/GetFrames
```

**Request Body:**
```json
{
  "job": {
    "id": "job-id-123"
  },
  "req": {
    "includeFinished": true,
    "page": 1,
    "limit": 100
  }
}
```

**Response:**
```json
{
  "frames": {
    "frames": [
      {
        "id": "frame-id-456",
        "name": "0001-layer_name",
        "layerName": "comp_layer",
        "number": 1,
        "state": "WAITING",
        "retryCount": 0,
        "exitStatus": -1,
        "startTime": 0,
        "stopTime": 0,
        "maxRss": "0",
        "usedMemory": "0",
        "lastResource": "/0.00/0"
      }
    ]
  }
}
```

### Pause Job

Pause a running or pending job.

```http
POST /job.JobInterface/Pause
```

**Request Body:**
```json
{
  "job": {
    "id": "job-id-123"
  }
}
```

**Response:**
```json
{}
```

### Resume Job

Resume a paused job.

```http
POST /job.JobInterface/Resume
```

**Request Body:**
```json
{
  "job": {
    "id": "job-id-123"
  }
}
```

### Kill Job

Terminate a job and all its frames.

```http
POST /job.JobInterface/Kill
```

**Request Body:**
```json
{
  "job": {
    "id": "job-id-123"
  }
}
```

---

## Frame Interface

Manage individual frame operations.

### Get Frame

Retrieve detailed information about a specific frame.

```http
POST /frame.FrameInterface/GetFrame
```

**Request Body:**
```json
{
  "id": "frame-id-456"
}
```

**Response:**
```json
{
  "frame": {
    "id": "frame-id-456",
    "name": "0001-layer_name",
    "layerName": "comp_layer",
    "number": 1,
    "state": "SUCCEEDED",
    "retryCount": 0,
    "exitStatus": 0,
    "startTime": 1694000000,
    "stopTime": 1694000300,
    "maxRss": "2147483648",
    "usedMemory": "1073741824",
    "totalCoreTime": 300
  }
}
```

### Retry Frame

Retry a failed frame.

```http
POST /frame.FrameInterface/Retry
```

**Request Body:**
```json
{
  "frame": {
    "id": "frame-id-456"
  }
}
```

### Kill Frame

Kill a running frame.

```http
POST /frame.FrameInterface/Kill
```

**Request Body:**
```json
{
  "frame": {
    "id": "frame-id-456"
  }
}
```

### Eat Frame

Mark a frame as completed (skip rendering).

```http
POST /frame.FrameInterface/Eat
```

**Request Body:**
```json
{
  "frame": {
    "id": "frame-id-456"
  }
}
```

---

## Layer Interface

Manage job layers and their properties.

### Get Layer

Retrieve layer information.

```http
POST /layer.LayerInterface/GetLayer
```

**Request Body:**
```json
{
  "id": "layer-id-789"
}
```

**Response:**
```json
{
  "layer": {
    "id": "layer-id-789",
    "name": "comp_layer",
    "type": "Render",
    "isEnabled": true,
    "minimumCores": 1,
    "maximumCores": 4,
    "minimumMemory": 2147483648,
    "layerStats": {
      "totalFrames": 25,
      "runningFrames": 0,
      "deadFrames": 0,
      "pendingFrames": 25,
      "succeededFrames": 0
    }
  }
}
```

### Find Layer

Find a layer within a job.

```http
POST /layer.LayerInterface/FindLayer
```

**Request Body:**
```json
{
  "job": {
    "id": "job-id-123"
  },
  "layer": "comp_layer"
}
```

### Get Layer Frames

Get all frames for a specific layer.

```http
POST /layer.LayerInterface/GetFrames
```

**Request Body:**
```json
{
  "layer": {
    "id": "layer-id-789"
  },
  "req": {
    "page": 1,
    "limit": 100
  }
}
```

### Kill Layer

Kill all frames in a layer.

```http
POST /layer.LayerInterface/Kill
```

**Request Body:**
```json
{
  "layer": {
    "id": "layer-id-789"
  }
}
```

---

## Host Interface

Manage render hosts and their resources.

### Get All Hosts

Retrieve all hosts in the render farm.

```http
POST /host.HostInterface/GetHosts
```

**Request Body:**
```json
{}
```

**Response:**
```json
{
  "hosts": {
    "hosts": [
      {
        "id": "host-id-abc",
        "name": "render-node-01",
        "lockState": "OPEN",
        "bootTime": 1694000000,
        "pingTime": 1694001000,
        "os": "linux",
        "totalCores": 16,
        "idleCores": 12,
        "totalMemory": 68719476736,
        "freeMemory": 34359738368,
        "totalGpus": 2,
        "freeGpus": 2,
        "hostStats": {
          "totalFrames": 4,
          "runningFrames": 4
        }
      }
    ]
  }
}
```

### Find Host

Find a specific host by name.

```http
POST /host.HostInterface/FindHost
```

**Request Body:**
```json
{
  "name": "render-node-01"
}
```

### Get Host

Get detailed host information.

```http
POST /host.HostInterface/GetHost
```

**Request Body:**
```json
{
  "id": "host-id-abc"
}
```

### Lock Host

Prevent new jobs from being assigned to a host.

```http
POST /host.HostInterface/Lock
```

**Request Body:**
```json
{
  "host": {
    "id": "host-id-abc"
  }
}
```

### Unlock Host

Allow jobs to be assigned to a host.

```http
POST /host.HostInterface/Unlock
```

**Request Body:**
```json
{
  "host": {
    "id": "host-id-abc"
  }
}
```

---

## Group Interface

Manage resource groups and allocation.

### Find Group

Find a group within a show.

```http
POST /group.GroupInterface/FindGroup
```

**Request Body:**
```json
{
  "show": {
    "name": "myshow"
  },
  "name": "comp"
}
```

**Response:**
```json
{
  "group": {
    "id": "group-id-def",
    "name": "comp",
    "department": "compositing",
    "defaultJobPriority": 100,
    "defaultJobMinCores": 1,
    "defaultJobMaxCores": 8,
    "groupStats": {
      "runningFrames": 5,
      "deadFrames": 0,
      "pendingFrames": 20,
      "pendingJobs": 3
    }
  }
}
```

### Get Group

Get detailed group information.

```http
POST /group.GroupInterface/GetGroup
```

**Request Body:**
```json
{
  "id": "group-id-def"
}
```

### Set Minimum Cores

Set minimum core allocation for a group.

```http
POST /group.GroupInterface/SetMinCores
```

**Request Body:**
```json
{
  "group": {
    "id": "group-id-def"
  },
  "cores": 4
}
```

### Set Maximum Cores

Set maximum core allocation for a group.

```http
POST /group.GroupInterface/SetMaxCores
```

**Request Body:**
```json
{
  "group": {
    "id": "group-id-def"
  },
  "cores": 16
}
```

---

## Owner Interface

Manage resource ownership and allocation.

### Get Owner

Get owner information and resource allocation.

```http
POST /owner.OwnerInterface/GetOwner
```

**Request Body:**
```json
{
  "name": "artist1"
}
```

**Response:**
```json
{
  "owner": {
    "name": "artist1",
    "maxCores": 20,
    "minCores": 2,
    "maxGpus": 4,
    "minGpus": 0,
    "ownerStats": {
      "runningFrames": 8,
      "maxFrames": 50
    }
  }
}
```

### Set Maximum Cores

Set maximum core allocation for an owner.

```http
POST /owner.OwnerInterface/SetMaxCores
```

**Request Body:**
```json
{
  "owner": {
    "name": "artist1"
  },
  "cores": 32
}
```

### Take Ownership

Take ownership of a host.

```http
POST /owner.OwnerInterface/TakeOwnership
```

**Request Body:**
```json
{
  "host": {
    "id": "host-id-abc"
  },
  "owner": {
    "name": "artist1"
  }
}
```

---

## Proc Interface

Manage running processes on hosts.

### Get Process

Get information about a running process.

```http
POST /proc.ProcInterface/GetProc
```

**Request Body:**
```json
{
  "id": "proc-id-ghi"
}
```

**Response:**
```json
{
  "proc": {
    "id": "proc-id-ghi",
    "name": "render_process",
    "logPath": "/tmp/rqd/logs/render_process.log",
    "unbooked": false,
    "reserved": true,
    "bookedCores": 4,
    "virtualMemory": 8589934592,
    "usedMemory": 4294967296,
    "bookedGpus": 1,
    "usedGpuMemory": 2147483648
  }
}
```

### Kill Process

Terminate a running process.

```http
POST /proc.ProcInterface/Kill
```

**Request Body:**
```json
{
  "proc": {
    "id": "proc-id-ghi"
  }
}
```

### Unbook Process

Unbook resources from a process.

```http
POST /proc.ProcInterface/Unbook
```

**Request Body:**
```json
{
  "proc": {
    "id": "proc-id-ghi"
  }
}
```

---

## Deed Interface

Manage resource deeds and ownership records.

### Get Deed Owner

Get the owner of a deed.

```http
POST /deed.DeedInterface/GetOwner
```

**Request Body:**
```json
{
  "deed": {
    "id": "deed-id-jkl"
  }
}
```

**Response:**
```json
{
  "owner": {
    "name": "artist1",
    "maxCores": 20,
    "minCores": 2
  }
}
```

### Get Deed Host

Get the host associated with a deed.

```http
POST /deed.DeedInterface/GetHost
```

**Request Body:**
```json
{
  "deed": {
    "id": "deed-id-jkl"
  }
}
```

**Response:**
```json
{
  "host": {
    "id": "host-id-abc",
    "name": "render-node-01",
    "lockState": "OPEN",
    "totalCores": 16,
    "idleCores": 8
  }
}
```

---

## Data Types

### Common Types

#### Job States

```
PENDING    - Job is waiting to start
RUNNING    - Job has active frames
FINISHED   - Job completed successfully
KILLED     - Job was terminated
PAUSED     - Job is paused
```

#### Frame States

```
WAITING    - Frame is waiting to start
RUNNING    - Frame is currently executing
SUCCEEDED  - Frame completed successfully
DEAD       - Frame failed
EATEN      - Frame was skipped
```

#### Host Lock States

```
OPEN       - Host accepts new jobs
LOCKED     - Host locked by user
NIMBY      - Host locked automatically
```

### Request/Response Objects

#### Job Object

```json
{
  "id": "string",
  "name": "string",
  "state": "JobState",
  "shot": "string",
  "show": "string",
  "user": "string",
  "group": "string",
  "facility": "string",
  "priority": "int32",
  "minCores": "float",
  "maxCores": "float",
  "isPaused": "bool",
  "hasComment": "bool",
  "startTime": "int32",
  "stopTime": "int32",
  "jobStats": {
    "runningFrames": "int32",
    "deadFrames": "int32",
    "pendingFrames": "int32",
    "succeededFrames": "int32",
    "totalFrames": "int32"
  }
}
```

#### Frame Object

```json
{
  "id": "string",
  "name": "string",
  "layerName": "string",
  "number": "int32",
  "state": "FrameState",
  "retryCount": "int32",
  "exitStatus": "int32",
  "startTime": "int32",
  "stopTime": "int32",
  "maxRss": "string",
  "usedMemory": "string",
  "lastResource": "string",
  "totalCoreTime": "int32"
}
```

#### Host Object

```json
{
  "id": "string",
  "name": "string",
  "lockState": "LockState",
  "bootTime": "int32",
  "pingTime": "int32",
  "os": "string",
  "totalCores": "int32",
  "idleCores": "int32",
  "totalMemory": "int64",
  "freeMemory": "int64",
  "totalGpus": "int32",
  "freeGpus": "int32"
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": "string",
  "code": "int32",
  "message": "string"
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `2` | `UNKNOWN` | Unknown error occurred |
| `3` | `INVALID_ARGUMENT` | Invalid request parameters |
| `5` | `NOT_FOUND` | Requested resource not found |
| `7` | `PERMISSION_DENIED` | Insufficient permissions |
| `16` | `UNAUTHENTICATED` | Authentication required |

### HTTP Status Codes

| Status | Meaning |
|--------|---------|
| `200` | Success |
| `400` | Bad Request - Invalid JSON or parameters |
| `401` | Unauthorized - Missing or invalid JWT |
| `403` | Forbidden - JWT validation failed |
| `404` | Not Found - Resource not found |
| `500` | Internal Server Error |

---

## Rate Limiting

The REST Gateway implements rate limiting to prevent abuse:

- **Default Limit**: 100 requests per second per client
- **Configurable**: Set via `RATE_LIMIT_RPS` environment variable
- **Headers**: Rate limit information in response headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1694001000
```

---

## Best Practices

### Performance

1. **Batch Requests**: Group related operations when possible
2. **Use Pagination**: Limit large data requests with page/limit parameters
3. **Cache Responses**: Implement client-side caching for static data
4. **Connection Pooling**: Reuse HTTP connections for multiple requests

### Security

1. **Token Expiration**: Use short-lived JWT tokens (1-2 hours)
2. **HTTPS Only**: Always use HTTPS in production
3. **Input Validation**: Validate all request parameters
4. **Error Handling**: Don't expose sensitive information in errors

### Reliability

1. **Retry Logic**: Implement exponential backoff for failed requests
2. **Circuit Breaker**: Use circuit breaker pattern for service calls
3. **Health Checks**: Monitor gateway health endpoints
4. **Graceful Degradation**: Handle partial failures gracefully

---

## SDK Examples

### Python Client

```python
import requests
import jwt
import time

class OpenCueClient:
    def __init__(self, base_url, jwt_secret):
        self.base_url = base_url
        self.jwt_secret = jwt_secret

    def _get_headers(self):
        token = jwt.encode({
            'sub': 'api-client',
            'exp': int(time.time()) + 3600
        }, self.jwt_secret, algorithm='HS256')

        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def get_shows(self):
        response = requests.post(
            f'{self.base_url}/show.ShowInterface/GetShows',
            headers=self._get_headers(),
            json={}
        )
        return response.json()

    def pause_job(self, job_id):
        response = requests.post(
            f'{self.base_url}/job.JobInterface/Pause',
            headers=self._get_headers(),
            json={'job': {'id': job_id}}
        )
        return response.json()

# Usage
client = OpenCueClient('http://localhost:8448', 'your-secret')
shows = client.get_shows()
client.pause_job('job-id-123')
```

### JavaScript Client

```javascript
class OpenCueClient {
  constructor(baseUrl, jwtSecret) {
    this.baseUrl = baseUrl;
    this.jwtSecret = jwtSecret;
  }

  async getHeaders() {
    const token = await this.createJWT();
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  async createJWT() {
    // Use jsonwebtoken library
    const jwt = require('jsonwebtoken');
    return jwt.sign({
      sub: 'web-client',
      exp: Math.floor(Date.now() / 1000) + 3600
    }, this.jwtSecret);
  }

  async getShows() {
    const headers = await this.getHeaders();
    const response = await fetch(
      `${this.baseUrl}/show.ShowInterface/GetShows`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({})
      }
    );
    return response.json();
  }

  async pauseJob(jobId) {
    const headers = await this.getHeaders();
    const response = await fetch(
      `${this.baseUrl}/job.JobInterface/Pause`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({ job: { id: jobId } })
      }
    );
    return response.json();
  }
}

// Usage
const client = new OpenCueClient('http://localhost:8448', 'your-secret');
const shows = await client.getShows();
await client.pauseJob('job-id-123');
```

---

## What's next?

- [Using the REST API](/docs/user-guides/using-rest-api/) - Usage examples and integration
- [REST API Tutorial](/docs/tutorials/rest-api-tutorial/) - Step-by-step walkthrough
- [Deploying REST Gateway](/docs/getting-started/deploying-rest-gateway) - Deployment instructions
- [CueWeb Developer Guide](/docs/developer-guide/cueweb-development) - Integration examples with CueWeb