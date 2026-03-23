# CueNIMBY - OpenCue NIMBY Control

CueNIMBY is a cross-platform system tray application that provides user control over OpenCue's NIMBY (Not In My Back Yard) feature on workstations. Built with Qt6 for native look and feel across all platforms.

## Features

- **System Tray Icon with OpenCue Logo**: Visual indication of current rendering state with professional icons
  - 🔄 **Starting**: Application is initializing
  - 🟢 **Available** (`opencue-available.png`): Host is idle and ready for rendering
  - 🔴 **Working** (`opencue-working.png`): Currently rendering frames (red dot in center)
  - 🔴 **Disabled** (`opencue-disabled.png`):
     - NIMBY locked (🔒 due to user activity)
     - Host locked (🔒 manually disabled)
     - Host down (❌ RQD is not running)
  - ❌ **Error** (`opencue-error.png`):
     - CueBot unreachable (❌ Cannot connect to server)
     - Machine not found on CueBot (❌ Check if RQD is running)
  - ⚠️ **Warning** (`opencue-warning.png`): Host ping above 60 seconds limit
  - 🔧 **Repair** (`opencue-repair.png`): Host is under repair, check with tech team
  - ❓ **Unknown** (`opencue-unknown.png`): Unknown status

- **Enhanced User Controls**:
  - Toggle workstation availability for rendering
  - Enable/disable desktop notifications
  - Enable/disable time-based scheduler
  - **Launch CueGUI** directly from the tray menu
  - **Open Config File** in your default editor
  - **Intelligent menu states**: Options appear disabled when action cannot be performed

- **Improved Desktop Notifications**:
  - Alert when a job starts rendering on your machine
  - Notify when NIMBY locks/unlocks your workstation
  - Notify when you manually change availability
  - **Alert when CueBot is unreachable** with helpful troubleshooting info
  - **Alert when host is not registered** with RQD status guidance
  - **Warning when host is lagging** (ping > 60 seconds)
  - **Notification when host is under repair**
  - Visual hints with emojis (🔒❌⚠️🔧) for quick status recognition

- **Resilient Connection**:
  - Tray starts even when CueBot is unreachable
  - Automatically reconnects when CueBot becomes available
  - Clear visual feedback about connection status

- **Enhanced About Window**:
  - Shows CueNIMBY version
  - Displays CueBot server address
  - Shows monitored hostname
  - Application description

- **Time-based Scheduler**:
  - Automatically disable rendering during work hours
  - Configure different schedules for each day of the week
  - Example: Disable rendering Mon-Fri 9AM-6PM, enable evenings and weekends

## Installation

### From Source

```bash
cd cuenimby
pip install .
```

### With Development Dependencies

```bash
pip install -e ".[dev,test]"
```

## Usage

### Basic Usage

Start CueNIMBY with default settings:

```bash
cuenimby
```

### Command Line Options

```bash
cuenimby --help

Options:
  --version              Show version and exit
  --config PATH          Path to config file (default: ~/.opencue/cuenimby.json)
  --cuebot-host HOST     Cuebot hostname (overrides config)
  --cuebot-port PORT     Cuebot port (overrides config)
  --hostname HOST        Host to monitor (default: local hostname)
  --no-notifications     Disable desktop notifications
  --verbose, -v          Enable verbose logging
```

### Examples

Connect to a specific Cuebot server:

```bash
cuenimby --cuebot-host cuebot.example.com --cuebot-port 8443
```

Run with verbose logging:

```bash
cuenimby --verbose
```

Monitor a specific host:

```bash
cuenimby --hostname workstation-01
```

## Configuration

CueNIMBY stores its configuration in `~/.opencue/cuenimby.json`. The configuration file is automatically created on first run with default values.

### Configuration File Format

```json
{
  "cuebot_host": "localhost",
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

### Configuration Options

- **cuebot_host**: Hostname of the Cuebot server
- **cuebot_port**: Port number for Cuebot gRPC
- **hostname**: Host to monitor (null = auto-detect local hostname)
- **poll_interval**: How often to check state (seconds)
- **show_notifications**: Enable/disable desktop notifications
- **notification_duration**: How long notifications stay visible (seconds)
- **scheduler_enabled**: Enable/disable time-based scheduler
- **schedule**: Weekly schedule configuration

### Schedule Configuration

Each day can have a schedule entry with:
- **start**: Start time in HH:MM format (24-hour)
- **end**: End time in HH:MM format (24-hour)
- **state**: Desired state during this time period ("disabled" or "available")

During the configured time period, the host will be set to the specified state. Outside the period, the opposite state applies.

## System Tray Menu

Right-click the tray icon to access:

- **Available** (checkbox): Toggle rendering availability
  - Disabled when host is not found or CueBot is unreachable
- **Notifications** (checkbox): Enable/disable notifications
- **Scheduler** (checkbox): Enable/disable time-based scheduler
- **Launch CueGUI**: Open CueGUI application directly
  - Disabled when CueGUI is not available
- **Open Config File**: Open the configuration file in your default editor
- **About**: Show application info including CueBot address and monitored host
- **Quit**: Exit CueNIMBY

## Platform-Specific Notes

### macOS

CueNIMBY uses the native macOS notification system. For best results:
- Grant notification permissions when prompted
- Install `terminal-notifier` for most reliable notifications (recommended):
  ```bash
  brew install terminal-notifier
  ```
- Alternative: Install optional `pync` package for enhanced notifications:
  ```bash
  pip install pync
  ```
- Built-in fallback uses osascript (no additional install required)

### Windows

CueNIMBY uses Windows 10+ toast notifications:
- Notifications require Windows 10 or later
- Install optional `win10toast` package:
  ```bash
  pip install win10toast
  ```

### Linux

CueNIMBY uses the freedesktop notification system:
- Requires a notification daemon (usually pre-installed)
- Install optional `notify2` package:
  ```bash
  pip install notify2
  ```
- Fallback to `notify-send` command if package unavailable

## Understanding NIMBY and Desktop Rendering

### What Does "Locked" Mean?

When a host is **locked** (either manually or via NIMBY), it becomes unavailable for rendering jobs in OpenCue:
- **Disabled (Manual Lock)**: User manually disabled rendering via CueNIMBY
- **NIMBY Locked**: RQD automatically locked the host due to user activity (mouse/keyboard)

In both cases, the host will not accept new rendering jobs. Any currently running jobs will continue until completion, but no new work will be dispatched to the host.

### Desktop Rendering Control

Desktop workstations in OpenCue are typically configured under a special allocation called `local.desktop`. This allows administrators to control rendering on user workstations separately from dedicated render farm machines.

**How Desktop Rendering Works:**

1. **Allocations**: Desktop hosts are assigned to the `local.desktop` allocation
2. **Show Subscriptions**: Shows are configured with subscriptions to allocations, including `local.desktop`
3. **Controlling Rendering**: To enable rendering on desktops for a specific show:
   - Increase the subscription size for the `local.desktop` allocation
   - Adjust the burst value to control how many jobs can run
   - Setting size/burst to zero effectively disables desktop rendering for that show

**Example:**
- Default: Show has `local.desktop` subscription with size=0, burst=0 (no desktop rendering)
- Enable: Set `local.desktop` subscription to size=10, burst=20 (allow up to 10 cores, burst to 20)

This gives production teams fine-grained control over when and how much desktop resources are used for rendering.

For more detailed information about desktop rendering control, allocations, and subscriptions, see the [Desktop rendering control guide](https://www.opencue.io/docs/other-guides/desktop-rendering-control) in the official documentation.

## Icon States Reference

All icons feature the OpenCue logo for professional appearance:

| Icon File | State | Emoji | Description |
|-----------|-------|-------|-------------|
| `opencue-starting.png` | Starting | 🔄 | Application is initializing |
| `opencue-available.png` | Available | 🟢 | Host is idle and ready for rendering |
| `opencue-working.png` | Working | 🔴 | Currently rendering frames (red dot in center) |
| `opencue-disabled.png` | Disabled/Locked/Down | 🔴 | NIMBY locked, Host locked, or Host down |
| `opencue-error.png` | Error/Unreachable | ❌ | CueBot unreachable or host not found |
| `opencue-warning.png` | Warning/Lagging | ⚠️ | Host ping above 60 second limit |
| `opencue-repair.png` | Under Repair | 🔧 | Host is under repair |
| `opencue-unknown.png` | Unknown | ❓ | Unknown status |
| `opencue-default.png` | Default | ⚪ | Fallback icon |

### Icon Gallery

Here are all the CueNIMBY icons with the OpenCue logo:

| Icon | Name | Description |
|------|------|-------------|
| ![Available](cuenimby/icons/opencue-available.png) | `opencue-available.png` | Green icon - Host ready for rendering |
| ![Working](cuenimby/icons/opencue-working.png) | `opencue-working.png` | Icon with red dot in center - Currently rendering |
| ![Disabled](cuenimby/icons/opencue-disabled.png) | `opencue-disabled.png` | Red icon - Host locked/disabled |
| ![Error](cuenimby/icons/opencue-error.png) | `opencue-error.png` | Red X icon - Connection error |
| ![Warning](cuenimby/icons/opencue-warning.png) | `opencue-warning.png` | Yellow icon - Warning state |
| ![Repair](cuenimby/icons/opencue-repair.png) | `opencue-repair.png` | Orange icon - Under repair |
| ![Starting](cuenimby/icons/opencue-starting.png) | `opencue-starting.png` | Gray icon - Initializing |
| ![Unknown](cuenimby/icons/opencue-unknown.png) | `opencue-unknown.png` | Gray ? icon - Unknown state |
| ![Default](cuenimby/icons/opencue-default.png) | `opencue-default.png` | Default fallback icon |

## Integration with RQD

CueNIMBY works alongside RQD's built-in NIMBY feature:

1. **RQD NIMBY**: Automatically detects user activity (mouse/keyboard) and locks the host
2. **CueNIMBY**: Provides user control and visual feedback via system tray

Both can run simultaneously:
- RQD handles automatic locking based on activity detection
- CueNIMBY allows manual control and shows visual notifications
- When RQD locks the host due to user activity, CueNIMBY reflects this with the NIMBY_LOCKED state (🔒 NIMBY locked icon)
- Users can manually lock/unlock via CueNIMBY regardless of RQD's automatic behavior
- CueNIMBY starts even when CueBot is unreachable and will catch up when connection is restored

## Troubleshooting

### Can't connect to CueBot

CueNIMBY will now start even when CueBot is unreachable and display a clear error status (❌).

Ensure:
- CueBot is running and accessible
- Hostname and port are correct in `~/.opencue/cuenimby.json`
- Network allows gRPC traffic on the specified port (default 8443)
- Environment variables are set if needed:
  ```bash
  export CUEBOT_HOST=cuebot.example.com
  export CUEBOT_PORT=8443
  ```

Check the tray icon:
- ❌ Red error icon = CueBot unreachable
- Hover over icon to see connection status message
- CueNIMBY will automatically reconnect when CueBot becomes available

### Host not found on CueBot

If you see "❌ Machine not found on CueBot, check if RQD is running":

Verify:
- RQD is running on your machine: `ps aux | grep rqd` (macOS/Linux) or Task Manager (Windows)
- The hostname matches exactly (case-sensitive)
- The host is registered with CueBot (check in CueGUI > Monitor Hosts)
- Use `--hostname` flag to specify exact hostname if needed
- RQD has successfully connected to CueBot (check RQD logs)

### Host ping is lagging

If you see "⚠️ Host ping above limit" warning:

This indicates RQD hasn't reported to CueBot in over 60 seconds. Check:
- RQD is still running
- Network connection is stable
- RQD logs for connection errors
- Consider restarting RQD if issue persists

### Host is under repair

If you see "🔧 Under Repair" status:

- Your host has been marked for maintenance by an administrator
- Contact your technical team for more information
- No rendering will occur on this host until repair state is cleared

### Notifications not working

Check:
- Notification permissions are granted (especially on macOS)
- Install platform-specific notification package (see Platform-Specific Notes)
- Enable notifications in configuration or tray menu
- Check system notification settings

### Icon not appearing

Some desktop environments require:
- Qt6 support (installed as dependency)
- System tray enabled in desktop settings
- Restart of the application after desktop environment changes
- On Linux: Ensure tray icon support is enabled in your desktop environment

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black cuenimby/
```

### Linting

```bash
pylint cuenimby/
```
