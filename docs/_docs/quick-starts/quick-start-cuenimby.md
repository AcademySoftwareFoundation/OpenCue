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

CueNIMBY is a Qt-based cross-platform system tray application that provides user control over OpenCue's NIMBY (Not In My Back Yard) feature on workstations. It features professional icons with the OpenCue logo, emoji hints (🔒❌⚠️🔧) for quick status recognition, and enhanced status detection. It allows artists and users to monitor their machine's rendering availability, toggle between available and disabled states, receive notifications when jobs start, launch CueGUI directly from the tray, and schedule automatic state changes. CueNIMBY starts even when CueBot is unreachable and reconnects automatically.

## Before you begin

You must have the following software installed on your machine:

* Python version 3.7 or greater
* The Python [`pip` command](https://pypi.org/project/pip/)
  * On some systems this command may be installed as `pip3`
* Qt for Python (PyQt6 or PySide6) - automatically installed with CueNIMBY
* OpenCue client libraries (pycue)
* Access to a running Cuebot server (CueNIMBY will start even if CueBot is unreachable and reconnect automatically)

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

2. Look for the CueNIMBY icon in your system tray (professional icons with OpenCue logo):
   * 🔄 **Starting** (`opencue-starting.png`): Application is initializing
   * 🟢 **Available** (`opencue-available.png`): Host is idle and ready for rendering
   * 🔵 **Working** (`opencue-working.png`): Currently rendering frames
   * 🔴 **Disabled** (`opencue-disabled.png`): Manually locked, NIMBY locked, or host down
   * ❌ **Error** (`opencue-error.png`): CueBot unreachable or machine not found on CueBot
   * ⚠️ **Warning** (`opencue-warning.png`): Host ping above 60 second limit
   * 🔧 **Repair** (`opencue-repair.png`): Host is under repair
   * ❓ **Unknown** (`opencue-unknown.png`): Unknown status

   **macOS - Available status:**

   ![CueNIMBY Available Status on macOS](/assets/images/cuenimby/macos/cuenimby_status_available-macos.png)

   **Windows - Available status:**

   ![CueNIMBY Available Status on Windows](/assets/images/cuenimby/windows/cuenimby_status_available-windows.png)

   **Icon Gallery:**

   | Icon | File | Description |
   |------|------|-------------|
   | ![Available](/assets/images/cuenimby/icons/opencue-available.png) | `opencue-available.png` | Green - Ready for rendering |
   | ![Working](/assets/images/cuenimby/icons/opencue-working.png) | `opencue-working.png` | Blue - Currently rendering |
   | ![Disabled](/assets/images/cuenimby/icons/opencue-disabled.png) | `opencue-disabled.png` | Red - Locked/disabled |
   | ![Error](/assets/images/cuenimby/icons/opencue-error.png) | `opencue-error.png` | Red X - Error/unreachable |
   | ![Warning](/assets/images/cuenimby/icons/opencue-warning.png) | `opencue-warning.png` | Yellow - Warning/lagging |
   | ![Repair](/assets/images/cuenimby/icons/opencue-repair.png) | `opencue-repair.png` | Orange - Under repair |
   | ![Starting](/assets/images/cuenimby/icons/opencue-starting.png) | `opencue-starting.png` | Gray - Initializing |
   | ![Unknown](/assets/images/cuenimby/icons/opencue-unknown.png) | `opencue-unknown.png` | Gray ? - Unknown |
   | ![Default](/assets/images/cuenimby/icons/opencue-default.png) | `opencue-default.png` | Default fallback |

3. Right-click the tray icon to access the menu:
   * Toggle **Available** to enable/disable rendering (disabled when CueBot is unreachable or host not found)
   * Toggle **Notifications** to control desktop alerts
   * Toggle **Scheduler** for time-based control
   * **Launch CueGUI** to open CueGUI application directly (disabled when CueGUI is not available)
   * **Open Config File** to edit configuration in your default editor
   * **About** to view CueBot address, monitored host, and version information

   **macOS - CueNIMBY menu:**

   ![CueNIMBY Menu on macOS](/assets/images/cuenimby/macos/cuenimby_about-macos.png)

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

CueNIMBY will now start even when CueBot is unreachable and display a clear error status (❌).

**macOS - Connection error:**

![CueNIMBY Connection Error on macOS](/assets/images/cuenimby/macos/cuenimby_status_error_cant_connect_to_cuebot-macos.png)

**Windows - Connection error:**

![CueNIMBY Connection Error on Windows](/assets/images/cuenimby/windows/cuenimby_status_error_cant_connect_to_cuebot-windows.png)

* Check the tray icon tooltip for specific error message
* Verify Cuebot is running and accessible
* Check firewall rules allow gRPC traffic on the Cuebot port
* Test connectivity: `telnet cuebot.example.com 8443`
* Verify hostname and port in `~/.opencue/cuenimby.json`
* Run with `--verbose` to see detailed connection errors
* CueNIMBY will automatically reconnect when CueBot becomes available

### Tray icon doesn't appear

* Linux: Ensure your desktop environment supports system tray icons
* Some environments require Qt6 and system tray support
* Try restarting CueNIMBY after logging in

### Host not found

If you see "❌ Machine not found on CueBot, check if RQD is running":

* Verify RQD is running on your machine: `ps aux | grep rqd` (macOS/Linux)
* Check RQD logs for connection errors
* Verify hostname matches in CueBot (check CueGUI > Monitor Hosts)
* Use `--hostname` flag to specify exact hostname: `cuenimby --hostname your-host-name`
* Ensure RQD successfully registered with CueBot

### Host lagging

If you see "⚠️ Host ping above limit" warning:

**macOS - Host lagging:**

![CueNIMBY Host Lagging on macOS](/assets/images/cuenimby/macos/cuenimby_status_warning_host_ping_above_limit-macos.png)

**Windows - Host lagging:**

![CueNIMBY Host Lagging on Windows](/assets/images/cuenimby/windows/cuenimby_status_warning_host_ping_above_limit-windows.png)

* Check if RQD is still running: `ps aux | grep rqd`
* Verify network connection stability
* Review RQD logs for connection issues
* Consider restarting RQD if problem persists
* Check CueBot server load

### Host under repair

If you see "🔧 Under Repair" status:

**macOS - Under repair:**

![CueNIMBY Under Repair on macOS](/assets/images/cuenimby/macos/cuenimby_status_repair_host_set_to_repair_state-macos.png)

**Windows - Under repair:**

![CueNIMBY Under Repair on Windows](/assets/images/cuenimby/windows/cuenimby_status_repair_host_set_to_repair_state-windows.png)

* Contact your technical team for repair status
* Host has been administratively marked for maintenance
* No rendering will occur until repair state is cleared
* Check with system administrators for estimated resolution

### No notifications

* macOS: Grant notification permissions in System Preferences. For best results, install terminal-notifier: `brew install terminal-notifier`
* Windows: Check notification settings in Windows Settings
* Linux: Ensure notification daemon is running: `ps aux | grep notification`
