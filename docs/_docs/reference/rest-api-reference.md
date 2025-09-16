---
title: "REST API Reference"
nav_order: 45
parent: Reference
layout: default
linkTitle: "OpenCue REST API Reference"
date: 2025-09-15
description: >
  Reference for OpenCue REST API endpoints and data structures
---

# REST API Reference

### Specification for OpenCue REST API endpoints

---

The OpenCue REST Gateway provides HTTP/REST endpoints for all OpenCue gRPC functionality. All endpoints use JSON for request and response payloads and require JWT authentication.

## Base URL and Authentication

**Base URL:** `http://localhost:8448` (or your gateway endpoint)

**Authentication:** ALL endpoints require JWT authentication - there are no public endpoints:
```
Authorization: Bearer <jwt-token>
```

**Content Type:** All requests must include:
```
Content-Type: application/json
```

**Important:** The REST Gateway has no unauthenticated health or status endpoints. Every API call requires a valid JWT token.

## Interface Overview

The REST API provides access to 9 core OpenCue interfaces:

| Interface | Purpose | Key Endpoints |
|-----------|---------|---------------|
| [Show](#show-interface) | Show management | GetShows, GetShow, CreateShow, Delete, GetActiveShows |
| [Job](#job-interface) | Job operations | GetJobs, GetJob, Kill, Pause, Resume, SetPriority, GetUpdatedFrames, SetAutoEat |
| [Frame](#frame-interface) | Frame management | GetFrames, GetFrame, Kill, Retry, Eat, MarkAsWaiting |
| [Layer](#layer-interface) | Layer operations | GetLayers, GetLayer, Kill, SetTags |
| [Group](#group-interface) | Host groups | GetGroups, GetGroup, CreateGroup |
| [Host](#host-interface) | Host management | GetHosts, GetHost, Lock, Unlock, Reboot |
| [Owner](#owner-interface) | Ownership | GetOwners, GetOwner |
| [Proc](#proc-interface) | Process monitoring | GetProcs, GetProc, Kill |
| [Deed](#deed-interface) | Resource deeds | GetDeeds, GetDeed |

## Show Interface

Manages OpenCue shows (production contexts).

### GetShows
Retrieve all shows in the system.

**Endpoint:** `POST /show.ShowInterface/GetShows`

**Request:**
```json
{}
```

**Response:**
```json
{
  "shows": [
    {
      "id": "show-uuid",
      "name": "my-show",
      "active": true,
      "default_min_cores": 1.0,
      "default_max_cores": 10.0
    }
  ]
}
```

### GetShow
Get details for a specific show.

**Endpoint:** `POST /show.ShowInterface/GetShow`

**Request:**
```json
{
  "name": "my-show"
}
```

**Response:**
```json
{
  "show": {
    "id": "show-uuid",
    "name": "my-show",
    "active": true,
    "default_min_cores": 1.0,
    "default_max_cores": 10.0,
    "comment_email": "admin@studio.com"
  }
}
```

### CreateShow
Create a new show.

**Endpoint:** `POST /show.ShowInterface/CreateShow`

**Request:**
```json
{
  "name": "new-show",
  "active": true,
  "default_min_cores": 1.0,
  "default_max_cores": 10.0
}
```

### Delete
Delete a show.

**Endpoint:** `POST /show.ShowInterface/Delete`

**Request:**
```json
{
  "show": {
    "name": "show-to-delete"
  }
}
```

### GetActiveShows
Get only active shows.

**Endpoint:** `POST /show.ShowInterface/GetActiveShows`

**Request:**
```json
{}
```

## Job Interface

Manages rendering jobs within shows.

### GetJobs
Retrieve jobs with optional filtering.

**Endpoint:** `POST /job.JobInterface/GetJobs`

**Request:**
```json
{
  "r": {
    "show": "my-show",
    "user": "artist1",
    "shot": "shot001"
  }
}
```

**Response:**
```json
{
  "jobs": [
    {
      "id": "job-uuid",
      "name": "my-job",
      "show": "my-show",
      "user": "artist1",
      "state": "PENDING",
      "total_frames": 100,
      "stats": {
        "pending_frames": 90,
        "running_frames": 10,
        "succeeded_frames": 0,
        "dead_frames": 0
      }
    }
  ]
}
```

### GetJob
Get detailed information about a specific job.

**Endpoint:** `POST /job.JobInterface/GetJob`

**Request:**
```json
{
  "id": "job-uuid"
}
```

### Kill
Kill a running job.

**Endpoint:** `POST /job.JobInterface/Kill`

**Request:**
```json
{
  "job": {
    "id": "job-uuid"
  }
}
```

### Pause
Pause job execution.

**Endpoint:** `POST /job.JobInterface/Pause`

**Request:**
```json
{
  "job": {
    "id": "job-uuid"
  }
}
```

### Resume
Resume a paused job.

**Endpoint:** `POST /job.JobInterface/Resume`

**Request:**
```json
{
  "job": {
    "id": "job-uuid"
  }
}
```

### SetPriority
Change job priority.

**Endpoint:** `POST /job.JobInterface/SetPriority`

**Request:**
```json
{
  "job": {
    "id": "job-uuid"
  },
  "priority": 50
}
```

### GetUpdatedFrames
Get frame updates since a timestamp.

**Endpoint:** `POST /job.JobInterface/GetUpdatedFrames`

**Request:**
```json
{
  "job": {
    "id": "job-uuid"
  },
  "last_check": 1642284000
}
```

### SetAutoEat
Configure automatic frame eating.

**Endpoint:** `POST /job.JobInterface/SetAutoEat`

**Request:**
```json
{
  "job": {
    "id": "job-uuid"
  },
  "value": true
}
```

## Frame Interface

Manages individual frames within jobs.

### GetFrames
Retrieve frames for a job.

**Endpoint:** `POST /frame.FrameInterface/GetFrames`

**Request:**
```json
{
  "r": {
    "job": "job-uuid",
    "state": ["SUCCEEDED", "DEAD"]
  }
}
```

**Response:**
```json
{
  "frames": [
    {
      "id": "frame-uuid",
      "name": "frame_001",
      "state": "SUCCEEDED",
      "layer": "render",
      "number": 1,
      "dispatch_order": 1,
      "start_time": 1642284000,
      "stop_time": 1642284300,
      "core_time": 300.0
    }
  ]
}
```

### GetFrame
Get detailed frame information.

**Endpoint:** `POST /frame.FrameInterface/GetFrame`

**Request:**
```json
{
  "id": "frame-uuid"
}
```

### Kill
Kill a running frame.

**Endpoint:** `POST /frame.FrameInterface/Kill`

**Request:**
```json
{
  "frame": {
    "id": "frame-uuid"
  }
}
```

### Retry
Retry a failed frame.

**Endpoint:** `POST /frame.FrameInterface/Retry`

**Request:**
```json
{
  "frame": {
    "id": "frame-uuid"
  }
}
```

### Eat
Mark frame as eaten (successful without re-running).

**Endpoint:** `POST /frame.FrameInterface/Eat`

**Request:**
```json
{
  "frame": {
    "id": "frame-uuid"
  }
}
```

### MarkAsWaiting
Reset frame to waiting state.

**Endpoint:** `POST /frame.FrameInterface/MarkAsWaiting`

**Request:**
```json
{
  "frame": {
    "id": "frame-uuid"
  }
}
```

## Layer Interface

Manages layers within jobs.

### GetLayers
Get layers for a job.

**Endpoint:** `POST /layer.LayerInterface/GetLayers`

**Request:**
```json
{
  "r": {
    "job": "job-uuid"
  }
}
```

**Response:**
```json
{
  "layers": [
    {
      "id": "layer-uuid",
      "name": "render",
      "type": "Render",
      "min_cores": 1.0,
      "max_cores": 4.0,
      "min_memory": 2048,
      "tags": ["linux", "maya"]
    }
  ]
}
```

### GetLayer
Get specific layer details.

**Endpoint:** `POST /layer.LayerInterface/GetLayer`

**Request:**
```json
{
  "id": "layer-uuid"
}
```

### Kill
Kill all frames in a layer.

**Endpoint:** `POST /layer.LayerInterface/Kill`

**Request:**
```json
{
  "layer": {
    "id": "layer-uuid"
  }
}
```

### SetTags
Update layer tags.

**Endpoint:** `POST /layer.LayerInterface/SetTags`

**Request:**
```json
{
  "layer": {
    "id": "layer-uuid"
  },
  "tags": ["linux", "maya2024"]
}
```

## Host Interface

Manages rendering hosts.

### GetHosts
List rendering hosts.

**Endpoint:** `POST /host.HostInterface/GetHosts`

**Request:**
```json
{
  "r": {
    "allocation": "general",
    "state": ["UP"]
  }
}
```

**Response:**
```json
{
  "hosts": [
    {
      "id": "host-uuid",
      "name": "render01",
      "state": "UP",
      "lock_state": "OPEN",
      "cores": 16,
      "memory": 32768,
      "idle_cores": 8,
      "idle_memory": 16384
    }
  ]
}
```

### GetHost
Get specific host details.

**Endpoint:** `POST /host.HostInterface/GetHost`

**Request:**
```json
{
  "name": "render01"
}
```

### Lock
Lock a host for maintenance.

**Endpoint:** `POST /host.HostInterface/Lock`

**Request:**
```json
{
  "host": {
    "name": "render01"
  }
}
```

### Unlock
Unlock a host.

**Endpoint:** `POST /host.HostInterface/Unlock`

**Request:**
```json
{
  "host": {
    "name": "render01"
  }
}
```

### Reboot
Reboot a host.

**Endpoint:** `POST /host.HostInterface/Reboot`

**Request:**
```json
{
  "host": {
    "name": "render01"
  }
}
```

## Group Interface

Manages host groups and allocations.

### GetGroups
List host groups.

**Endpoint:** `POST /group.GroupInterface/GetGroups`

**Request:**
```json
{}
```

**Response:**
```json
{
  "groups": [
    {
      "id": "group-uuid",
      "name": "linux_farm",
      "parent": "root",
      "cores": 256,
      "idle_cores": 128
    }
  ]
}
```

### GetGroup
Get specific group details.

**Endpoint:** `POST /group.GroupInterface/GetGroup`

**Request:**
```json
{
  "name": "linux_farm"
}
```

### CreateGroup
Create a new host group.

**Endpoint:** `POST /group.GroupInterface/CreateGroup`

**Request:**
```json
{
  "name": "new_group",
  "parent": "linux_farm"
}
```

## Owner Interface

Manages ownership and allocations.

### GetOwners
List owners.

**Endpoint:** `POST /owner.OwnerInterface/GetOwners`

**Request:**
```json
{}
```

### GetOwner
Get specific owner details.

**Endpoint:** `POST /owner.OwnerInterface/GetOwner`

**Request:**
```json
{
  "name": "department1"
}
```

## Proc Interface

Monitors running processes.

### GetProcs
List running processes.

**Endpoint:** `POST /proc.ProcInterface/GetProcs`

**Request:**
```json
{
  "r": {
    "host": "render01"
  }
}
```

### GetProc
Get specific process details.

**Endpoint:** `POST /proc.ProcInterface/GetProc`

**Request:**
```json
{
  "id": "proc-uuid"
}
```

### Kill
Kill a running process.

**Endpoint:** `POST /proc.ProcInterface/Kill`

**Request:**
```json
{
  "proc": {
    "id": "proc-uuid"
  }
}
```

## Deed Interface

Manages resource deeds.

### GetDeeds
List resource deeds.

**Endpoint:** `POST /deed.DeedInterface/GetDeeds`

**Request:**
```json
{
  "r": {}
}
```

### GetDeed
Get specific deed details.

**Endpoint:** `POST /deed.DeedInterface/GetDeed`

**Request:**
```json
{
  "id": "deed-uuid"
}
```

## Common Data Types

### Frame States
- `WAITING` - Frame is waiting to be dispatched
- `RUNNING` - Frame is currently executing
- `SUCCEEDED` - Frame completed successfully
- `DEAD` - Frame failed
- `EATEN` - Frame marked as complete without execution

### Host States
- `UP` - Host is online and available
- `DOWN` - Host is offline
- `REBOOT` - Host is rebooting

### Lock States
- `OPEN` - Host accepts new jobs
- `LOCKED` - Host is locked for maintenance
- `NIMBY_LOCKED` - Host locked by user activity

## Error Responses

Standard error response format:

```json
{
  "error": "rpc error: code = NotFound desc = Job not found",
  "code": 5,
  "message": "Job not found"
}
```

### Common Error Codes
- `3` - INVALID_ARGUMENT
- `5` - NOT_FOUND
- `7` - PERMISSION_DENIED
- `16` - UNAUTHENTICATED

## Rate Limits and Pagination

- No explicit rate limits currently implemented
- Large result sets should be filtered using request parameters
- Consider implementing client-side pagination for UI applications

## What's next?

- [Using the REST API](/docs/user-guides/using-rest-api/) - Usage examples and integration
- [REST API Tutorial](/docs/tutorials/rest-api-tutorial/) - Step-by-step walkthrough
