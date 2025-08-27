---
title: "CueCommander Technical Reference"
layout: default
parent: Reference
nav_order: 43
linkTitle: "CueCommander Technical Reference"
date: 2025-01-13
description: >
  Technical reference for CueCommander plugins, APIs, and implementation details
---

# CueCommander Technical Reference

This document provides technical details about CueCommander's implementation, plugin architecture, data models, and API interfaces for developers and system integrators.

## Architecture Overview

CueCommander is built on the same Qt-based framework as Cuetopia but loads administrator-specific plugins. Each plugin is a self-contained module that communicates with the OpenCue backend through the Python API.

### Component Architecture

```
CueCommander
├── Main Application (cuegui.Main)
│   ├── MainWindow
│   ├── Plugin Manager
│   └── Settings Manager
├── Plugins
│   ├── AllocationsPlugin
│   ├── LimitsPlugin
│   ├── MonitorCuePlugin
│   ├── MonitorHostsPlugin
│   ├── RedirectPlugin
│   ├── ServicePlugin
│   ├── ShowsPlugin
│   ├── StuckFramePlugin
│   ├── SubscriptionsPlugin
│   └── SubscriptionsGraphPlugin
└── Core Components
    ├── AbstractDockWidget
    ├── AbstractTreeWidget
    └── MenuActions
```

## Plugin Specifications

### AllocationsPlugin

**Module**: `cuegui.plugins.AllocationsPlugin`  
**Widget**: `AllocationsDockWidget`  
**Data Source**: `opencue.api.getAllocations()`

#### Class Structure

```python
class AllocationsDockWidget(AbstractDockWidget):
    - __monitorAllocations: MonitorAllocations
    - pluginRegisterSettings()

class MonitorAllocations(AbstractTreeWidget):
    - Update interval: 60 seconds
    - Drag-drop support: Yes
    - Context menu: Via MenuActions
```

#### Data Model

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| name | str | `alloc.data.name` | Allocation identifier |
| tag | str | `alloc.data.tag` | Allocation tag |
| cores | int | `alloc.data.stats.cores` | Total cores |
| idle | int | `alloc.totalAvailableCores()` | Available cores |
| locked | int | `alloc.totalLockedCores()` | Locked cores |
| hosts | int | `alloc.data.stats.hosts` | Host count |

#### Key Methods

- `_getUpdate()`: Fetches allocation list from Cuebot
- `dragEnterEvent()`: Handles host drag operations
- `dropEvent()`: Processes host reassignment
- `reparentHostIds()`: Moves hosts between allocations

---

### LimitsPlugin

**Module**: `cuegui.plugins.LimitsPlugin`  
**Widget**: `LimitsDockWidget`  
**Data Source**: `opencue.api.getLimits()`

#### Class Structure

```python
class LimitsDockWidget(AbstractDockWidget):
    - __limitsWidget: LimitsWidget
    - pluginRegisterSettings()
```

#### Data Model

| Field | Type | Description |
|-------|------|-------------|
| name | str | Limit identifier |
| max_value | int | Maximum concurrent value |
| current_running | int | Current active count |

#### Operations

- Create: `opencue.api.createLimit(name, max_value)`
- Update: `limit.setMaxValue(value)`
- Delete: `limit.delete()`
- Query: `opencue.api.findLimit(name)`

---

### MonitorCuePlugin

**Module**: `cuegui.plugins.MonitorCuePlugin`  
**Widget**: `MonitorCueDockWidget`  
**Data Source**: `opencue.api.getShows()`, `show.getGroups()`, `group.getJobs()`

#### Class Structure

```python
class MonitorCueDockWidget(AbstractDockWidget):
    - __monitorCue: CueJobMonitorTree
    - __toolbar: QToolBar
    - __showMenuActions: MenuActions
    - __cueStateBar: CueStateBarWidget (optional)
```

#### Tree Hierarchy

```
Show
├── RootGroup
│   ├── Group
│   │   ├── Job
│   │   └── Job
│   └── Group
└── Jobs (ungrouped)
```

#### Update Mechanism

- Default interval: 10 seconds
- Manual refresh: Spacebar
- Smart updates: Only refreshes visible items
- Differential updates: Compares object states

#### Column Data

| Column | Data Source | Update Type |
|--------|-------------|-------------|
| Name | `object.data.name` | Static |
| State | Calculated from stats | Real-time |
| Running | `stats.running_frames` | Real-time |
| Waiting | `stats.waiting_frames` | Real-time |
| Depend | `stats.depend_frames` | Real-time |
| Dead | `stats.dead_frames` | Real-time |
| Cores | `stats.reserved_cores` | Real-time |
| GPUs | `stats.reserved_gpus` | Real-time |

---

### MonitorHostsPlugin

**Module**: `cuegui.plugins.MonitorHostsPlugin`  
**Widget**: `HostMonitorDockWidget`  
**Data Source**: `opencue.api.getHosts()`, `host.getProcs()`

#### Class Structure

```python
class HostMonitorDockWidget(AbstractDockWidget):
    - __monitorHosts: HostMonitor
    - __monitorProcs: ProcMonitor
    - __splitter: QSplitter (vertical)
```

#### Host Data Model

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| name | str | `host.data.name` | Host FQDN |
| load | float | `host.data.load` | Load average |
| cores | int | `host.data.cores` | Core count |
| memory | int | `host.data.memory` | Total memory |
| state | enum | `host.data.state` | UP/DOWN/REPAIR |
| locked | bool | `host.data.lock_state` | Lock status |
| alloc | str | `host.data.alloc_name` | Allocation |

#### Proc Data Model

| Field | Type | Description |
|-------|------|-------------|
| frame_name | str | Running frame |
| job_name | str | Parent job |
| cores | float | Allocated cores |
| memory | int | Memory usage |
| runtime | int | Seconds running |

#### Host States

```python
class HostState(Enum):
    UP = 0
    DOWN = 1
    REPAIR = 4

class LockState(Enum):
    OPEN = 0
    LOCKED = 1
    NIMBY_LOCKED = 2
```

---

### RedirectPlugin

**Module**: `cuegui.plugins.RedirectPlugin`  
**Widget**: `RedirectWidget`  
**Core Class**: `cuegui.Redirect.RedirectWidget`

#### Redirect Algorithm

```python
def redirect_procs(source_job, target_job, filters):
    """
    1. Get procs from source_job matching filters
    2. Check target_job can accept procs
    3. Call proc.redirectTo(target_job)
    4. Return redirect count
    """
```

#### Filter Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| allocations | list | [] | Target allocations |
| min_cores | int | 1 | Minimum cores |
| max_cores | int | None | Maximum cores |
| min_memory | int | 0 | Memory threshold MB |
| proc_hour_cutoff | float | 0 | Min runtime hours |
| services | list | [] | Required services |

---

### ServicePlugin

**Module**: `cuegui.plugins.ServicePlugin`  
**Widget**: `ServicesDockWidget`  
**Data Source**: `opencue.api.getDefaultServices()`

#### Service Configuration Model

```python
class ServiceConfig:
    name: str                   # Service identifier
    threadable: bool            # Threading support
    min_threads: int            # Min threads (x100)
    max_threads: int            # Max threads (x100)
    min_memory_mb: int          # Min RAM MB
    min_gpu_memory_mb: int      # Min GPU MB
    timeout: int                # Minutes
    timeout_llu: int            # LLU timeout
    oom_increase_mb: int        # OOM adjustment
    tags: List[str]             # Service tags
```

#### Service Operations

- Create: `opencue.api.createService(config)`
- Update: `service.update(config)`
- Delete: `service.delete()`
- Query: `opencue.api.findService(name)`

---

### ShowsPlugin

**Module**: `cuegui.plugins.ShowsPlugin`  
**Widget**: `ShowsDockWidget`  
**Data Source**: `opencue.api.getShows()`

#### Show Data Model

| Field | Type | Description |
|-------|------|-------------|
| name | str | Show identifier |
| active | bool | Active status |
| default_min_cores | float | Min cores per frame |
| default_max_cores | float | Max cores per frame |
| reservations | list | Host reservations |
| stats | ShowStats | Runtime statistics |

#### Show Creation

```python
def create_show(name, allocations):
    show = opencue.api.createShow(name)
    for alloc in allocations:
        show.createSubscription(alloc, size, burst)
    return show
```

---

### StuckFramePlugin

**Module**: `cuegui.plugins.StuckFramePlugin`  
**Widget**: `StuckWidget`  
**Detection Algorithm**: Time-based heuristics

#### Detection Criteria

```python
class StuckFrameFilter:
    service: str                # Service filter
    exclude_regex: str          # Exclusion pattern
    percent_since_llu: float    # % runtime since LLU
    min_llu: int               # Min seconds since LLU
    percent_avg_time: float    # % of average time
    min_runtime: int           # Min total runtime
    enabled: bool              # Filter active
```

#### Frame Analysis

1. **LLU Check**: Time since last log update
2. **Runtime Check**: Compare to average completion
3. **Pattern Match**: Check against known issues
4. **Service Filter**: Apply service-specific rules

---

### SubscriptionsPlugin

**Module**: `cuegui.plugins.SubscriptionsPlugin`  
**Widget**: `SubscriptionDockWidget`  
**Data Source**: `show.getSubscriptions()`

#### Subscription Model

```python
class Subscription:
    show: Show                  # Parent show
    allocation: Allocation      # Target allocation
    size: int                  # Guaranteed cores
    burst: int                 # Burst capacity
    priority: int              # Subscription priority
```

#### Subscription Operations

- Create: `show.createSubscription(alloc, size, burst)`
- Update: `sub.setSize(size)`, `sub.setBurst(burst)`
- Delete: `sub.delete()`
- Query: `show.getSubscriptions()`

---

### SubscriptionsGraphPlugin

**Module**: `cuegui.plugins.SubscriptionsGraphPlugin`  
**Widget**: `SubscriptionGraphDockWidget`  
**Visualization**: Qt-based bar graphs

#### Graph Components

```python
class SubscriptionGraph:
    - Shows dropdown selector
    - Allocation bars (horizontal)
    - Usage indicators (filled portion)
    - Burst visualization (extended bars)
    - Color coding by allocation
```

#### Data Updates

- Refresh interval: 5 seconds
- Data source: Combined subscription/allocation stats
- Calculation: `usage = running_cores / subscription_size`

---

## Event System

CueCommander uses Qt signals/slots for event handling:

### Application Events

| Signal | Description | Handlers |
|--------|-------------|----------|
| `facility_changed` | Facility switch | All plugins refresh |
| `view_object` | Object view request | Opens relevant plugin |
| `job_changed` | Job selection | Updates dependent views |
| `host_changed` | Host selection | Updates proc view |

### Plugin Events

```python
# Example event connection
self.app.facility_changed.connect(self.refresh)
self.tree.itemSelectionChanged.connect(self.selectionChanged)
```

---

## Performance Considerations

### Update Strategies

1. **Differential Updates**: Only update changed items
2. **Lazy Loading**: Load data on-demand
3. **Update Intervals**: Configurable per plugin
4. **Batch Operations**: Group API calls

### Memory Management

```python
# Plugins implement cleanup
def cleanup(self):
    self.timer.stop()
    self.clearItems()
    self.disconnect_signals()
```

### Threading

- Main GUI thread for UI updates
- Worker threads for API calls
- ThreadPool size: 3 (default)

---

## Configuration

### Settings Storage

Location: `~/.config/opencue/cuegui.ini`

```ini
[CueCommander]
AllocationsOpen=true
MonitorCueOpen=true
UpdateInterval=10
AutoRefresh=true

[Allocations]
columnVisibility=1,1,1,1,0,0,1,1
columnOrder=0,1,2,3,4,5,6,7
columnWidths=150,100,50,50,65,55,65,55

[MonitorCue]
shows=production,testing
expandGroups=false
showFinished=false
```

### Plugin Registration

```python
PLUGIN_NAME = "PluginName"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "Description"
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = "WidgetClass"
```

---

## API Integration

### OpenCue Python API

All plugins use the OpenCue Python API:

```python
import opencue

# API initialization handled by framework
# Plugins access through opencue.api namespace
```

### Common API Patterns

```python
# List operations
allocations = opencue.api.getAllocations()
hosts = opencue.api.getHosts()
shows = opencue.api.getShows()

# Find operations
job = opencue.api.findJob("show-shot-user_v001")
host = opencue.api.findHost("rendernode01")

# Modification operations
job.kill()
host.lock()
allocation.reparentHosts(host_list)
```

---

## Extension Points

### Custom Plugins

Create custom CueCommander plugins:

```python
from cuegui.AbstractDockWidget import AbstractDockWidget

class CustomPlugin(AbstractDockWidget):
    def __init__(self, parent):
        super().__init__(parent, "CustomPlugin")
        # Add widgets and logic
```

### Menu Actions

Extend context menus:

```python
from cuegui.MenuActions import MenuActions

self.menu_actions = MenuActions(self, self.update, self.selection)
self.menu_actions.addAction("Custom Action", self.customHandler)
```

### Custom Filters

Add filtering capabilities:

```python
class CustomFilter:
    def matches(self, item):
        # Return True if item matches filter
        return custom_logic(item)
```

---

## Security Considerations

### Permission Model

- Read: All authenticated users
- Write: Requires admin role
- Delete: Requires admin role
- Service modification: Requires admin role

### Audit Logging

Operations logged to Cuebot:
- Allocation changes
- Service modifications
- Job kills
- Host state changes
- Show creation/deletion

### Best Practices

1. Validate all user input
2. Use API permission checks
3. Log administrative actions
4. Implement confirmation dialogs
5. Rate limit refresh operations

---

## Debugging

### Debug Mode

Enable debug logging:

```bash
export CUEGUI_LOG_LEVEL=DEBUG
cuecommander
```

### Common Debug Points

```python
import cuegui.Logger
logger = cuegui.Logger.getLogger(__file__)

logger.debug("Update started")
logger.info("Loaded %d items", count)
logger.warning("Connection timeout")
logger.error("API call failed: %s", error)
```
