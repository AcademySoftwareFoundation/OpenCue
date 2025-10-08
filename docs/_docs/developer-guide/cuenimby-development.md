---
title: "CueNIMBY development guide"
nav_order: 82
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

CueNIMBY is a Python-based system tray application built with modern, modular architecture. It's designed for cross-platform compatibility and maintainability.

### Technology stack

* **Language**: Python 3.7+
* **UI Framework**: pystray (system tray)
* **Graphics**: Pillow (icon generation)
* **API Client**: pycue (OpenCue Python API)
* **Notifications**: Platform-specific libraries
* **Testing**: pytest
* **Packaging**: Hatchling

### Key features

* Cross-platform (macOS, Windows, Linux)
* Real-time host monitoring
* Desktop notifications
* Time-based scheduling
* Configuration management
* Threaded architecture

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
├── monitor.py           # Host state monitoring
├── notifier.py          # Desktop notifications
├── scheduler.py         # Time-based scheduler
└── tray.py              # System tray UI
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

**Purpose**: Monitor OpenCue host state and running frames

**Key responsibilities**:
* Connect to Cuebot via pycue
* Poll host state periodically
* Detect state changes
* Detect new frame starts
* Provide host control (lock/unlock)
* Trigger callbacks for events

**Key classes**:
* `HostMonitor`: Main monitoring class
* `HostState`: Enum for host states

**Threading**: Runs in background daemon thread

#### `notifier.py` - Notifications

**Purpose**: Cross-platform desktop notifications

**Key responsibilities**:
* Detect platform
* Initialize appropriate notification system
* Send notifications for events
* Provide convenience methods for common notifications

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

**Purpose**: System tray UI and application coordination

**Key responsibilities**:
* Create system tray icon
* Generate state-based icons
* Handle menu interactions
* Coordinate components
* Manage application lifecycle

**Key classes**:
* `CueNIMBYTray`: Main tray application class

**UI library**: pystray

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

### Icon generation

* Icons are generated on-demand
* Cached within pystray
* Keep simple for performance

### Notification rate limiting

* Avoid spamming notifications
* Consider debouncing rapid state changes

## Related documentation

* [Desktop rendering control guide](/docs/other-guides/desktop-rendering-control) - Understanding allocations, subscriptions, and NIMBY states
* [NIMBY concept guide](/docs/concepts/nimby) - NIMBY system overview
* [CueNIMBY user guide](/docs/user-guides/cuenimby-user-guide) - End-user documentation
* [Quick start: CueNIMBY](/docs/quick-starts/quick-start-cuenimby) - Getting started guide
