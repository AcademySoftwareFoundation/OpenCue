---
title: "CueNIMBY development guide"
nav_order: 86
parent: Developer Guide
layout: default
linkTitle: "CueNIMBY development"
date: 2025-10-01
description: >
  Developer guide for contributing to CueNIMBY
---

# CueNIMBY development guide

### Developer guide for contributing to CueNIMBY

---

This guide covers CueNIMBY's architecture, testing, and contribution guidelines.

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

CueNIMBY is a Python-based system tray application built with modern, modular architecture using Qt for native look and feel. It's designed for cross-platform compatibility and maintainability.

### Technology stack

* **Language**: Python 3.7+
* **UI Framework**: Qt6 (QSystemTrayIcon, QMenu)
* **Graphics**: Qt6 QPixmap for icon rendering
* **API Client**: pycue (OpenCue Python API)
* **Notifications**: Platform-specific libraries with enhanced fallback chain
* **Testing**: pytest with full coverage
* **Packaging**: Hatchling
* **Icons**: Professional icon set with OpenCue logo

### Key features

* Cross-platform (macOS, Windows, Linux) with native UI
* Real-time host monitoring with enhanced status detection
* Desktop notifications with emoji hints (🔒❌⚠️🔧)
* Time-based scheduling
* Configuration management
* Threaded architecture
* **Resilient connection**: Starts even when CueBot is unreachable
* **Enhanced status states**: CueBot connectivity, host registration, ping monitoring, repair state
* **CueGUI integration**: Launch CueGUI directly from tray menu
* **Intelligent menu states**: Options disabled when actions cannot be performed

## Architecture

### Component overview

```
┌─────────────────────────────────────────────────────────┐
│                CueNIMBY Tray                            │
│                  (tray.py)                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │         System Tray Icon & Menu                 │    │
│  │  - Visual state indicator                       │    │
│  │  - User controls (lock/unlock)                  │    │
│  │  - Settings menu                                │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌─────────────┐ ┌──────────────┐
│   Monitor    │ │  Notifier   │ │  Scheduler   │
│ (monitor.py) │ │(notifier.py)│ │(scheduler.py)│
└──────────────┘ └─────────────┘ └──────────────┘
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌─────────────┐ ┌─────────────┐
│ OpenCue API  │ │   Platform  │ │    Time     │
│   (pycue)    │ │Notifications│ │   Based     │
│              │ │             │ │   Rules     │
└──────────────┘ └─────────────┘ └─────────────┘
        │
        ▼
┌──────────────┐
│   Cuebot     │
│   Server     │
└──────────────┘
```

### Module structure

```
cuenimby/
├── __init__.py          # Package initialization
├── __main__.py          # CLI entry point
├── config.py            # Configuration management
├── monitor.py           # Host state monitoring with enhanced status detection
├── notifier.py          # Desktop notifications with emoji support
├── scheduler.py         # Time-based scheduler
├── tray.py              # Qt system tray UI
└── icons/               # Icon assets with OpenCue logo
    ├── opencue-available.png
    ├── opencue-working.png
    ├── opencue-disabled.png
    ├── opencue-error.png
    ├── opencue-warning.png
    ├── opencue-repair.png
    ├── opencue-starting.png
    ├── opencue-unknown.png
    ├── opencue-default.png
    ├── opencue-icon.ico      # Windows icon
    └── opencue-icons.psd     # Source file
```

### Module descriptions

#### `__main__.py` - Entry point

**Purpose**: Command-line interface and application initialization

**Key responsibilities**:
* Parse command-line arguments
* Setup logging
* Initialize configuration
* Create and start tray application

**Key classes/functions**:
* `main()`: Entry point function
* `setup_logging()`: Configure logging

#### `config.py` - Configuration

**Purpose**: Manage application configuration

**Key responsibilities**:
* Load/save JSON configuration
* Provide default values
* Expose configuration via properties
* Handle configuration file creation

**Key classes**:
* `Config`: Configuration management class

**Configuration file location**: `~/.opencue/cuenimby.json`

#### `monitor.py` - Host monitoring

**Purpose**: Monitor OpenCue host state and running frames with enhanced status detection

**Key responsibilities**:
* Connect to Cuebot via pycue
* Poll host state periodically
* **Detect CueBot connectivity issues**
* **Check host registration status**
* **Monitor host ping times**
* **Detect repair state**
* Detect state changes
* Detect new frame starts
* Provide host control (lock/unlock)
* Trigger callbacks for events
* **Continue operation when CueBot is unreachable**

**Key classes**:
* `HostMonitor`: Main monitoring class
* `HostState`: Enum for host states
  - `STARTING`
  - `AVAILABLE`
  - `WORKING`
  - `NIMBY_LOCKED`
  - `HOST_LOCKED`
  - `HOST_DOWN`
  - `NO_HOST`
  - `HOST_LAGGING`
  - `CUEBOT_UNREACHABLE`
  - `ERROR`
  - `REPAIR`
  - `UNKNOWN`

**Threading**: Runs in background daemon thread

**Enhanced Error Handling**: Gracefully handles connection failures and provides clear status feedback

#### `notifier.py` - Notifications

**Purpose**: Cross-platform desktop notifications with emoji support

**Key responsibilities**:
* Detect platform
* Initialize appropriate notification system
* Send notifications for events with emoji hints (🔒❌⚠️🔧)
* Provide convenience methods for common notifications
* **Enhanced notification messages** with helpful troubleshooting information

**Key classes**:
* `Notifier`: Notification manager
* `NotifierType`: Enum for notification backend types

**Platform support**:
* macOS: terminal-notifier (preferred), pync, or osascript
* Windows: win10toast
* Linux: notify2 or notify-send

**Implementation notes**:
* Auto-detects terminal-notifier on macOS for best reliability
* Uses fallback chain if preferred backend unavailable
* Proper string escaping for AppleScript on macOS
* **Emoji support across all platforms**
* **Context-aware notification messages**

#### `scheduler.py` - Scheduler

**Purpose**: Time-based automatic state changes

**Key responsibilities**:
* Parse schedule configuration
* Check current time against schedule
* Determine desired state
* Trigger state change callbacks
* Run periodic checks

**Key classes**:
* `NimbyScheduler`: Scheduler class

**Threading**: Runs in background daemon thread

#### `tray.py` - System tray

**Purpose**: Qt-based system tray UI and application coordination

**Key responsibilities**:
* Create system tray icon using QSystemTrayIcon
* Load professional icons with OpenCue logo
* Handle menu interactions with QMenu
* **Implement intelligent menu states**
* **Add "Launch CueGUI" menu option**
* **Enhanced "About" dialog** showing CueBot address
* Coordinate components
* Manage application lifecycle
* **Handle startup when CueBot is unreachable**

**Key classes**:
* `CueNIMBYTray`: Main tray application class

**UI library**: Qt (QSystemTrayIcon, QMenu, QAction, QPixmap)

**Icon Management**
* Icons stored in `icons/` directory
* Loaded using QPixmap for native rendering
* State-to-icon mapping:
  ```python
  ICONS = {
      HostState.STARTING:     "opencue-starting.png",
      HostState.AVAILABLE:    "opencue-available.png",
      HostState.WORKING:      "opencue-working.png",
      HostState.NIMBY_LOCKED: "opencue-disabled.png",
      HostState.HOST_DOWN:    "opencue-disabled.png",
      HostState.HOST_LOCKED:  "opencue-disabled.png",
      HostState.NO_HOST:      "opencue-error.png",
      HostState.HOST_LAGGING: "opencue-warning.png",
      HostState.CUEBOT_UNREACHABLE: "opencue-error.png",
      HostState.ERROR:        "opencue-error.png",
      HostState.UNKNOWN:      "opencue-unknown.png",
      HostState.REPAIR:       "opencue-repair.png",
  }
  ```

**Menu State Management**:
* Menu items automatically disabled based on application state
* "Available" checkbox disabled when CueBot is unreachable or host not found
* "Launch CueGUI" option disabled when CueGUI is not available

## Development setup

### Clone repository

```bash
git clone https://github.com/<username>/OpenCue.git
cd OpenCue/cuenimby
```

### Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install in development mode

```bash
pip install -e ".[dev,test]"
```

This installs:
* CueNIMBY in editable mode
* Development dependencies (black, pylint)
* Test dependencies (pytest, pytest-mock)

### Verify installation

```bash
cuenimby --version
pytest
```

## Testing


### Running tests

**All tests**:
```bash
pytest
```

**Specific module**:
```bash
pytest tests/test_config.py
```

**Specific test**:
```bash
pytest tests/test_config.py::test_default_config
```

**With verbose output**:
```bash
pytest -v
```

**With coverage**:
```bash
pytest --cov=cuenimby --cov-report=term-missing
```

## Platform-specific development

### macOS

**Testing notifications**:
```bash
# Install optional dependency
pip install pync

# Test
cuenimby --verbose
```

### Windows

**Testing notifications**:
```bash
# Install optional dependency
pip install win10toast

# Test
cuenimby --verbose
```

### Linux

**Testing on different DEs**:

Test on multiple desktop environments:
* GNOME
* KDE
* XFCE
* i3 (with systray daemon)

**Testing notifications**:
```bash
# Install optional dependency
pip install notify2

# Test
cuenimby --verbose

# Manual notification test
notify-send "Test" "Message"
```

## Debugging

### Enable verbose logging

```bash
cuenimby --verbose
```

### Log specific modules

```python
import logging

logging.getLogger('cuenimby.monitor').setLevel(logging.DEBUG)
logging.getLogger('cuenimby.scheduler').setLevel(logging.DEBUG)
```

## Performance considerations

### Polling interval

* Default: 5 seconds
* Trade-off: Responsiveness vs. resource usage
* Monitor CPU usage when adjusting
* **Enhanced error handling**: Graceful degradation when CueBot is unreachable

### Icon management

* Icons loaded from disk using QPixmap
* Cached by Qt for performance
* Professional icons with OpenCue logo
* 9 distinct icon states for clear visual feedback

### Notification rate limiting

* Avoid spamming notifications
* Consider debouncing rapid state changes
* Context-aware notifications with actionable messages

### Connection resilience

* Application starts even when CueBot is unreachable
* Automatic reconnection attempts
* Clear visual feedback during connection issues
* No blocking on network operations

## New Icon System

**Professional icons with OpenCue logo**:
* 9 icon states for comprehensive status feedback
* Consistent visual identity
* Designed for clarity at small sizes
* Source PSD file included for customization

**Icon files**:
* `opencue-available.png` - Green (ready)
* `opencue-working.png` - Icon with red dot in center (rendering)
* `opencue-disabled.png` - Red (locked/down)
* `opencue-error.png` - Red with X (error/unreachable)
* `opencue-warning.png` - Yellow (warning/lagging)
* `opencue-repair.png` - Orange with wrench (repair)
* `opencue-starting.png` - Gray (initializing)
* `opencue-unknown.png` - Gray with question (unknown)
* `opencue-default.png` - Fallback

**Icon Gallery**:

All icons are located in `cuenimby/icons/` and feature the OpenCue logo:

| Icon | File | Description |
|------|------|-------------|
| ![Available](/assets/images/cuenimby/icons/opencue-available.png) | `opencue-available.png` | Green - Host ready for rendering |
| ![Working](/assets/images/cuenimby/icons/opencue-working.png) | `opencue-working.png` | Icon with red dot in center - Currently rendering |
| ![Disabled](/assets/images/cuenimby/icons/opencue-disabled.png) | `opencue-disabled.png` | Red - Host locked/disabled |
| ![Error](/assets/images/cuenimby/icons/opencue-error.png) | `opencue-error.png` | Red X - Connection error |
| ![Warning](/assets/images/cuenimby/icons/opencue-warning.png) | `opencue-warning.png` | Yellow - Warning/lagging |
| ![Repair](/assets/images/cuenimby/icons/opencue-repair.png) | `opencue-repair.png` | Orange - Under repair |
| ![Starting](/assets/images/cuenimby/icons/opencue-starting.png) | `opencue-starting.png` | Gray - Initializing |
| ![Unknown](/assets/images/cuenimby/icons/opencue-unknown.png) | `opencue-unknown.png` | Gray ? - Unknown state |
| ![Default](/assets/images/cuenimby/icons/opencue-default.png) | `opencue-default.png` | Default fallback |

The source PSD file (`opencue-icons.psd`) is included for customization and creating additional icon states.

### Enhanced Status Detection

**New status states**:
1. **CUEBOT_UNREACHABLE**: Detects when CueBot server is down or unreachable
2. **NO_HOST**: Detects when machine is not registered with CueBot
3. **HOST_LAGGING**: Warns when host ping exceeds 60 seconds
4. **REPAIR**: Shows when host is administratively marked for repair

**Benefits**:
* Clear visual feedback for connection issues
* Helpful troubleshooting guidance in notifications
* Reduced user confusion
* Proactive problem identification

### Emoji Support

**Integration**:
* Emojis in status messages: 🔒❌⚠️🔧
* Visual hints for quick status recognition
* Platform-agnostic (works on all OSs)
* Enhances accessibility

### CueGUI Integration

**"Launch CueGUI" menu option**:
* Direct access to CueGUI from tray
* Automatically detects CueGUI availability
* Menu item disabled when CueGUI not found
* Convenient workflow improvement

### Enhanced About Window

**Improvements**:
* Shows CueBot server address
* Displays monitored hostname
* Application version
* Helpful for debugging and support

## Related documentation

* [Desktop rendering control guide](/docs/other-guides/desktop-rendering-control) - Understanding allocations, subscriptions, and NIMBY states
* [NIMBY concept guide](/docs/concepts/nimby) - NIMBY system overview
* [CueNIMBY user guide](/docs/user-guides/cuenimby-user-guide) - End-user documentation
* [Quick start: CueNIMBY](/docs/quick-starts/quick-start-cuenimby) - Getting started guide
