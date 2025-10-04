---
title: "CueNIMBY Quick Start"
nav_order: 7
parent: Quick Starts
layout: default
linkTitle: "Quick start for CueNIMBY"
date: 2025-10-01
description: >
  Get started with CueNIMBY workstation control
---

# Quick start for CueNIMBY

### Get started with CueNIMBY workstation control

---

CueNIMBY is a cross-platform system tray application that provides user control over OpenCue's NIMBY (Not In My Back Yard) feature on workstations. It allows artists and users to monitor their machine's rendering availability, toggle between available and disabled states, receive notifications when jobs start, and schedule automatic state changes.

## Before you begin

You must have the following software installed on your machine:

* Python version 3.7 or greater
* The Python [`pip` command](https://pypi.org/project/pip/)
  * On some systems this command may be installed as `pip3`
* OpenCue client libraries (pycue)
* Access to a running Cuebot server

### Platform-specific requirements

**macOS:**
* macOS 10.14 or later
* Optional but recommended: `terminal-notifier` for most reliable notifications (`brew install terminal-notifier`)
* Alternative: `pync` for enhanced notifications (`pip install pync`)
* Built-in fallback: osascript (no additional install required)

**Windows:**
* Windows 10 or later
* Optional: `win10toast` for toast notifications

**Linux:**
* A desktop environment with system tray support
* Notification daemon (usually pre-installed)
* Optional: `notify2` for desktop notifications

## Installing CueNIMBY

### From source

1. Clone or download the OpenCue repository:

   ```bash
   git clone https://github.com/<username>/OpenCue.git
   cd OpenCue
   ```

2. Install CueNIMBY:

   ```bash
   cd cuenimby
   pip install .
   ```

### Using the sandbox installer

If you're using the OpenCue sandbox environment, CueNIMBY is automatically installed when you run:

```bash
./sandbox/install-client-sources.sh
```

## Running CueNIMBY

1. Start CueNIMBY from the command line:

   ```bash
   cuenimby
   ```

   On first run, CueNIMBY creates a configuration file at `~/.opencue/cuenimby.json`.

2. Look for the CueNIMBY icon in your system tray:
   * 🟢 Green: Available for rendering
   * 🔵 Blue: Currently rendering
   * 🔴 Red: Disabled (manually locked)
   * 🟠 Orange: NIMBY locked (due to user activity)

3. Right-click the tray icon to access the menu:
   * Toggle **Available** to enable/disable rendering
   * Toggle **Notifications** to control desktop alerts
   * Toggle **Scheduler** for time-based control

## Connecting to Cuebot

By default, CueNIMBY connects to `localhost:8443`. To connect to a different Cuebot server:

### Using command-line arguments

```bash
cuenimby --cuebot-host cuebot.example.com --cuebot-port 8443
```

### Using environment variables

```bash
export CUEBOT_HOST=cuebot.example.com
export CUEBOT_PORT=8443
cuenimby
```

### Using configuration file

Edit `~/.opencue/cuenimby.json`:

```json
{
  "cuebot_host": "cuebot.example.com",
  "cuebot_port": 8443
}
```

## Testing the setup

1. With CueNIMBY running, verify your host appears in CueGUI:
   * Open CueGUI or CueCommander
   * Navigate to the Hosts view
   * Find your workstation by hostname

2. Test manual control:
   * Right-click the CueNIMBY tray icon
   * Uncheck **Available** to disable rendering
   * Check **Available** to re-enable rendering
   * Observe the icon color change and notification

3. Test job notifications:
   * Submit a test job to OpenCue
   * When a frame starts on your workstation, you should receive a notification

## Troubleshooting

### CueNIMBY won't start

* Check that Python 3.7+ is installed: `python --version` or `python3 --version`
* Verify OpenCue client libraries are installed: `pip list | grep pycue`
* Check the logs for errors: Run with `cuenimby --verbose`

### Can't connect to Cuebot

* Verify Cuebot is running and accessible
* Check firewall rules allow gRPC traffic on the Cuebot port
* Test connectivity: `telnet cuebot.example.com 8443`

### Tray icon doesn't appear

* Linux: Ensure your desktop environment supports system tray icons
* Some environments require AppIndicator support
* Try restarting CueNIMBY after logging in

### No notifications

* macOS: Grant notification permissions in System Preferences. For best results, install terminal-notifier: `brew install terminal-notifier`
* Windows: Check notification settings in Windows Settings
* Linux: Ensure notification daemon is running: `ps aux | grep notification`
