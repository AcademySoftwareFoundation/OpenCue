# CueNIMBY - OpenCue NIMBY Control

CueNIMBY is a cross-platform system tray application that provides user control over OpenCue's NIMBY (Not In My Back Yard) feature on workstations.

## Features

- **System Tray Icon**: Visual indication of current rendering state
  - 🟢 Green: Available for rendering
  - 🔵 Blue: Currently rendering
  - 🔴 Red: Disabled (manually locked)
  - 🟠 Orange: NIMBY locked (due to user activity)
  - ⚫ Gray: Unknown/Disconnected

- **User Controls**:
  - Toggle workstation availability for rendering
  - Enable/disable desktop notifications
  - Enable/disable time-based scheduler

- **Desktop Notifications**:
  - Alert when a job starts rendering on your machine
  - Notify when NIMBY locks/unlocks your workstation
  - Notify when you manually change availability

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
- **Notifications** (checkbox): Enable/disable notifications
- **Scheduler** (checkbox): Enable/disable time-based scheduler
- **Open Config File**: Open the configuration file in your default editor
- **About**: Show application info
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

## Integration with RQD

CueNIMBY works alongside RQD's built-in NIMBY feature:

1. **RQD NIMBY**: Automatically detects user activity (mouse/keyboard) and locks the host
2. **CueNIMBY**: Provides user control and visual feedback via system tray

Both can run simultaneously:
- RQD handles automatic locking based on activity detection
- CueNIMBY allows manual control and shows visual notifications
- When RQD locks the host due to user activity, CueNIMBY reflects this with the NIMBY_LOCKED state (🟠 Orange icon)
- Users can manually lock/unlock via CueNIMBY regardless of RQD's automatic behavior

## Troubleshooting

### Can't connect to Cuebot

Ensure:
- Cuebot is running and accessible
- Hostname and port are correct
- Network allows gRPC traffic on the specified port
- Environment variables are set if needed:
  ```bash
  export CUEBOT_HOST=cuebot.example.com
  export CUEBOT_PORT=8443
  ```

### Notifications not working

Check:
- Notification permissions are granted
- Install platform-specific notification package (see Platform-Specific Notes)
- Enable notifications in configuration or tray menu

### Host not found

Verify:
- The hostname matches exactly (case-sensitive)
- The host is registered with Cuebot
- Use `--hostname` flag to specify exact hostname

### Icon not appearing

Some desktop environments require:
- AppIndicator support (Linux)
- System tray enabled in desktop settings
- Restart of the application after desktop environment changes

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
