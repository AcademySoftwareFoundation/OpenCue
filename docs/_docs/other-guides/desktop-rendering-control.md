---
title: "Desktop rendering control"
nav_order: 48
parent: Other Guides
layout: default
linkTitle: "Desktop rendering control"
date: 2025-10-03
description: >
  Understanding and configuring desktop rendering in OpenCue
---

# Desktop rendering control

### Understanding and configuring desktop rendering in OpenCue

---

This guide explains how OpenCue manages desktop workstations for rendering, including allocations, subscriptions, and NIMBY states.

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

Desktop rendering allows organizations to leverage user workstations as rendering resources during idle time. OpenCue provides fine-grained control over when and how desktop resources are used through:

* **Allocations**: Logical groupings of hosts (e.g., `local.desktop`, `local.general`)
* **Subscriptions**: Show-specific allocation access and resource limits
* **NIMBY States**: Host availability and locking mechanisms
* **Priorities**: Resource allocation between different shows and jobs

This guide focuses on the `local.desktop` allocation and how to control rendering on workstations.

## What does "locked" mean?

When a host is **locked**, it becomes unavailable for rendering jobs in OpenCue. Understanding the different lock states is crucial for managing desktop rendering.

### Lock states

| State | Icon | Lock Type | Description |
|-------|------|-----------|-------------|
| **AVAILABLE** | 🟢 Green | Not locked | Host is idle and ready to accept jobs |
| **WORKING** | 🔵 Blue | Not locked | Host is actively running frames |
| **DISABLED** | 🔴 Red | Manual lock | User manually disabled rendering via CueGUI or CueNIMBY |
| **NIMBY_LOCKED** | 🟠 Orange | Automatic lock | RQD locked the host due to user activity (keyboard/mouse) |

### Lock behavior

When a host is locked (either DISABLED or NIMBY_LOCKED):

1. **No new jobs dispatched**: Cuebot will not send new frames to the host
2. **Running frames affected**:
   - If `ignore_nimby=false` (default): Running frames are killed
   - If `ignore_nimby=true`: Running frames continue to completion
3. **Resources released**: Host cores/memory become unavailable to OpenCue
4. **State visible**: Lock state is visible in CueGUI and other tools

### Lock vs. Unlock

**Locking a host**:
```python
import opencue

host = opencue.api.findHost("workstation-01")
host.lock()  # Manually lock the host
```

**Unlocking a host**:
```python
host.unlock()  # Unlock to allow rendering
```

**Checking lock state**:
```python
from opencue_proto import host_pb2

lock_state = host.lockState()
if lock_state == host_pb2.LockState.Value('NIMBY_LOCKED'):
    print("Host is NIMBY locked")
elif lock_state == host_pb2.LockState.Value('LOCKED'):
    print("Host is manually locked")
elif lock_state == host_pb2.LockState.Value('OPEN'):
    print("Host is unlocked")
```

## Desktop allocation architecture

### The `local.desktop` allocation

OpenCue uses a special allocation called `local.desktop` to manage desktop workstations separately from dedicated render nodes.

**Why separate desktop allocation?**

1. **Different resource profiles**: Desktops often have different hardware than render nodes
2. **Availability patterns**: Desktops are only available during idle time
3. **Priority management**: Desktop resources typically have lower priority
4. **User control**: Artists need visibility and control over their machines
5. **License management**: Some software licenses should only run on specific machines

### Architecture diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Cuebot                              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Allocations                        │   │
│  │                                                     │   │
│  │  ┌───────────────┐      ┌──────────────────┐      │   │
│  │  │ local.general │      │  local.desktop   │      │   │
│  │  │               │      │                  │      │   │
│  │  │  • node-001   │      │  • workstation-01│      │   │
│  │  │  • node-002   │      │  • workstation-02│      │   │
│  │  │  • node-003   │      │  • workstation-03│      │   │
│  │  │  • ...        │      │  • ...           │      │   │
│  │  └───────────────┘      └──────────────────┘      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Show Subscriptions                   │   │
│  │                                                     │   │
│  │  Show: "feature_film"                              │   │
│  │  ├─ local.general:  size=100, burst=200            │   │
│  │  └─ local.desktop:  size=0,   burst=0  [DISABLED]  │   │
│  │                                                     │   │
│  │  Show: "commercial"                                │   │
│  │  ├─ local.general:  size=50,  burst=100            │   │
│  │  └─ local.desktop:  size=10,  burst=20  [ENABLED]  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Host assignment to allocations

Hosts are assigned to allocations based on configuration:

**RQD configuration** (`rqd.conf` or environment variables):
```bash
# Assign this host to local.desktop allocation
# Note: Set DEFAULT_FACILITY to "local" and the host will be assigned
# to the default allocation (local.general) unless specified otherwise
export DEFAULT_FACILITY="local"
```

**CueGUI** (for administrators):
1. Open CueGUI
2. Navigate to Monitor Hosts
3. Right-click host
4. Edit > Allocation
5. Select `local.desktop`

## Show subscriptions

Shows access allocations through **subscriptions**. Each subscription defines how many resources a show can use from an allocation.

### Subscription parameters

| Parameter | Description | Desktop Typical |
|-----------|-------------|-----------------|
| **Size** | Guaranteed minimum cores | 0-20 |
| **Burst** | Maximum cores when available | 0-50 |
| **Priority** | Scheduling priority within allocation | 1-10 (lower) |

### Subscription size vs. burst

**Size**: Guaranteed minimum resources
* Show will always get at least this many cores (if available)
* Cuebot reserves these resources for the show
* Higher size = more guaranteed throughput

**Burst**: Maximum resources when available
* Show can use up to this many cores when allocation is idle
* Opportunistic resource usage
* Higher burst = better utilization of idle capacity

**Example**:
```
Show: "myshow"
Allocation: local.desktop
  - Size: 10 cores
  - Burst: 50 cores

Behavior:
  - Guaranteed at least 10 cores (if 10 desktop cores are unlocked)
  - Can use up to 50 cores when other shows aren't using them
  - If only 5 cores available, gets 5 cores
  - If 100 cores available and no competition, gets 50 cores
```

### Controlling desktop rendering

#### Disable desktop rendering for a show

Set subscription size and burst to zero:

**Using CueGUI**:
1. Open CueGUI
2. Navigate to Shows
3. Right-click show
4. Subscriptions
5. Find `local.desktop` subscription
6. Set size=0, burst=0

**Using PyCue**:
```python
import opencue

show = opencue.api.findShow("myshow")
for sub in show.getSubscriptions():
    if sub.data.allocation_name == "local.desktop":
        sub.setSize(0)
        sub.setBurst(0)
```

**Using CueAdmin (command-line)**:
```bash
cueadmin -size myshow local.desktop 0
cueadmin -burst myshow local.desktop 0
```

#### Enable desktop rendering for a show

Set appropriate size and burst values:

**Conservative** (10 cores guaranteed, up to 20):
```bash
cueadmin -size myshow local.desktop 10
cueadmin -burst myshow local.desktop 20
```

**Aggressive** (0 guaranteed, up to 100 opportunistic):
```bash
cueadmin -size myshow local.desktop 0
cueadmin -burst myshow local.desktop 100
```

**Balanced** (20 guaranteed, up to 50):
```bash
cueadmin -size myshow local.desktop 20
cueadmin -burst myshow local.desktop 50
```

#### Dynamic control during production

Shows often need different desktop access at different times:

**Normal operation** (no desktop rendering):
```bash
cueadmin -size myshow local.desktop 0
cueadmin -burst myshow local.desktop 0
```

**Crunch time** (enable desktop rendering):
```bash
cueadmin -size myshow local.desktop 20
cueadmin -burst myshow local.desktop 100
```

**Overnight only** (use CueNIMBY scheduler):
* Set subscription to allow desktop rendering
* Configure CueNIMBY scheduler on workstations
* Workstations auto-disable during work hours

## Practical workflows

### Workflow 1: Production show with emergency deadline

**Scenario**: Feature film needs to complete final renders by end of week.

**Solution**:
1. **Enable desktop rendering**:
   ```bash
   cueadmin -size feature_film local.desktop 50
   cueadmin -burst feature_film local.desktop 200
   ```

2. **Notify artists**:
   * Send email explaining desktop rendering will be enabled
   * Artists can use CueNIMBY to manually lock machines if needed
   * RQD NIMBY provides automatic protection

3. **Monitor usage**:
   * Check CueGUI to see desktop utilization
   * Verify jobs are using desktop resources
   * Monitor for user complaints

4. **Disable after deadline**:
   ```bash
   cueadmin -size feature_film local.desktop 0
   cueadmin -burst feature_film local.desktop 0
   ```

### Workflow 2: Scheduled overnight rendering

**Scenario**: Allow rendering on desktops only during off-hours (6pm-9am weekdays, all weekend).

**Solution**:
1. **Enable desktop rendering in OpenCue**:
   ```bash
   cueadmin -size myshow local.desktop 0
   cueadmin -burst myshow local.desktop 100
   ```

2. **Configure CueNIMBY scheduler** on each workstation (`~/.opencue/cuenimby.json`):
   ```json
   {
     "scheduler_enabled": true,
     "schedule": {
       "monday": {
         "start": "09:00",
         "end": "18:00",
         "state": "disabled"
       },
       "tuesday": {
         "start": "09:00",
         "end": "18:00",
         "state": "disabled"
       },
       "wednesday": {
         "start": "09:00",
         "end": "18:00",
         "state": "disabled"
       },
       "thursday": {
         "start": "09:00",
         "end": "18:00",
         "state": "disabled"
       },
       "friday": {
         "start": "09:00",
         "end": "18:00",
         "state": "disabled"
       }
     }
   }
   ```

3. **Result**:
   * 9am-6pm Mon-Fri: Workstations locked (disabled)
   * 6pm-9am weekdays + all weekend: Workstations available
   * Users receive notifications when renders start
   * Users can override schedule manually if needed

### Workflow 3: Department-specific rendering

**Scenario**: Only allow specific departments' machines to render.

**Solution**:
1. **Create department allocations**:
   ```bash
   cueadmin -create-allocation local.lighting
   cueadmin -create-allocation local.fx
   cueadmin -create-allocation local.anim
   ```

2. **Assign hosts to department allocations**:
   * Configure RQD on each machine with appropriate facility tag
   * Or use CueGUI to assign hosts to allocations

3. **Configure show subscriptions**:
   ```bash
   # Lighting show only uses lighting workstations
   cueadmin -subscribe myshow local.lighting
   cueadmin -size myshow local.lighting 0
   cueadmin -burst myshow local.lighting 50

   # FX show uses both FX and lighting workstations
   cueadmin -subscribe myshow local.fx
   cueadmin -size myshow local.fx 0
   cueadmin -burst myshow local.fx 30

   cueadmin -subscribe myshow local.lighting
   cueadmin -size myshow local.lighting 0
   cueadmin -burst myshow local.lighting 20
   ```

### Workflow 4: License-aware rendering

**Scenario**: Expensive software licenses should only run on specific machines.

**Solution**:
1. **Tag hosts with license info**:
   ```bash
   cueadmin -tag workstation-01 has_license_houdini
   cueadmin -tag workstation-02 has_license_houdini
   ```

2. **Configure job to require tag**:
   ```python
   import outline

   job = outline.cuerun.createJob(
       show="myshow",
       shot="shot01",
       tags=["has_license_houdini"]
   )
   ```

3. **Result**:
   * Jobs only run on tagged machines
   * Other workstations remain available for non-licensed work
   * Optimal license utilization

## Integration with NIMBY

Desktop rendering works in conjunction with NIMBY for user control:

### Two-layer control

**Layer 1: Show Subscriptions** (Administrator control)
* Controls whether show can access desktop allocation
* Sets resource limits
* Managed via CueAdmin/CueGUI

**Layer 2: NIMBY States** (User/automatic control)
* Controls whether individual hosts accept jobs
* Provides user visibility and control
* Managed via RQD automatic detection and CueNIMBY manual control

### Combined behavior

```
Can job run on desktop host?

1. Show subscription check:
   ├─ Is local.desktop subscription size > 0 OR burst > 0?
   │  ├─ NO  → Job cannot use desktop hosts
   │  └─ YES → Continue to step 2

2. Host availability check:
   ├─ Is host in AVAILABLE or WORKING state?
   │  ├─ NO  → Job cannot run on this host
   │  └─ YES → Continue to step 3

3. Resource availability check:
   ├─ Are cores/memory available?
   │  ├─ NO  → Job queued until resources available
   │  └─ YES → Job dispatched to host
```

### Example scenarios

**Scenario A**: Show enabled for desktop, host available
* Show subscription: size=10, burst=50
* Host state: AVAILABLE
* **Result**: ✅ Jobs can run

**Scenario B**: Show enabled for desktop, host locked
* Show subscription: size=10, burst=50
* Host state: NIMBY_LOCKED (user is working)
* **Result**: ❌ Jobs cannot run on this host

**Scenario C**: Show disabled for desktop, host available
* Show subscription: size=0, burst=0
* Host state: AVAILABLE
* **Result**: ❌ Jobs cannot use desktop allocation

**Scenario D**: Show enabled, user manually locked
* Show subscription: size=10, burst=50
* Host state: DISABLED (via CueNIMBY)
* **Result**: ❌ Jobs cannot run on this host

## Monitoring and reporting

### Check current desktop usage

**Using CueGUI**:
1. Monitor > Hosts
2. Filter by allocation: `local.desktop`
3. View current state and running frames

**Using CueAdmin**:
```bash
# List all desktop hosts
cueadmin -lh -allocation local.desktop
```

**Using PyCue**:
```python
import opencue

# Get all desktop hosts
hosts = opencue.api.getHosts(alloc=["local.desktop"])

for host in hosts:
    print(f"{host.name()}: {host.state()}")

# Get running frames on desktop
for host in hosts:
    procs = host.getProcs()
    if procs:
        print(f"{host.name()} running {len(procs)} frames")
```

### Check show subscription status

**Using CueGUI**:
- Check list of subscriptions by show on CueGUI > CueCommander > Subscriptions

**Using PyCue**:
```python
import opencue

# First, list available shows
shows = opencue.api.getShows()
print("Available shows:")
for show in shows:
    print(f"  - {show.name()}")

# Then check subscriptions for a specific show
show = opencue.api.findShow("your_show_name")  # Replace with actual show name
for sub in show.getSubscriptions():
    if "local.desktop" in sub.data.allocation_name:
        print(f"\nAllocation: {sub.data.allocation_name}")
        print(f"  Size: {sub.data.size}")
        print(f"  Burst: {sub.data.burst}")
        print(f"  Priority: {sub.data.priority}")
```

### Generate desktop usage report

```python
import opencue

def desktop_usage_report():
    """Generate report of desktop allocation usage."""

    # Get all desktop hosts
    hosts = opencue.api.getHosts(alloc=["local.desktop"])

    stats = {
        'total_hosts': len(hosts),
        'available': 0,
        'working': 0,
        'disabled': 0,
        'nimby_locked': 0,
        'total_cores': 0,
        'used_cores': 0,
        'frames_running': 0,
    }

    for host in hosts:
        stats['total_cores'] += host.data.cores

        state = host.state()
        if state == 'UP':
            stats['available'] += 1
        elif state == 'NIMBY_LOCKED':
            stats['nimby_locked'] += 1
        elif state == 'LOCKED':
            stats['disabled'] += 1

        procs = host.getProcs()
        if procs:
            stats['working'] += 1
            stats['frames_running'] += len(procs)
            stats['used_cores'] += len(procs)

    # Print report
    print("Desktop Allocation Usage Report")
    print("=" * 50)
    print(f"Total Hosts: {stats['total_hosts']}")
    print(f"  Available: {stats['available']}")
    print(f"  Working: {stats['working']}")
    print(f"  NIMBY Locked: {stats['nimby_locked']}")
    print(f"  Manually Disabled: {stats['disabled']}")
    print()
    print(f"Total Cores: {stats['total_cores']}")
    print(f"Used Cores: {stats['used_cores']}")

    if stats['total_cores'] > 0:
        utilization = stats['used_cores'] / stats['total_cores'] * 100
        print(f"Utilization: {utilization:.1f}%")
    else:
        print("Utilization: N/A (no hosts found)")

    print()
    print(f"Frames Running: {stats['frames_running']}")

    return stats

# Run report
desktop_usage_report()
```

## Troubleshooting

### Jobs not running on desktops

**Check 1: Show subscription**
* Check list of subscriptions by show on CueGUI > CueCommander > Subscriptions
* Verify `local.desktop` subscription exists
* Verify size > 0 OR burst > 0

**Check 2: Host availability**
```bash
cueadmin -lh -allocation local.desktop
```
* Verify hosts are in AVAILABLE or WORKING state
* Check for NIMBY_LOCKED or DISABLED hosts

**Check 3: Host allocation**
```bash
cueadmin -lh workstation-01
```
* Verify host is actually in `local.desktop` allocation

**Check 4: Job configuration**
* Verify job doesn't have conflicting service requirements
* Check job isn't limited to different allocation
* Verify job priority allows desktop resources

### Too many desktop jobs running

**Solution 1: Reduce burst limit**
```bash
cueadmin -burst myshow local.desktop 20  # Reduce from higher value
```

**Solution 2: Reduce priority**
```bash
cueadmin -priority myshow local.desktop 1  # Lower priority
```

**Solution 3: Disable temporarily**
```bash
cueadmin -size myshow local.desktop 0
cueadmin -burst myshow local.desktop 0
```

### Desktop hosts constantly NIMBY locked

**Causes**:
* Users are actively working (expected)
* RQD NIMBY sensitivity too high
* Spurious input events (mice, keyboards)

**Solutions**:
1. **Increase NIMBY idle timeout**:
   ```bash
   export MINIMUM_IDLE=600  # 10 minutes instead of 5
   ```

2. **Check for spurious events**:
   * Disconnect unused input devices
   * Check for background processes generating events

3. **Use CueNIMBY scheduler**:
   * Configure specific hours for rendering
   * Users won't be interrupted during work hours

### Users complaining about rendering on machines

**Immediate action**:
1. Tell users to open CueNIMBY and uncheck "Available"
2. Or manually lock via CueGUI: Right-click host > Lock

**Long-term solution**:
1. Deploy CueNIMBY to all workstations
2. Enable RQD NIMBY for automatic protection
3. Configure appropriate schedules
4. Communicate desktop rendering policy clearly

## Best practices

### For administrators

1. **Start conservatively**: Begin with small size/burst values
2. **Monitor closely**: Watch desktop usage and user feedback
3. **Communicate clearly**: Inform users about desktop rendering policies
4. **Provide tools**: Deploy CueNIMBY for user visibility and control
5. **Use scheduling**: Limit desktop rendering to off-hours when possible
6. **Set priorities**: Desktop allocations should typically have lower priority
7. **Test thoroughly**: Verify NIMBY behavior before enabling widely
8. **Document policies**: Clear guidelines for users and operators

### For production teams

1. **Plan ahead**: Enable desktop rendering before crunch, not during
2. **Communicate**: Inform artists when desktop rendering is enabled
3. **Set expectations**: Explain impact and duration
4. **Provide support**: Help artists configure CueNIMBY
5. **Monitor impact**: Watch for complaints or performance issues
6. **Clean up**: Disable desktop rendering when deadline passes

### For users/artists

1. **Use CueNIMBY**: Install and run for visibility and control
2. **Configure schedules**: Match your work hours
3. **Manual override**: Lock machine before intensive local work
4. **Report issues**: Help improve the system
5. **Be considerate**: Unlock when not actively working

## Related documentation

* [NIMBY concept guide](/docs/concepts/nimby) - Overview of NIMBY system
* [CueNIMBY user guide](/docs/user-guides/cuenimby-user-guide) - Complete CueNIMBY usage guide
* [Quick start: CueNIMBY](/docs/quick-starts/quick-start-cuenimby) - Get started quickly
* [Customizing RQD](/docs/other-guides/customizing-rqd) - RQD NIMBY configuration
