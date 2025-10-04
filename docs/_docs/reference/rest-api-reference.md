---
layout: default
title: OpenCue REST API Reference
parent: Reference
nav_order: 62
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

The REST API provides access to all OpenCue interfaces:

### Core Interfaces

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

### Management Interfaces

| Interface | Purpose | Key Endpoints |
|-----------|---------|---------------|
| [Allocation Interface](#allocation-interface) | Resource allocation | GetAll, Get, Find, GetHosts, SetBillable |
| [Facility Interface](#facility-interface) | Multi-site management | Get, Create, Delete, GetAllocations |
| [Filter Interface](#filter-interface) | Job filters | FindFilter, GetActions, GetMatchers, SetEnabled |
| [Action Interface](#action-interface) | Filter actions | Delete, Commit, GetParentFilter |
| [Matcher Interface](#matcher-interface) | Filter matchers | Delete, Commit, GetParentFilter |
| [Depend Interface](#depend-interface) | Dependencies | GetDepend, Satisfy, Unsatisfy |
| [Subscription Interface](#subscription-interface) | Show subscriptions | Get, Find, Delete, SetSize, SetBurst |
| [Limit Interface](#limit-interface) | Resource limits | GetAll, Get, Create, Delete, SetMaxValue |
| [Service Interface](#service-interface) | Service definitions | GetService, GetDefaultServices, CreateService, Update, Delete |
| [ServiceOverride Interface](#serviceoverride-interface) | Service overrides | Update, Delete |
| [Task Interface](#task-interface) | Task management | Delete, SetMinCores, ClearAdjustments |

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

### Set Layer Tags

Set tags on a layer for job categorization and routing. Tags help filter and organize layers by render type, software, or other attributes.

```http
POST /layer.LayerInterface/SetTags
```

**Request Body:**
```json
{
  "layer": {
    "id": "layer-id-789"
  },
  "tags": ["nuke", "comp", "high-priority"]
}
```

**Response:**
```json
{}
```

**Use Cases:**
- Tag layers by software (nuke, maya, blender, houdini)
- Tag by render type (comp, lighting, fx, sim)
- Tag by priority or department for resource allocation
- Filter jobs by layer tags in monitoring dashboards

**Note:** SetTags replaces all existing tags on the layer. To retrieve current tags, call GetLayer - the tags field is included in the layer response:

```json
{
  "layer": {
    "id": "layer-id-789",
    "name": "comp_layer",
    "tags": ["nuke", "comp", "high-priority"],
    "type": "Render",
    "isEnabled": true
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

### Add Tags to Host

Add one or more tags to a host for categorization and filtering.

```http
POST /host.HostInterface/AddTags
```

**Request Body:**
```json
{
  "host": {
    "id": "host-id-abc"
  },
  "tags": ["gpu", "high-memory", "linux"]
}
```

**Response:**
```json
{}
```

**Use Cases:**
- Tag hosts by hardware capabilities (gpu, cpu-only, high-memory)
- Tag hosts by location or department (studio-a, comp-team)
- Tag hosts for specific job routing and allocation

### Remove Tags from Host

Remove one or more tags from a host.

```http
POST /host.HostInterface/RemoveTags
```

**Request Body:**
```json
{
  "host": {
    "id": "host-id-abc"
  },
  "tags": ["gpu", "high-memory"]
}
```

**Response:**
```json
{}
```

### Rename Host Tag

Rename a tag across a host (useful for standardizing tag names).

```http
POST /host.HostInterface/RenameTag
```

**Request Body:**
```json
{
  "host": {
    "id": "host-id-abc"
  },
  "old_tag": "gpu",
  "new_tag": "nvidia-gpu"
}
```

**Response:**
```json
{}
```

### Get Host Tags

Retrieve tags for a host by calling GetHost - tags are included in the host object.

```http
POST /host.HostInterface/GetHost
```

**Request Body:**
```json
{
  "id": "host-id-abc"
}
```

**Response:**
```json
{
  "host": {
    "id": "host-id-abc",
    "name": "render-node-01",
    "tags": ["gpu", "high-memory", "linux"],
    "lockState": "OPEN",
    "totalCores": 16,
    "totalMemory": 68719476736,
    "totalGpus": 2
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

## Allocation Interface

Manage resource allocations across facilities and shows.

### Get All Allocations

Retrieve all allocations in the system.

```http
POST /facility.AllocationInterface/GetAll
```

**Request Body:**
```json
{}
```

**Response:**
```json
{
  "allocations": {
    "allocations": [
      {
        "id": "alloc-id-123",
        "name": "cloud",
        "tag": "cloud",
        "facility": "aws-us-west",
        "billable": true,
        "stats": {
          "cores": 256,
          "availableCores": 128,
          "idleCores": 64,
          "runningCores": 64,
          "lockedCores": 0,
          "hosts": 16,
          "lockedHosts": 0,
          "downHosts": 0
        }
      }
    ]
  }
}
```

### Get Allocation

Get details for a specific allocation.

```http
POST /facility.AllocationInterface/Get
```

**Request Body:**
```json
{
  "id": "alloc-id-123"
}
```

### Find Allocation

Find an allocation by name.

```http
POST /facility.AllocationInterface/Find
```

**Request Body:**
```json
{
  "name": "cloud"
}
```

### Get Allocation Hosts

Get all hosts in an allocation.

```http
POST /facility.AllocationInterface/GetHosts
```

**Request Body:**
```json
{
  "allocation": {
    "id": "alloc-id-123"
  }
}
```

### Set Allocation Billable

Set whether an allocation is billable.

```http
POST /facility.AllocationInterface/SetBillable
```

**Request Body:**
```json
{
  "allocation": {
    "id": "alloc-id-123"
  },
  "value": true
}
```

---

## Facility Interface

Manage multi-site render farm facilities.

### Get Facility

Get facility information by name.

```http
POST /facility.FacilityInterface/Get
```

**Request Body:**
```json
{
  "name": "aws-us-west"
}
```

**Response:**
```json
{
  "facility": {
    "id": "facility-id-456",
    "name": "aws-us-west"
  }
}
```

### Create Facility

Create a new facility.

```http
POST /facility.FacilityInterface/Create
```

**Request Body:**
```json
{
  "name": "aws-us-east"
}
```

### Delete Facility

Mark a facility as inactive.

```http
POST /facility.FacilityInterface/Delete
```

**Request Body:**
```json
{
  "name": "aws-us-east"
}
```

### Get Facility Allocations

Get all allocations for a facility.

```http
POST /facility.FacilityInterface/GetAllocations
```

**Request Body:**
```json
{
  "facility": {
    "id": "facility-id-456"
  }
}
```

---

## Filter Interface

Manage job filters for automated job routing and actions.

### Find Filter

Find a filter by show and name.

```http
POST /filter.FilterInterface/FindFilter
```

**Request Body:**
```json
{
  "show": "myshow",
  "name": "auto_priority"
}
```

**Response:**
```json
{
  "filter": {
    "id": "filter-id-789",
    "name": "auto_priority",
    "type": "MATCH_ALL",
    "order": 1,
    "enabled": true
  }
}
```

### Get Filter Actions

Get all actions for a filter.

```http
POST /filter.FilterInterface/GetActions
```

**Request Body:**
```json
{
  "filter": {
    "id": "filter-id-789"
  }
}
```

**Response:**
```json
{
  "actions": {
    "actions": [
      {
        "id": "action-id-abc",
        "type": "SET_JOB_PRIORITY",
        "valueType": "INTEGER_TYPE",
        "integerValue": 200
      }
    ]
  }
}
```

### Get Filter Matchers

Get all matchers for a filter.

```http
POST /filter.FilterInterface/GetMatchers
```

**Request Body:**
```json
{
  "filter": {
    "id": "filter-id-789"
  }
}
```

**Response:**
```json
{
  "matchers": {
    "matchers": [
      {
        "id": "matcher-id-def",
        "subject": "JOB_NAME",
        "type": "CONTAINS",
        "input": "urgent"
      }
    ]
  }
}
```

### Set Filter Enabled

Enable or disable a filter.

```http
POST /filter.FilterInterface/SetEnabled
```

**Request Body:**
```json
{
  "filter": {
    "id": "filter-id-789"
  },
  "enabled": true
}
```

### Delete Filter

Delete a filter.

```http
POST /filter.FilterInterface/Delete
```

**Request Body:**
```json
{
  "filter": {
    "id": "filter-id-789"
  }
}
```

---

## Action Interface

Manage filter actions.

### Delete Action

Delete a filter action.

```http
POST /filter.ActionInterface/Delete
```

**Request Body:**
```json
{
  "action": {
    "id": "action-id-abc"
  }
}
```

### Commit Action

Update action properties.

```http
POST /filter.ActionInterface/Commit
```

**Request Body:**
```json
{
  "action": {
    "id": "action-id-abc",
    "type": "SET_JOB_PRIORITY",
    "integerValue": 250
  }
}
```

---

## Matcher Interface

Manage filter matchers.

### Delete Matcher

Delete a filter matcher.

```http
POST /filter.MatcherInterface/Delete
```

**Request Body:**
```json
{
  "matcher": {
    "id": "matcher-id-def"
  }
}
```

### Commit Matcher

Update matcher properties.

```http
POST /filter.MatcherInterface/Commit
```

**Request Body:**
```json
{
  "matcher": {
    "id": "matcher-id-def",
    "subject": "JOB_NAME",
    "type": "REGEX",
    "input": "^urgent.*"
  }
}
```

---

## Depend Interface

Manage job and frame dependencies.

### Get Dependency

Get a dependency by ID.

```http
POST /depend.DependInterface/GetDepend
```

**Request Body:**
```json
{
  "id": "depend-id-ghi"
}
```

**Response:**
```json
{
  "depend": {
    "id": "depend-id-ghi",
    "type": "JOB_ON_JOB",
    "target": "EXTERNAL",
    "anyFrame": false,
    "active": true,
    "dependerJob": "myshow-shot002-comp",
    "dependerLayer": "",
    "dependerFrame": "",
    "dependOnJob": "myshow-shot001-render",
    "dependOnLayer": "",
    "dependOnFrame": ""
  }
}
```

### Satisfy Dependency

Mark a dependency as satisfied.

```http
POST /depend.DependInterface/Satisfy
```

**Request Body:**
```json
{
  "depend": {
    "id": "depend-id-ghi"
  }
}
```

### Unsatisfy Dependency

Mark a dependency as unsatisfied (reactivate).

```http
POST /depend.DependInterface/Unsatisfy
```

**Request Body:**
```json
{
  "depend": {
    "id": "depend-id-ghi"
  }
}
```

---

## Subscription Interface

Manage show subscriptions to allocations.

### Get Subscription

Get a subscription by ID.

```http
POST /subscription.SubscriptionInterface/Get
```

**Request Body:**
```json
{
  "id": "sub-id-jkl"
}
```

**Response:**
```json
{
  "subscription": {
    "id": "sub-id-jkl",
    "name": "myshow.cloud",
    "showName": "myshow",
    "facility": "aws-us-west",
    "allocationName": "cloud",
    "size": 50,
    "burst": 25,
    "reservedCores": 45,
    "reservedGpus": 8
  }
}
```

### Find Subscription

Find a subscription by name.

```http
POST /subscription.SubscriptionInterface/Find
```

**Request Body:**
```json
{
  "name": "myshow.cloud"
}
```

### Delete Subscription

Delete a subscription.

```http
POST /subscription.SubscriptionInterface/Delete
```

**Request Body:**
```json
{
  "subscription": {
    "id": "sub-id-jkl"
  }
}
```

### Set Subscription Size

Set the base size of a subscription.

```http
POST /subscription.SubscriptionInterface/SetSize
```

**Request Body:**
```json
{
  "subscription": {
    "id": "sub-id-jkl"
  },
  "newSize": 75
}
```

### Set Subscription Burst

Set the burst capacity of a subscription.

```http
POST /subscription.SubscriptionInterface/SetBurst
```

**Request Body:**
```json
{
  "subscription": {
    "id": "sub-id-jkl"
  },
  "burst": 50
}
```

---

## Limit Interface

Manage resource limits for layer types.

### Get All Limits

Get all limits in the system.

```http
POST /limit.LimitInterface/GetAll
```

**Request Body:**
```json
{}
```

**Response:**
```json
{
  "limits": [
    {
      "id": "limit-id-mno",
      "name": "nuke_license",
      "maxValue": 50,
      "currentRunning": 32
    }
  ]
}
```

### Get Limit

Get a limit by ID.

```http
POST /limit.LimitInterface/Get
```

**Request Body:**
```json
{
  "id": "limit-id-mno"
}
```

### Find Limit

Find a limit by name.

```http
POST /limit.LimitInterface/Find
```

**Request Body:**
```json
{
  "name": "nuke_license"
}
```

### Create Limit

Create a new resource limit.

```http
POST /limit.LimitInterface/Create
```

**Request Body:**
```json
{
  "name": "maya_license",
  "maxValue": 100
}
```

**Response:**
```json
{
  "limit": {
    "id": "limit-id-new",
    "name": "maya_license",
    "maxValue": 100,
    "currentRunning": 0
  }
}
```

### Delete Limit

Delete a limit.

```http
POST /limit.LimitInterface/Delete
```

**Request Body:**
```json
{
  "name": "maya_license"
}
```

### Set Limit Max Value

Update the maximum value for a limit.

```http
POST /limit.LimitInterface/SetMaxValue
```

**Request Body:**
```json
{
  "name": "nuke_license",
  "maxValue": 75
}
```

---

## Service Interface

Manage service definitions and requirements.

### Get Service

Get a service by name.

```http
POST /service.ServiceInterface/GetService
```

**Request Body:**
```json
{
  "name": "nuke"
}
```

**Response:**
```json
{
  "service": {
    "id": "service-id-pqr",
    "name": "nuke",
    "threadable": true,
    "minCores": 1,
    "maxCores": 8,
    "minMemory": 4294967296,
    "minGpuMemory": 0,
    "tags": ["nuke", "comp"],
    "timeout": 0,
    "timeoutLlu": 0,
    "minGpus": 0,
    "maxGpus": 0,
    "minMemoryIncrease": 0
  }
}
```

### Get Default Services

Get all default services.

```http
POST /service.ServiceInterface/GetDefaultServices
```

**Request Body:**
```json
{}
```

**Response:**
```json
{
  "services": {
    "services": [
      {
        "id": "service-id-pqr",
        "name": "nuke",
        "threadable": true,
        "minCores": 1,
        "maxCores": 8,
        "minMemory": 4294967296
      },
      {
        "id": "service-id-stu",
        "name": "maya",
        "threadable": false,
        "minCores": 1,
        "maxCores": 1,
        "minMemory": 2147483648
      }
    ]
  }
}
```

### Create Service

Create a new service definition.

```http
POST /service.ServiceInterface/CreateService
```

**Request Body:**
```json
{
  "data": {
    "name": "blender",
    "threadable": true,
    "minCores": 1,
    "maxCores": 16,
    "minMemory": 2147483648,
    "tags": ["blender", "render"]
  }
}
```

### Update Service

Update service properties.

```http
POST /service.ServiceInterface/Update
```

**Request Body:**
```json
{
  "service": {
    "id": "service-id-pqr",
    "name": "nuke",
    "minMemory": 8589934592
  }
}
```

### Delete Service

Delete a service definition.

```http
POST /service.ServiceInterface/Delete
```

**Request Body:**
```json
{
  "service": {
    "id": "service-id-pqr"
  }
}
```

---

## ServiceOverride Interface

Manage service overrides for specific shows.

### Update Service Override

Update a service override.

```http
POST /service.ServiceOverrideInterface/Update
```

**Request Body:**
```json
{
  "service": {
    "id": "override-id-vwx",
    "minMemory": 16777216000
  }
}
```

### Delete Service Override

Delete a service override.

```http
POST /service.ServiceOverrideInterface/Delete
```

**Request Body:**
```json
{
  "service": {
    "id": "override-id-vwx"
  }
}
```

---

## Task Interface

Manage tasks for shot priorities and department resources.

### Delete Task

Remove a task.

```http
POST /task.TaskInterface/Delete
```

**Request Body:**
```json
{
  "task": {
    "id": "task-id-yz1"
  }
}
```

### Set Task Min Cores

Set minimum cores for a task.

```http
POST /task.TaskInterface/SetMinCores
```

**Request Body:**
```json
{
  "task": {
    "id": "task-id-yz1"
  },
  "newMinCores": 16
}
```

**Response:**
```json
{}
```

### Clear Task Adjustments

Clear any core adjustments made to a task.

```http
POST /task.TaskInterface/ClearAdjustments
```

**Request Body:**
```json
{
  "task": {
    "id": "task-id-yz1"
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

## Tag Management

Tags are labels used to categorize and filter hosts and job layers in OpenCue. They enable resource allocation, job routing, and organizational workflows.

### Tag Use Cases

**Host Tags:**
- Hardware classification (gpu, high-memory, cpu-only)
- Location/facility identification (studio-a, datacenter-west)
- Department allocation (lighting-team, fx-team)
- Maintenance status (testing, production, maintenance)

**Layer Tags:**
- Software requirements (nuke, maya, blender, houdini)
- Render type (comp, lighting, fx, simulation, rendering)
- Priority classification (rush, standard, low-priority)
- Department routing (comp-dept, lighting-dept)

### Tag Operations Summary

| Operation | Host Endpoint | Layer Endpoint | Description |
|-----------|--------------|----------------|-------------|
| **Get Tags** | `GetHost` (returns tags field) | `GetLayer` (returns tags field) | Retrieve all tags |
| **Add Tags** | `AddTags` | N/A | Add tags (hosts only) |
| **Set Tags** | N/A | `SetTags` | Replace all tags (layers only) |
| **Remove Tags** | `RemoveTags` | N/A | Remove specific tags (hosts only) |
| **Rename Tag** | `RenameTag` | N/A | Rename a tag (hosts only) |

### Tag Management Workflows

#### Host Tagging Workflow

```bash
# 1. Get current host tags
curl -X POST http://localhost:8448/host.HostInterface/GetHost \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": "host-id-abc"}'
# Response includes: "tags": ["existing-tag"]

# 2. Add new tags
curl -X POST http://localhost:8448/host.HostInterface/AddTags \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "host": {"id": "host-id-abc"},
    "tags": ["gpu", "high-memory"]
  }'

# 3. Remove unwanted tags
curl -X POST http://localhost:8448/host.HostInterface/RemoveTags \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "host": {"id": "host-id-abc"},
    "tags": ["existing-tag"]
  }'

# 4. Rename a tag for standardization
curl -X POST http://localhost:8448/host.HostInterface/RenameTag \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "host": {"id": "host-id-abc"},
    "old_tag": "gpu",
    "new_tag": "nvidia-gpu"
  }'
```

#### Layer Tagging Workflow

```bash
# 1. Get current layer tags
curl -X POST http://localhost:8448/layer.LayerInterface/GetLayer \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": "layer-id-789"}'
# Response includes: "tags": ["existing-tag"]

# 2. Set new tags (replaces all existing tags)
curl -X POST http://localhost:8448/layer.LayerInterface/SetTags \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "layer": {"id": "layer-id-789"},
    "tags": ["nuke", "comp", "high-priority"]
  }'
```

### Best Practices

1. **Tag Naming Conventions:**
   - Use lowercase with hyphens (e.g., `high-memory`, not `HighMemory`)
   - Be consistent across the facility
   - Avoid special characters

2. **Tag Organization:**
   - Use a hierarchical scheme (e.g., `hw-gpu`, `hw-cpu`, `dept-lighting`)
   - Document tag meanings in a central location
   - Review and clean up unused tags regularly

3. **Security Considerations:**
   - Tags can affect job routing and resource allocation
   - Restrict tag modification permissions appropriately
   - Audit tag changes for compliance

4. **Integration with Job Routing:**
   - Use host tags to route jobs to specific hardware
   - Use layer tags to identify software requirements
   - Combine with filters for automated job management

### API Endpoints Reference

**Host Tag Endpoints:**
- Host tags: [Add Tags](#add-tags-to-host), [Remove Tags](#remove-tags-from-host), [Rename Tag](#rename-host-tag), [Get Tags](#get-host-tags)

**Layer Tag Endpoints:**
- Layer tags: [Set Tags](#set-layer-tags)

---

## What's next?

- [Using the REST API](/docs/user-guides/using-rest-api/) - Usage examples and integration
- [REST API Tutorial](/docs/tutorials/rest-api-tutorial/) - Step-by-step walkthrough
- [Deploying REST Gateway](/docs/getting-started/deploying-rest-gateway) - Deployment instructions
- [CueWeb Developer Guide](/docs/developer-guide/cueweb-development) - Integration examples with CueWeb