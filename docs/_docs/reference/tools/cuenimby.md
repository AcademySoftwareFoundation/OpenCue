---
title: "CueNIMBY - NIMBY CLI and System Tray Application"
nav_order: 67
parent: "Command Line Tools"
grand_parent: "Reference"
layout: default
date: 2025-10-01
description: >
  CueNimby is a cross-platform system tray application that provides user control over OpenCue's NIMBY (Not In My Back Yard) feature on workstations.
---

# CueNIMBY

### System tray application for workstation NIMBY control

---

CueNIMBY is a Qt-based cross-platform system tray application that provides user control over OpenCue's NIMBY (Not In My Back Yard) feature on workstations. Built with Qt6 for native look and feel, it features professional icons with the OpenCue logo, emoji hints (🔒❌⚠️🔧) for quick status recognition, and enhanced status detection.

## Synopsis

```
cuenimby [OPTIONS]
```

## Description

CueNIMBY provides a visual interface for monitoring and controlling workstation availability for rendering. It runs as a system tray application with professional icons featuring the OpenCue logo, sends desktop notifications with emoji hints (🔒❌⚠️🔧) for important events, provides direct access to CueGUI, and supports time-based scheduling for automatic state changes. CueNIMBY starts even when CueBot is unreachable and automatically reconnects when the connection is restored.

The application is designed to work alongside RQD's automatic NIMBY feature, providing users with enhanced status detection (CueBot connectivity, host registration, ping monitoring), visibility, and manual control while RQD handles automatic protection based on user activity.

## Options

### General options

`--version`
: Show CueNIMBY version and exit

`--help`, `-h`
: Show help message and exit

`--verbose`, `-v`
: Enable verbose (DEBUG) logging

### Connection options

`--config PATH`
: Path to configuration file
: Default: `~/.opencue/cuenimby.json`

`--cuebot-host HOST`
: Cuebot server hostname
: Overrides configuration file
: Can also be set via `CUEBOT_HOST` environment variable

`--cuebot-port PORT`
: Cuebot server port
: Overrides configuration file
: Can also be set via `CUEBOT_PORT` environment variable

`--hostname HOST`
: Hostname to monitor
: Default: local hostname (auto-detected)
: Useful for monitoring remote hosts

### Feature options

`--no-notifications`
: Disable desktop notifications
: Overrides configuration file setting

## Configuration

### Configuration file

CueNIMBY stores configuration in `~/.opencue/cuenimby.json`. The file is automatically created on first run with default values.

#### Example configuration

```json
{
  "cuebot_host": "cuebot.example.com",
  "cuebot_port": 8443,
  "hostname": null,
  "poll_interval": 5,
  "show_notifications": true,
  "notification_duration": 5,
  "scheduler_enabled": false,
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
    }
  }
}
```

### Configuration parameters

#### Connection settings

`cuebot_host` (string)
: Hostname or IP address of Cuebot server
: Default: `"localhost"` or value of `CUEBOT_HOST` environment variable

`cuebot_port` (integer)
: Port number for Cuebot gRPC service
: Default: `8443` or value of `CUEBOT_PORT` environment variable

`hostname` (string or null)
: Hostname to monitor
: Default: `null` (auto-detect local hostname)
: Set to monitor a different host

#### Polling settings

`poll_interval` (integer)
: How often to check host state, in seconds
: Default: `5`
: Recommended range: 5-60 seconds
: Lower values increase responsiveness but use more resources

#### Notification settings

`show_notifications` (boolean)
: Enable desktop notifications
: Default: `true`

`notification_duration` (integer)
: How long notifications stay visible, in seconds
: Default: `5`
: May not be honored by all platforms

#### Scheduler settings

`scheduler_enabled` (boolean)
: Enable time-based scheduler
: Default: `false`

`schedule` (object)
: Weekly schedule configuration
: Keys: day names (lowercase: monday, tuesday, etc.)
: Values: schedule entry objects

##### Schedule entry format

```json
{
  "start": "HH:MM",  // Start time (24-hour format)
  "end": "HH:MM",    // End time (24-hour format)
  "state": "disabled" // Desired state: "disabled" or "available"
}
```

During the specified time range, the host will be set to the specified state. Outside the range, the opposite state applies.

### Environment variables

`CUEBOT_HOST`
: Default Cuebot hostname
: Overridden by `--cuebot-host` or config file

`CUEBOT_PORT`
: Default Cuebot port
: Overridden by `--cuebot-port` or config file

## System tray interface

### Icon states

All icons feature the OpenCue logo for professional appearance and consistent visual identity.

| Icon File | Emoji | State | Description |
|-----------|-------|-------|-------------|
| `opencue-starting.png` | 🔄 | STARTING | Application is initializing |
| `opencue-available.png` | 🟢 | AVAILABLE | Host is unlocked and idle, ready to accept jobs |
| `opencue-working.png` | 🔴 | WORKING | Host is unlocked and actively rendering frames (red dot in center) |
| `opencue-disabled.png` | 🔴 | DISABLED | Host is manually locked via CueGUI or CueNIMBY |
| `opencue-disabled.png` | 🔒 | NIMBY_LOCKED | Host is locked by RQD NIMBY due to user activity |
| `opencue-disabled.png` | ❌ | HOST_DOWN | RQD is not running on the host |
| `opencue-error.png` | ❌ | CUEBOT_UNREACHABLE | Cannot connect to CueBot server |
| `opencue-error.png` | ❌ | NO_HOST | Machine not found on CueBot, check if RQD is running |
| `opencue-warning.png` | ⚠️ | HOST_LAGGING | Host ping above 60 second limit, check if RQD is running |
| `opencue-repair.png` | 🔧 | REPAIR | Host is under repair, check with tech team |
| `opencue-unknown.png` | ❓ | UNKNOWN | State cannot be determined |

#### Icon Gallery

Visual representation of all CueNIMBY icons:

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

### Menu options

**Available** (checkbox)
: Toggle host availability for rendering
: Checked: Host accepts rendering jobs
: Unchecked: Host rejects rendering jobs
: Disabled when CueBot is unreachable or host is not found

**Notifications** (checkbox)
: Toggle desktop notifications with emoji hints (🔒❌⚠️🔧)
: Changes persist to configuration file

**Scheduler** (checkbox)
: Toggle time-based scheduler
: Requires `schedule` configuration
: Changes persist to configuration file

**Launch CueGUI**
: Opens CueGUI application directly from the tray
: Disabled when CueGUI is not available
: Convenient access to full OpenCue interface

**Open Config File**
: Opens configuration file in your default editor
: File location: `~/.opencue/cuenimby.json`
: Changes take effect after application restart

**About**
: Show application information using Qt dialog
: Displays version, CueBot server address, monitored hostname, and description
: Enhanced with connection information for troubleshooting

**Quit**
: Exit CueNIMBY
: Host state in OpenCue remains unchanged

## Notifications

CueNIMBY sends desktop notifications for the following events:

### Frame started

Sent when a rendering frame starts on the monitored host.

```
OpenCue - Frame Started
Rendering: show_name/frame_name
```

### NIMBY locked

Sent when RQD locks the host due to user activity.

```
OpenCue - NIMBY Locked
Host locked due to user activity. Rendering stopped.
```

### NIMBY unlocked

Sent when RQD unlocks the host after idle period.

```
OpenCue - NIMBY Unlocked
Host available for rendering.
```

### Manual lock

Sent when user manually disables rendering.

```
OpenCue - Host Disabled
Host manually disabled for rendering.
```

### Manual unlock

Sent when user manually enables rendering.

```
OpenCue - Host Enabled
Host enabled for rendering.
```

### CueBot unreachable

Sent when CueNIMBY cannot connect to the CueBot server.

```
❌ OpenCue - CueBot Unreachable
Cannot connect to CueBot server. Check connection.
```

### Host not found

Sent when the monitored host is not registered with CueBot.

```
❌ OpenCue - Host Not Found
Machine not found on CueBot. Check if RQD is running.
```

### Host lagging

Sent when host ping exceeds 60 seconds.

```
⚠️ OpenCue - Host Lagging
Host ping above limit. Check if RQD is running.
```

### Host under repair

Sent when host is marked for repair.

```
🔧 OpenCue - Under Repair
Host is under repair. Contact tech team.
```

## Platform-specific features

### macOS

**Notifications:**
* Uses native Notification Center
* Requires notification permissions (granted automatically)
* Auto-detects and uses `terminal-notifier` if available (most reliable)
* Fallback chain: terminal-notifier → pync → osascript
* Recommended: Install terminal-notifier for best results
  ```bash
  brew install terminal-notifier
  ```
* Alternative: Install `pync` for enhanced notifications
  ```bash
  pip install pync
  ```
* Built-in fallback uses osascript (no additional install required)

**System tray:**
* Qt-based native system tray integration
* Icon appears in menu bar (top-right)
* Professional icons with OpenCue logo
* Native look and feel

### Windows

**Notifications:**
* Uses Windows 10+ toast notifications
* Requires Windows 10 or later
* Optional: Install `win10toast` for better support
  ```bash
  pip install win10toast
  ```

**System tray:**
* Qt-based native system tray integration
* Icon appears in notification area (bottom-right)
* May be hidden in overflow area
* Professional icons with OpenCue logo

**Auto-start:**
* Add to Startup folder: `Win+R`, type `shell:startup`
* Or use Task Scheduler for more control

### Linux

**Notifications:**
* Uses freedesktop notification standard
* Requires notification daemon (usually pre-installed)
* Optional: Install `notify2` for better integration
  ```bash
  pip install notify2
  ```

**System tray:**
* Qt-based native system tray integration
* Requires system tray support in desktop environment
* Professional icons with OpenCue logo
* Works on GNOME, KDE, XFCE, and other desktop environments

**Auto-start:**
* Add to autostart applications in desktop settings
* Or create systemd user service

## Integration

### With RQD

CueNIMBY is designed to work alongside RQD's NIMBY feature:

**RQD NIMBY (Automatic):**
* Monitors keyboard/mouse input
* Locks host on user activity
* Unlocks after idle period
* Kills running frames

**CueNIMBY (Manual + Visual):**
* Shows current state with professional icons featuring OpenCue logo
* Enhanced status detection (CueBot connectivity, host registration, ping monitoring)
* Allows manual override
* Sends notifications with emoji hints (🔒❌⚠️🔧)
* Provides scheduling
* Launches CueGUI directly from tray
* Starts even when CueBot is unreachable

Both can run simultaneously. CueNIMBY shows RQD's NIMBY_LOCKED state and allows manual control independent of RQD's automatic behavior. CueNIMBY provides proactive alerts for connection issues and host problems.

### With CueGUI

CueNIMBY's state changes are immediately visible in CueGUI:

* Host list shows lock state
* Lock state icon updates
* Host color indicates availability

Users can lock/unlock from either CueGUI or CueNIMBY - changes are synchronized through Cuebot.

### With OpenCue API

CueNIMBY uses the OpenCue Python API (pycue) to:

* Query host state
* Lock/unlock hosts
* Monitor running frames

API calls used:
```python
opencue.api.findHost(hostname)
host.lock()
host.unlock()
host.lockState()
host.getProcs()
```

## Examples

### Basic usage

Start with default settings:
```bash
cuenimby
```

### Connect to specific Cuebot

Using command-line options:
```bash
cuenimby --cuebot-host cuebot.prod.com --cuebot-port 8443
```

Using environment variables:
```bash
export CUEBOT_HOST=cuebot.prod.com
export CUEBOT_PORT=8443
cuenimby
```

### Monitor remote host

```bash
cuenimby --hostname render-node-05
```

### Debug mode

```bash
cuenimby --verbose
```

### Custom configuration

```bash
cuenimby --config /etc/opencue/cuenimby-prod.json
```

### Disable notifications

```bash
cuenimby --no-notifications
```

## Scheduler configuration examples

### Workweek protection

Disable rendering during business hours:

```json
{
  "scheduler_enabled": true,
  "schedule": {
    "monday": {"start": "09:00", "end": "18:00", "state": "disabled"},
    "tuesday": {"start": "09:00", "end": "18:00", "state": "disabled"},
    "wednesday": {"start": "09:00", "end": "18:00", "state": "disabled"},
    "thursday": {"start": "09:00", "end": "18:00", "state": "disabled"},
    "friday": {"start": "09:00", "end": "18:00", "state": "disabled"}
  }
}
```

Effect:
* 9am-6pm: Disabled (artist working)
* 6pm-9am: Available (overnight rendering)
* Weekends: Always available

### Lunch hour availability

Enable during lunch break:

```json
{
  "schedule": {
    "monday": {"start": "12:00", "end": "13:00", "state": "available"}
  }
}
```

### Split shift

Multiple periods per day:

```json
{
  "schedule": {
    "monday": [
      {"start": "09:00", "end": "12:00", "state": "disabled"},
      {"start": "13:00", "end": "18:00", "state": "disabled"}
    ]
  }
}
```

Note: Current version supports one period per day. Use most important period.

## Troubleshooting

### Common issues

**Icon doesn't appear**
* Linux: Ensure desktop environment supports system tray with Qt
* Windows: Check hidden icons in overflow area
* macOS: Check menu bar settings
* Verify Qt is installed

**Can't connect to Cuebot**
* CueNIMBY will now start even when CueBot is unreachable (shows ❌ icon)
* Check tray icon tooltip for specific error message
* Verify Cuebot hostname and port in `~/.opencue/cuenimby.json`
* Check network connectivity: `telnet cuebot.example.com 8443`
* Verify firewall rules allow gRPC traffic
* Run with `--verbose` for detailed connection errors
* CueNIMBY will automatically reconnect when CueBot becomes available

**Host not found**
* Shows ❌ "Machine not found on CueBot" status
* Verify RQD is running: `ps aux | grep rqd` (macOS/Linux)
* Check RQD logs for connection errors
* Verify hostname matches in CueBot (check CueGUI > Monitor Hosts)
* Use `--hostname` flag to specify exact hostname
* Ensure RQD successfully registered with CueBot

**Host lagging**
* Shows ⚠️ "Host ping above limit" warning
* Check if RQD is still running
* Verify network connection stability
* Review RQD logs for connection issues
* Consider restarting RQD
* Check CueBot server load

**Host under repair**
* Shows 🔧 "Under Repair" status
* Contact technical team for repair status
* Host administratively marked for maintenance
* No rendering will occur until cleared
* Check with administrators for resolution time

**Notifications don't work**
* macOS: Grant notification permissions. Install terminal-notifier: `brew install terminal-notifier`
* Windows: Check notification settings in Windows Settings
* Linux: Verify notification daemon is running: `ps aux | grep notification`
* Install platform-specific libraries (pync, win10toast, notify2)
* Check notifications are enabled in CueNIMBY menu

**State not updating**
* Check poll interval in configuration (may be too high)
* Verify host exists in Cuebot (check CueGUI > Monitor Hosts)
* Check hostname matches exactly (case-sensitive)
* Restart CueNIMBY with `--verbose` to see detailed status
* Check for connection issues (❌ or ⚠️ icons)

**Scheduler not triggering**
* Verify `scheduler_enabled: true` in configuration
* Check time format is HH:MM in 24-hour format
* Verify day names are lowercase (monday, tuesday, etc.)
* Check schedule logic matches desired behavior
* Run with `--verbose` to see scheduler activity

### Log files

CueNIMBY logs to stderr. To capture:

```bash
cuenimby --verbose 2>&1 | tee cuenimby.log
```

## See also

* [Desktop rendering control guide](/docs/other-guides/desktop-rendering-control) - Understanding desktop allocations, subscriptions, and NIMBY states
* [CueNIMBY user guide](/docs/user-guides/cuenimby-user-guide) - Complete usage guide
* [CueNIMBY tutorial](/docs/tutorials/cuenimby-tutorial) - Step-by-step walkthrough
* [NIMBY concept guide](/docs/concepts/nimby) - NIMBY system overview
* [Quick start: CueNIMBY](/docs/quick-starts/quick-start-cuenimby) - Quick start guide
