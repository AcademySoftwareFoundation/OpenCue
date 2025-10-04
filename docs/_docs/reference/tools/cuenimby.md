---
title: "CueNIMBY - NIMBY CLI and System Tray Application"
nav_order: 61
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

CueNIMBY is a cross-platform system tray application that provides user control over OpenCue's NIMBY (Not In My Back Yard) feature on workstations.

## Synopsis

```
cuenimby [OPTIONS]
```

## Description

CueNIMBY provides a visual interface for monitoring and controlling workstation availability for rendering. It runs as a system tray application, displays state through color-coded icons, sends desktop notifications for important events, and supports time-based scheduling for automatic state changes.

The application is designed to work alongside RQD's automatic NIMBY feature, providing users with visibility and manual control while RQD handles automatic protection based on user activity.

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

| Icon color | State | Description |
|------------|-------|-------------|
| 🟢 Green | AVAILABLE | Host is unlocked and idle |
| 🔵 Blue | WORKING | Host is unlocked and rendering |
| 🔴 Red | DISABLED | Host is manually locked |
| 🟠 Orange | NIMBY_LOCKED | Host is locked by RQD NIMBY |
| ⚫ Gray | UNKNOWN | State cannot be determined |

### Menu options

**Available** (checkbox)
: Toggle host availability for rendering
: Checked: Host accepts rendering jobs
: Unchecked: Host rejects rendering jobs

**Notifications** (checkbox)
: Toggle desktop notifications
: Changes persist to configuration file

**Scheduler** (checkbox)
: Toggle time-based scheduler
: Requires `schedule` configuration
: Changes persist to configuration file

**About**
: Show application information using native platform dialog
: Displays version, monitored host, and description
: Uses AppleScript (macOS), MessageBox (Windows), or zenity/kdialog (Linux)
: Works regardless of notification settings

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
* Icon appears in menu bar (top-right)
* Follows system dark/light mode

### Windows

**Notifications:**
* Uses Windows 10+ toast notifications
* Requires Windows 10 or later
* Optional: Install `win10toast` for better support
  ```bash
  pip install win10toast
  ```

**System tray:**
* Icon appears in notification area (bottom-right)
* May be hidden in overflow area

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
* Requires system tray support in desktop environment
* Some environments need AppIndicator:
  ```bash
  sudo apt-get install gir1.2-appindicator3-0.1
  ```

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
* Shows current state
* Allows manual override
* Sends notifications
* Provides scheduling

Both can run simultaneously. CueNIMBY shows RQD's NIMBY_LOCKED state and allows manual control independent of RQD's automatic behavior.

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
* Linux: Install AppIndicator support
* Windows: Check hidden icons
* macOS: Check menu bar settings

**Can't connect to Cuebot**
* Verify Cuebot hostname and port
* Check network connectivity
* Verify firewall rules
* Run with `--verbose` for details

**Notifications don't work**
* macOS: Grant notification permissions
* Windows: Check notification settings
* Linux: Verify notification daemon
* Install platform-specific libraries

**State not updating**
* Check poll interval (may be too high)
* Verify host exists in Cuebot
* Check hostname matches
* Restart CueNIMBY

**Scheduler not triggering**
* Verify `scheduler_enabled: true`
* Check time format (HH:MM, 24-hour)
* Verify day names (lowercase)
* Check schedule logic

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
