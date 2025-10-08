---
title: "CueNIMBY User Guide"
nav_order: 35
parent: User Guides
layout: default
linkTitle: "CueNIMBY user guide"
date: 2025-10-01
description: >
  Complete guide to using CueNIMBY for workstation control
---

# CueNIMBY user guide

### Complete guide to using CueNIMBY for workstation control

---

This guide covers all aspects of using CueNIMBY, OpenCue's system tray application for workstation NIMBY control.

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

CueNIMBY is a cross-platform system tray application that gives you control over your workstation's availability for rendering. It provides:

* **Visual feedback**: Color-coded icon showing current state
* **Manual control**: Toggle rendering on/off with a single click
* **Desktop notifications**: Alerts when jobs start or state changes
* **Time-based scheduling**: Automatic state changes based on your schedule
* **Cross-platform support**: Works on macOS, Windows, and Linux

## Installation

### Requirements

* Python 3.7 or later
* OpenCue client libraries (pycue)
* Access to a Cuebot server

### Installing from source

```bash
cd OpenCue/cuenimby
pip install .
```

### Verifying installation

```bash
cuenimby --version
```

## Getting started

### Starting CueNIMBY

Launch CueNIMBY from the command line:

```bash
cuenimby
```

The application starts in the background and adds an icon to your system tray.

### Connecting to Cuebot

#### Using command-line options

```bash
cuenimby --cuebot-host cuebot.example.com --cuebot-port 8443
```

#### Using environment variables

```bash
export CUEBOT_HOST=cuebot.example.com
export CUEBOT_PORT=8443
cuenimby
```

#### Using configuration file

Create or edit `~/.opencue/cuenimby.json`:

```json
{
  "cuebot_host": "cuebot.example.com",
  "cuebot_port": 8443
}
```

## Understanding the tray icon

The CueNIMBY tray icon uses colors to indicate your workstation's current state:

| Icon | State | Description |
|------|-------|-------------|
| 🟢 **Green** | Available | Your machine is idle and ready to accept rendering jobs |
| 🔵 **Blue** | Working | Your machine is currently rendering a frame |
| 🔴 **Red** | Disabled | You've manually disabled rendering |
| 🟠 **Orange** | NIMBY Locked | RQD has locked the machine due to user activity |
| ⚫ **Gray** | Unknown | Cannot determine state (connection issue) |

### State transitions

```
Available ⟷ Working
    ↕          ↕
Disabled ⟷ NIMBY Locked
```

* **Available ↔ Working**: Happens automatically when jobs start/finish
* **Available ↔ Disabled**: You control via the menu
* **Any → NIMBY Locked**: RQD detects user activity
* **NIMBY Locked → Available**: RQD detects idle period

## Using the menu

Right-click the CueNIMBY icon to open the menu.

### Available (checkbox)

Controls whether your machine accepts rendering jobs.

**Checked** (🟢/🔵): Machine is available for rendering
* Jobs can be dispatched to your machine
* Currently running jobs continue

**Unchecked** (🔴): Machine is disabled for rendering
* No new jobs will be dispatched
* Currently running jobs are killed (unless they have `ignore_nimby=true`)

**To toggle**:
1. Right-click the tray icon
2. Click "Available" to check/uncheck

### Notifications (checkbox)

Controls desktop notifications.

**Checked**: Notifications enabled
* Alert when a rendering job starts
* Alert when NIMBY locks/unlocks
* Alert when you manually change availability

**Unchecked**: Notifications disabled
* No desktop alerts
* Icon still updates to show state

**To toggle**:
1. Right-click the tray icon
2. Click "Notifications" to check/uncheck

### Scheduler (checkbox)

Controls time-based automatic state changes.

**Checked**: Scheduler active
* Your machine automatically changes state based on schedule
* Example: Disabled 9am-6pm Mon-Fri, available otherwise

**Unchecked**: Scheduler inactive
* No automatic state changes
* You maintain full manual control

**To toggle**:
1. Right-click the tray icon
2. Click "Scheduler" to check/uncheck

See [Scheduler](#scheduler) section for configuration details.

### About

Shows application information using native platform dialog:
* CueNIMBY version
* Host being monitored
* Brief description

The About dialog uses native platform dialogs (AppleScript on macOS, MessageBox on Windows, zenity/kdialog on Linux) and works regardless of notification settings.

### Quit

Exits CueNIMBY. Your machine's state in OpenCue remains unchanged.

## Desktop notifications

CueNIMBY sends desktop notifications for important events.

### Notification types

#### Frame Started
```
OpenCue - Frame Started
Rendering: myshow_ep101/frame_0001
```
Sent when a rendering job begins on your machine.

#### NIMBY Locked
```
OpenCue - NIMBY Locked
Host locked due to user activity. Rendering stopped.
```
Sent when RQD detects user activity and locks the machine.

#### NIMBY Unlocked
```
OpenCue - NIMBY Unlocked
Host available for rendering.
```
Sent when RQD unlocks after an idle period.

#### Host Disabled
```
OpenCue - Host Disabled
Host manually disabled for rendering.
```
Sent when you manually disable rendering.

#### Host Enabled
```
OpenCue - Host Enabled
Host enabled for rendering.
```
Sent when you manually enable rendering.

### Platform-specific behavior

**macOS:**
* Uses native Notification Center
* Notifications appear in top-right corner
* Requires notification permissions (granted on first notification)
* Auto-detects and uses `terminal-notifier` if available (most reliable)
* Fallback chain: terminal-notifier → pync → osascript
* For best results, install terminal-notifier: `brew install terminal-notifier`

**Windows:**
* Uses Windows 10+ toast notifications
* Notifications appear in bottom-right corner
* Respects Windows notification settings

**Linux:**
* Uses freedesktop notification standard
* Appearance depends on desktop environment
* Requires notification daemon (usually pre-installed)

### Disabling notifications

**Temporarily**:
1. Right-click tray icon
2. Uncheck "Notifications"

**Permanently**:
Edit `~/.opencue/cuenimby.json`:
```json
{
  "show_notifications": false
}
```

## Scheduler

The scheduler automatically controls your machine's availability based on time and day of week.

### How scheduling works

1. Define time periods for each day of the week
2. Specify desired state during those periods
3. CueNIMBY automatically changes state based on current time
4. Outside scheduled periods, opposite state applies

### Configuration

Edit `~/.opencue/cuenimby.json`:

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

### Schedule format

Each day entry contains:

* **start**: Start time in HH:MM format (24-hour)
* **end**: End time in HH:MM format (24-hour)
* **state**: Desired state during this period
  * `"disabled"`: Machine will be locked
  * `"available"`: Machine will be unlocked

### Schedule examples

**Example 1: Workday protection**

Disable rendering during business hours:
```json
"monday": {
  "start": "09:00",
  "end": "18:00",
  "state": "disabled"
}
```
* 9am-6pm: Disabled
* 6pm-9am: Available

**Example 2: Lunch hour**

Enable rendering during lunch:
```json
"monday": {
  "start": "12:00",
  "end": "13:00",
  "state": "available"
}
```

**Example 3: Night shift**

Disable during night shift:
```json
"monday": {
  "start": "22:00",
  "end": "06:00",
  "state": "disabled"
}
```

**Example 4: Weekend availability**

No entry = always use manual control on weekends.

### Enabling the scheduler

**Via menu**:
1. Configure schedule in config file
2. Right-click tray icon
3. Check "Scheduler"

**Via config file**:
```json
{
  "scheduler_enabled": true
}
```

### Scheduler behavior

* Checks schedule every minute
* Changes state if needed
* Shows notification when changing state
* Manual changes override scheduler until next check
* Disabled days use manual control

## Configuration

### Configuration file location

```
~/.opencue/cuenimby.json
```

On first run, CueNIMBY creates this file with default values.

### Full configuration example

```json
{
  "cuebot_host": "cuebot.example.com",
  "cuebot_port": 8443,
  "hostname": null,
  "poll_interval": 5,
  "show_notifications": true,
  "notification_duration": 5,
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

### Configuration options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `cuebot_host` | string | "localhost" | Cuebot server hostname |
| `cuebot_port` | integer | 8443 | Cuebot server port |
| `hostname` | string/null | null | Host to monitor (null = auto-detect) |
| `poll_interval` | integer | 5 | State check interval (seconds) |
| `show_notifications` | boolean | true | Enable desktop notifications |
| `notification_duration` | integer | 5 | Notification display time (seconds) |
| `scheduler_enabled` | boolean | false | Enable time-based scheduler |
| `schedule` | object | {} | Weekly schedule configuration |

### Reloading configuration

Changes to the config file take effect:
* Immediately for most settings
* After restart for connection settings

To apply connection changes:
1. Quit CueNIMBY
2. Edit config file
3. Restart CueNIMBY

## Command-line options

### Basic usage

```bash
cuenimby [OPTIONS]
```

### Available options

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `--config PATH` | Path to config file |
| `--cuebot-host HOST` | Cuebot hostname (overrides config) |
| `--cuebot-port PORT` | Cuebot port (overrides config) |
| `--hostname HOST` | Host to monitor (default: local) |
| `--no-notifications` | Disable notifications |
| `--verbose`, `-v` | Enable verbose logging |

### Examples

**Connect to specific Cuebot**:
```bash
cuenimby --cuebot-host cuebot.prod.example.com --cuebot-port 8443
```

**Monitor different host**:
```bash
cuenimby --hostname workstation-02
```

**Disable notifications**:
```bash
cuenimby --no-notifications
```

**Debug mode**:
```bash
cuenimby --verbose
```

**Custom config**:
```bash
cuenimby --config /path/to/custom/config.json
```

## Integration with RQD

CueNIMBY works alongside RQD's automatic NIMBY feature.

For detailed information on how NIMBY states interact with desktop rendering allocations and show subscriptions, see the [Desktop rendering control guide](/docs/other-guides/desktop-rendering-control).

### How they work together

**RQD (Automatic)**:
* Monitors keyboard/mouse input
* Locks immediately on user activity
* Unlocks after idle period (default 5 minutes)
* Kills running frames when locking

**CueNIMBY (Manual + Feedback)**:
* Shows current state
* Allows manual control
* Sends notifications
* Provides scheduling

### Typical setup

1. **RQD runs as a service**: Automatic protection
2. **CueNIMBY runs at login**: Visual feedback and control

### State coordination

When RQD locks:
1. RQD detects input and locks host
2. Cuebot updates host state to NIMBY_LOCKED
3. CueNIMBY polls and sees NIMBY_LOCKED
4. CueNIMBY updates icon to orange (🟠)
5. CueNIMBY sends "NIMBY Locked" notification

When you manually lock via CueNIMBY:
1. You uncheck "Available" in menu
2. CueNIMBY calls Cuebot API to lock host
3. Cuebot updates host state to LOCKED
4. Icon changes to red (🔴)
5. CueNIMBY sends "Host Disabled" notification
6. RQD sees locked state and doesn't dispatch jobs

## Troubleshooting

### Icon doesn't appear

**macOS:**
* Check System Preferences -> Notifications -> CueNIMBY
* Try restarting after login

**Windows:**
* Check system tray settings
* Show hidden icons

**Linux:**
* Ensure desktop environment supports system tray
* Some environments require AppIndicator support
* Try: `sudo apt-get install gir1.2-appindicator3-0.1`

### Can't connect to Cuebot

**Symptoms**: Gray icon, "Cannot determine state" logs

**Solutions**:
1. Verify Cuebot is running: `telnet cuebot.example.com 8443`
2. Check hostname/port in config
3. Check firewall rules
4. Run with `--verbose` to see connection errors

### Notifications not working

**macOS:**
* Grant notification permissions in System Preferences
* For best reliability, install terminal-notifier: `brew install terminal-notifier`
* Alternative: Install `pync`: `pip install pync`
* Built-in fallback uses osascript (no additional install required)

**Windows:**
* Check Windows notification settings
* Install `win10toast`: `pip install win10toast`

**Linux:**
* Verify notification daemon is running: `ps aux | grep notification`
* Install `notify2`: `pip install notify2`
* Test manually: `notify-send "Test" "Message"`

### State not updating

**Symptoms**: Icon stuck on one color

**Solutions**:
1. Check `poll_interval` in config (increase if too frequent)
2. Verify host exists in Cuebot: Check CueGUI Hosts view
3. Check hostname matches: `hostname` vs config
4. Restart CueNIMBY

### Scheduler not working

**Symptoms**: State doesn't change at scheduled time

**Solutions**:
1. Verify `scheduler_enabled: true` in config
2. Check "Scheduler" is checked in menu
3. Verify time format is HH:MM (24-hour)
4. Check day names are lowercase (monday, tuesday, etc.)
5. Restart CueNIMBY after config changes

### High CPU usage

**Causes**: Polling too frequently

**Solution**:
Increase poll interval in config:
```json
{
  "poll_interval": 10
}
```

## Best practices

### For artists

1. **Run at startup**: Add CueNIMBY to login items
2. **Configure schedule**: Match your work hours
3. **Check before heavy work**: Manually disable if doing intense local work
4. **Report issues**: Help improve the tool
5. **Communicate**: Let others know if you need exclusive use

### For administrators

1. **Deploy to all workstations**: Ensure consistent behavior
2. **Document policies**: Clear guidelines for users
3. **Provide support**: Help users configure correctly
4. **Monitor usage**: Track NIMBY events
5. **Test updates**: Verify new versions before deployment

### Performance tips

* Use appropriate poll interval (5-10 seconds)
* Disable notifications if not needed
* Use scheduler to reduce manual intervention
* Close CueNIMBY if not using workstation rendering

## Advanced usage

### Monitoring remote hosts

Monitor a different host:
```bash
cuenimby --hostname render-node-01
```

Useful for:
* Monitoring render nodes from workstation
* Remote administration
* Multi-host management

### Multiple instances

Run separate CueNIMBY instances with different configs:

```bash
# Terminal 1 - Local host
cuenimby --config ~/.opencue/local.json

# Terminal 2 - Remote host
cuenimby --config ~/.opencue/remote.json --hostname remote-01
```

### Automation

Start CueNIMBY automatically:

**macOS** (launchd):
Create `~/Library/LaunchAgents/com.opencue.cuenimby.plist`

**Windows** (Task Scheduler):
Create task to run on login

**Linux** (systemd user service):
Create `~/.config/systemd/user/cuenimby.service`

### Log monitoring

View logs for debugging:
```bash
cuenimby --verbose 2>&1 | tee cuenimby.log
```

## Related guides

* [Desktop rendering control guide](/docs/other-guides/desktop-rendering-control) - Understanding desktop allocations, subscriptions, and NIMBY states
* [NIMBY concept guide](/docs/concepts/nimby) - Overview of NIMBY system components
* [Quick start: CueNIMBY](/docs/quick-starts/quick-start-cuenimby) - Get started quickly
* [CueNIMBY tutorial](/docs/tutorials/cuenimby-tutorial) - Step-by-step tutorial
* [CueNIMBY development guide](/docs/developer-guide/cuenimby-development) - For developers
