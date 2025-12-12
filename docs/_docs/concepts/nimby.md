---
title: "NIMBY"
nav_order: 14
parent: Concepts
layout: default
linkTitle: "NIMBY"
date: 2025-10-01
description: >
  Understanding NIMBY (Not In My Back Yard) for workstation rendering
---

# NIMBY

### Understanding NIMBY (Not In My Back Yard) for workstation rendering

---

NIMBY (Not In My Back Yard) is OpenCue's system for managing workstation availability for rendering. It allows organizations to leverage artist workstations as rendering resources while ensuring artists maintain control over their machines during active work.

## What is NIMBY?

NIMBY is a feature that automatically or manually controls whether a workstation accepts rendering jobs from OpenCue. When NIMBY is "locked," the workstation is unavailable for rendering. When "unlocked," the workstation can accept and process render jobs.

The name "Not In My Back Yard" reflects the computer user's perspective: they want rendering to happen somewhere else (not on their machine) when they're actively using it.

## NIMBY Components

OpenCue's NIMBY system consists of two complementary components:

### RQD NIMBY (Automatic)

The RQD (Render Queue Daemon) includes built-in NIMBY functionality that automatically detects user activity:

* **Input Detection**: Monitors keyboard and mouse activity using the `pynput` library
* **Automatic Locking**: Locks the host immediately when user input is detected
* **Automatic Unlocking**: Unlocks the host after a configurable idle period (default: 5 minutes)
* **Frame Termination**: Kills running frames when locking due to user activity

RQD NIMBY runs as part of the RQD process and requires no user interaction. It's enabled by default on workstations when RQD is configured with the `OVERRIDE_NIMBY` setting.

### CueNIMBY (Manual Control + Notifications)

CueNIMBY is a Qt-based system tray application that provides user control and feedback:

* **Visual State Indicator**: Professional icons with OpenCue logo showing current availability
* **Enhanced Status Detection**: Monitors CueBot connectivity, host registration, and ping times
* **Manual Control**: Users can toggle availability on/off via menu
* **Desktop Notifications**: Alerts with emoji hints (🔒❌⚠️🔧) for quick status recognition
* **Time-based Scheduling**: Automatic state changes based on schedule
* **Launch CueGUI**: Direct access to CueGUI from the tray menu
* **Resilient Connection**: Starts even when CueBot is unreachable, reconnects automatically
* **Cross-platform**: Works on macOS, Windows, and Linux with native look and feel

CueNIMBY runs independently of RQD and communicates with Cuebot via the OpenCue API.

## How NIMBY Works Together

Both NIMBY components can run simultaneously on the same workstation:

```
┌─────────────────────────────────────────────────┐
│                 Workstation                     │
│                                                 │
│  ┌──────────────┐         ┌──────────────┐      │
│  │     RQD      │         │  CueNIMBY    │      │
│  │   (Daemon)   │         │  (Tray App)  │      │
│  │              │         │              │      │
│  │  • Monitors  │         │  • Shows     │      │
│  │    input     │         │    state     │      │
│  │  • Auto lock │         │  • Manual    │      │
│  │  • Kills     │         │    control   │      │
│  │    frames    │         │  • Notifies  │      │
│  └──────┬───────┘         └──────┬───────┘      │
│         │                        │              │
│         └────────┬───────────────┘              │
│                  │                              │
└──────────────────┼──────────────────────────────┘
                   │
                   ▼
           ┌──────────────┐
           │    Cuebot    │
           │   (Server)   │
           └──────────────┘
```

**Interaction:**
1. RQD automatically locks when detecting user input
2. CueNIMBY shows the NIMBY_LOCKED state and sends notification
3. User can manually lock/unlock via CueNIMBY menu
4. Both changes are reflected in Cuebot and visible in CueGUI

## NIMBY States

Workstations can be in one of several states. CueNIMBY displays these with professional icons featuring the OpenCue logo:

| State | Icon | Emoji | Description |
|-------|------|-------|-------------|
| **STARTING** | `opencue-starting.png` | 🔄 | Application is initializing |
| **AVAILABLE** | `opencue-available.png` | 🟢 | Host is unlocked and idle, ready to accept jobs |
| **WORKING** | `opencue-working.png` | 🔴 | Host is unlocked and actively running frames (red dot in center) |
| **DISABLED** | `opencue-disabled.png` | 🔴 | Host is manually locked (via CueGUI or CueNIMBY) |
| **NIMBY_LOCKED** | `opencue-disabled.png` | 🔒 | Host is locked by NIMBY due to user activity |
| **HOST_DOWN** | `opencue-disabled.png` | ❌ | RQD is not running on the host |
| **NO_HOST** | `opencue-error.png` | ❌ | Machine not found on CueBot, check if RQD is running |
| **HOST_LAGGING** | `opencue-warning.png` | ⚠️ | Host ping above 60 second limit, check if RQD is running |
| **CUEBOT_UNREACHABLE** | `opencue-error.png` | ❌ | Cannot connect to CueBot server |
| **REPAIR** | `opencue-repair.png` | 🔧 | Host is under repair, check with tech team |
| **UNKNOWN** | `opencue-unknown.png` | ❓ | Unknown status |

### Icon Gallery

All CueNIMBY icons feature the OpenCue logo for professional appearance:

| Icon | File | Description |
|------|------|-------------|
| ![Available](/assets/images/cuenimby/icons/opencue-available.png) | `opencue-available.png` | Green - Ready for rendering |
| ![Working](/assets/images/cuenimby/icons/opencue-working.png) | `opencue-working.png` | Icon with red dot in center - Currently rendering |
| ![Disabled](/assets/images/cuenimby/icons/opencue-disabled.png) | `opencue-disabled.png` | Red - Locked/disabled |
| ![Error](/assets/images/cuenimby/icons/opencue-error.png) | `opencue-error.png` | Red X - Error/unreachable |
| ![Warning](/assets/images/cuenimby/icons/opencue-warning.png) | `opencue-warning.png` | Yellow - Warning/lagging |
| ![Repair](/assets/images/cuenimby/icons/opencue-repair.png) | `opencue-repair.png` | Orange - Under repair |
| ![Starting](/assets/images/cuenimby/icons/opencue-starting.png) | `opencue-starting.png` | Gray - Initializing |
| ![Unknown](/assets/images/cuenimby/icons/opencue-unknown.png) | `opencue-unknown.png` | Gray ? - Unknown |
| ![Default](/assets/images/cuenimby/icons/opencue-default.png) | `opencue-default.png` | Default fallback |

## NIMBY Configuration

### RQD NIMBY Configuration

Configure RQD NIMBY via environment variables or `rqd.conf`:

```bash
# Enable NIMBY on this workstation
export OVERRIDE_NIMBY=true

# Idle time before unlocking (seconds)
export MINIMUM_IDLE=300

# Check interval when locked (seconds)
export CHECK_INTERVAL_LOCKED=5
```

### CueNIMBY Configuration

Configure CueNIMBY via `~/.opencue/cuenimby.json`:

```json
{
  "cuebot_host": "cuebot.example.com",
  "cuebot_port": 8443,
  "poll_interval": 5,
  "show_notifications": true,
  "scheduler_enabled": true,
  "schedule": {
    "monday": {
      "start": "09:00",
      "end": "18:00",
      "state": "disabled"
    }
  }
}
```

For more details on NIMBY states and desktop rendering, see [Desktop rendering control guide](/docs/other-guides/desktop-rendering-control).

## Use Cases

### 1. Artist Workstations

**Scenario**: Artists need their machines during the day but want to contribute to rendering overnight.

**Solution**:
* Run RQD with NIMBY enabled for automatic protection
* Run CueNIMBY with scheduler: disabled 9am-6pm, available otherwise
* Artists see notifications when overnight renders start
* Artists can manually disable if needed

### 2. Floating Licenses

**Scenario**: Expensive software licenses should only run on machines that need them.

**Solution**:
* Configure jobs with `ignore_nimby=false` (default)
* Artists manually lock workstations when not using licensed software
* Licensed jobs only run on available machines

### 3. Development Machines

**Scenario**: Developers need full control but want to contribute when idle.

**Solution**:
* Run CueNIMBY only (no automatic RQD NIMBY)
* Developers manually toggle availability as needed
* Visual feedback shows when machine is rendering

### 4. Render Farm Expansion

**Scenario**: Studio needs extra capacity during crunch time.

**Solution**:
* Deploy RQD + CueNIMBY to all workstations
* Artists receive notifications when renders start
* Automatic detection prevents interference with active work
* Manual control allows artists to opt out if needed

## Best Practices

### For System Administrators

1. **Enable NIMBY on all workstations**: Prevents unexpected interference with artist work
2. **Set appropriate idle timeouts**: Balance between responsiveness and availability
3. **Communicate clearly**: Inform artists about workstation rendering policies
4. **Monitor usage**: Track NIMBY events to optimize configuration
5. **Test thoroughly**: Verify NIMBY behavior before deploying to production

### For Artists and Users

1. **Use CueNIMBY for visibility**: Know when your machine is rendering
2. **Configure schedules**: Automate availability based on your work hours
3. **Manual control**: Lock your machine before heavy local work
4. **Report issues**: Help improve NIMBY by reporting problems
5. **Be considerate**: Unlock machines when not in active use

## Technical Details

### Lock/Unlock API

Both RQD and CueNIMBY use the OpenCue API to control host lock state:

```python
import opencue

# Get host
host = opencue.api.findHost("workstation-01")

# Lock host
host.lock()

# Unlock host
host.unlock()

# Check lock state
if host.lockState() == opencue.api.host_pb2.NIMBY_LOCKED:
    print("Host is NIMBY locked")
```

### Frame Behavior

When NIMBY locks a host:

* **Running frames**: Killed with exit signal (unless `ignore_nimby=true`)
* **Queued frames**: Not dispatched to this host
* **Resources**: Released back to the pool
* **Status**: Updated in Cuebot and visible in CueGUI

### Ignore NIMBY Flag

Jobs can be configured to ignore NIMBY:

```python
import outline

# Create job that ignores NIMBY
job = outline.cuerun.createJob(
    show="myshow",
    shot="shot01",
    ignore_nimby=True  # Will run even on NIMBY-locked hosts
)
```

Use cases for `ignore_nimby=true`:
* Critical production renders
* Emergency fixes
* System maintenance tasks

## Troubleshooting

### NIMBY Not Working

**Symptoms**: RQD doesn't lock when user is active

**Solutions**:
1. Check `OVERRIDE_NIMBY` is set to `true`
2. Verify `pynput` is installed: `pip list | grep pynput`
3. Check RQD logs for NIMBY initialization errors
4. Ensure DISPLAY is set correctly (Linux)

### False Positives

**Symptoms**: NIMBY locks when user is not active

**Solutions**:
1. Check for background processes triggering input events
2. Adjust `MINIMUM_IDLE` to a higher value
3. Review system for spurious input device events

### CueNIMBY Connection Issues

**Symptoms**: CueNIMBY shows ❌ error icon or "CueBot unreachable" message

**Improved Behavior**: CueNIMBY now starts even when CueBot is unreachable and automatically reconnects when available.

**Solutions**:
1. Check the tray icon tooltip for specific error message
2. Verify CueBot hostname and port in `~/.opencue/cuenimby.json`
3. Check network connectivity and firewall rules
4. Ensure OpenCue client libraries are installed
5. Run with `--verbose` to see detailed errors
6. CueNIMBY will show clear visual feedback and automatically reconnect

### Host Not Found

**Symptoms**: CueNIMBY shows ❌ "Machine not found on CueBot"

**Solutions**:
1. Verify RQD is running on the machine
2. Check RQD logs for connection errors
3. Verify hostname matches in CueBot (check CueGUI > Monitor Hosts)
4. Use `--hostname` flag to specify exact hostname
5. Ensure RQD successfully registered with CueBot

### Host Lagging

**Symptoms**: CueNIMBY shows ⚠️ "Host ping above limit" warning

**Solutions**:
1. Check if RQD is still running
2. Verify network connection stability
3. Review RQD logs for connection issues
4. Consider restarting RQD if problem persists
5. Check CueBot server load

### Host Under Repair

**Symptoms**: CueNIMBY shows 🔧 "Under Repair" status

**Solutions**:
1. Contact your technical team for repair status
2. Host has been administratively marked for maintenance
3. No rendering will occur until repair state is cleared
4. Check with system administrators for estimated resolution

## Related guides

* [Desktop rendering control guide](/docs/other-guides/desktop-rendering-control) - Detailed guide on desktop rendering, allocations, and subscriptions
* [CueNIMBY user guide](/docs/user-guides/cuenimby-user-guide) - Complete CueNIMBY usage guide
* [Quick start: CueNIMBY](/docs/quick-starts/quick-start-cuenimby) - Get started quickly with CueNIMBY
