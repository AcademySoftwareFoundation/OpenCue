---
title: "CueNIMBY development guide"
nav_order: 75
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

This guide covers CueNIMBY's architecture, development workflow, testing, and contribution guidelines.

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

**Platform support**:
* macOS: pync or osascript
* Windows: win10toast
* Linux: notify2 or notify-send

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

## Development workflow

### 1. Create feature branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make changes

Edit source files in `cuenimby/`.

### 3. Test changes

```bash
# Run tests
pytest

# Run specific test
pytest tests/test_config.py::test_default_config

# Run with coverage
pytest --cov=cuenimby --cov-report=html
```

### 4. Format code

```bash
# Format with black
black cuenimby/ tests/

# Check formatting
black --check cuenimby/ tests/
```

### 5. Lint code

```bash
# Run pylint
pylint cuenimby/

# Check specific file
pylint cuenimby/tray.py
```

### 6. Test manually

```bash
# Run in development mode
cuenimby --verbose

# Test with custom config
cuenimby --config /tmp/test-config.json
```

### 7. Commit changes

```bash
git add .
git commit -m "Add feature: description"
```

### 8. Push and create PR

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Testing

### Test structure

```
tests/
├── __init__.py
├── test_config.py      # Config tests
├── test_monitor.py     # Monitor tests (TODO)
├── test_notifier.py    # Notifier tests
└── test_scheduler.py   # Scheduler tests
```

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

**Building app bundle** (future):
```bash
py2app cuenimby/__main__.py
```

### Windows

**Testing notifications**:
```bash
# Install optional dependency
pip install win10toast

# Test
cuenimby --verbose
```

**Building executable** (future):
```bash
pyinstaller cuenimby/__main__.py
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

## Release process

### Version numbering

* **Major** (1.x.x): Breaking changes
* **Minor** (x.1.x): New features, backwards compatible
* **Patch** (x.x.1): Bug fixes

### Release checklist

1. **Update version** in `cuenimby/__init__.py`
2. **Run full test suite**: `pytest`
3. **Test on all platforms** (macOS, Windows, Linux)
