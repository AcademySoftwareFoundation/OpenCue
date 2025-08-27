---
title: "Cuetopia Technical Reference"
layout: default
parent: "Developer Guide"
nav_order: 58
linkTitle: "Cuetopia Technical Reference"
date: 2025-01-07
description: >
  Technical documentation for Cuetopia plugin architecture, data flow, and RPC communication
---

# Cuetopia Technical Reference

This document provides detailed technical information about the Cuetopia monitoring system's internal architecture, data processing, and RPC communication patterns.

## Architecture Overview

Cuetopia consists of three main plugins that communicate through Qt signals and share data via RPC calls to the Cuebot server.

```
┌─────────────────────────────────────────────────────────┐
│                     CueGUI Application                   │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Monitor Jobs │  │ Job Details  │  │  Job Graph   │  │
│  │    Plugin    │←→│    Plugin    │←→│    Plugin    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         ↓                  ↓                 ↓          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              RPC Communication Layer              │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────┘
                          ↓
                    ┌──────────┐
                    │  Cuebot  │
                    │  Server  │
                    └──────────┘
```

## Plugin Components

### Monitor Jobs Plugin (`MonitorJobsPlugin.py`)

#### Class Structure
```python
MonitorJobsDockWidget (Main container)
├── JobMonitorTree (Tree widget)
│   ├── JobWidgetItem (Individual job items)
│   ├── MenuActions (Context menus)
│   └── ItemDelegate (Custom rendering)
├── JobRegexLoadEditBox (Search field)
└── JobLoadFinishedCheckBox (Filter control)
```

#### Key Methods and Data Flow

1. **Job Loading Process**
```python
_regexLoadJobsHandle() -> opencue.api.getJobs() -> addJob() -> JobWidgetItem creation
```

2. **Update Cycle**
```python
Timer (10s) -> _update() -> updateItem() -> RPC calls -> UI refresh
```

3. **State Calculation**
```python
displayState(job):
    if job.data.state == FINISHED: return "Finished"
    if job.data.is_paused: return "Paused"
    if job.data.job_stats.dead_frames > 0: return "Failing"
    if all_pending_are_dependent: return "Dependency"
    return "In Progress"
```

### Monitor Job Details Plugin (`MonitorJobDetailsPlugin.py`)

#### Component Architecture

```python
MonitorLayerFramesDockWidget
├── LayerMonitorTree
│   ├── LayerWidgetItem
│   └── Layer statistics processing
└── FrameMonitor
    ├── FrameMonitorTree
    ├── FrameRangeSelection
    └── Filter controls
```

#### Frame Data Processing

1. **Frame Loading**

```python
setJob(job) -> job.getFrames(search) -> FrameWidgetItem creation

Search parameters:
    - limit: 500 frames
    - offset: page * 500
    - status_filter: selected states
    - layer_filter: selected layers
```

2. **Log Data Buffering**

```python
FrameLogDataBuffer:
    - Caches last log line
    - Calculates LLU (Last Log Update)
    - 15-second cache timeout
    - Thread pool for async reads
```

3. **ETA Calculation**
```python
FrameEtaDataBuffer:
    - Historical frame times
    - Rolling average calculation
    - Per-layer estimations
    - Updates every 30 seconds
```

### Job Graph Plugin (`MonitorJobGraphPlugin.py`)

#### Graph Construction
```python
createGraph():
    for layer in job.getLayers():
        node = CueLayerNode(layer)
        graph.add_node(node)
    
    for node in graph.nodes:
        for depend in node.getWhatDependsOnThis():
            child = graph.get_node(depend.dependErLayer())
            child.set_input(node.output)
```

#### Node Updates
```python
update() -> job.getLayers() -> node.setRpcObject(layer) -> visual refresh
Update frequency: 20 seconds
```

## RPC Communication Patterns

### Job Data Retrieval

#### Basic Job Information

```python
# Single job fetch
job = opencue.api.findJob(job_name)
Returns: Job object with nested data structure

# Multiple jobs with pattern
jobs = opencue.api.getJobs(regex=["pattern"], include_finished=True)
Returns: List of Job objects
```

#### Job Data Structure

```protobuf
Job {
    JobData data {
        string name
        string id
        State state
        bool is_paused
        int64 start_time
        int64 stop_time
        bool has_comment
        bool auto_eat
    }
    JobStats job_stats {
        int32 total_frames
        int32 succeeded_frames
        int32 running_frames
        int32 dead_frames
        int32 eaten_frames
        int32 waiting_frames
        int32 depend_frames
        int64 max_rss
    }
}
```

### Layer Data Access

#### Layer Fetching

```python
layers = job.getLayers()
Returns: List of Layer objects with statistics
```

#### Layer Data Structure

```protobuf
Layer {
    LayerData data {
        string name
        string range
        int32 chunk_size
        int32 dispatch_order
        repeated string services
        repeated string limits
        float min_cores
        int64 min_memory
        int32 min_gpus
        int64 min_gpu_memory
        repeated string tags
        int32 timeout
        int32 timeout_llu
    }
    LayerStats layer_stats {
        int32 total_frames
        int32 succeeded_frames
        int32 running_frames
        int32 dead_frames
        int32 eaten_frames
        int32 waiting_frames
        int32 depend_frames
        int64 max_rss
        float avg_frame_sec
    }
}
```

### Frame Data Operations

#### Frame Search
```python
frames = job.getFrames(
    status=["RUNNING", "DEAD"],   # Status filter
    layer=["layer_name"],         # Layer filter
    offset=0,                     # Pagination offset
    limit=500                     # Max results
)
```

#### Frame Data Fields
```protobuf
Frame {
    FrameData data {
        int32 number
        string layer_name
        int32 dispatch_order
        State state
        string frame_state_display_override
        int32 retry_count
        string last_resource
        int64 start_time
        int64 stop_time
        int64 used_memory
        int64 max_rss
        int64 used_gpu_memory
        int64 max_gpu_memory
        CheckpointState checkpoint_state
        int32 checkpoint_count
    }
}
```

## Data Update Strategies

### Pull-Based Updates

1. **Timer-Driven Refresh**

```python
QTimer -> timeout signal -> _update() method -> RPC calls
Intervals:
    - Job Monitor: 10 seconds
    - Frame Monitor: On demand
    - Job Graph: 20 seconds
```

2. **Event-Driven Updates**

```python
User action -> Signal emission -> Connected slots -> RPC refresh
Examples:
    - Job selection -> view_object signal
    - Filter change -> immediate refresh
    - Manual refresh -> F5 key handler
```

### Optimization Techniques

#### Batch Operations

```python
# Instead of individual calls
for job_id in job_ids:
    job = opencue.api.getJob(job_id)
    
# Use batch retrieval
jobs = opencue.api.getJobs(id=job_ids)
```

#### Differential Updates

```python
# Only update changed fields
if new_data.job_stats != cached_data.job_stats:
    update_statistics_display()
```

#### Lazy Loading

```python
# Load only visible items
visible_range = tree.visibleRange()
for item in visible_range:
    item.updateData()
```

## Memory Management

### Object Lifecycle

1. **Job Proxy Storage**

```python
class JobMonitorTree:
    def __init__(self):
        self.__jobTimeLoaded = {}  # Job ID → timestamp
        self.__jobs = {}           # Job ID → Job proxy
        
    def addJob(self, job_id, timestamp):
        if self.isExpired(timestamp):
            return  # Don't load expired jobs
        self.__jobs[job_id] = opencue.api.getJob(job_id)
```

2. **Weak References**

```python
# Prevent circular references
self.parent = weakref.proxy(parent)
```

3. **Cache Expiration**

```python
JOB_RESTORE_THRESHOLD_DAYS = 3
JOB_RESTORE_THRESHOLD_LIMIT = 200

def restoreJobs(self, job_list):
    today = datetime.now()
    for job_id, timestamp in job_list[:LIMIT]:
        if (today - timestamp).days <= THRESHOLD_DAYS:
            self.addJob(job_id)
```

## Signal and Slot Connections

### Core Signals

```python
# Job selection signal
view_object = QtCore.Signal(object)

# Job removal signal
unmonitor = QtCore.Signal(object)

# Facility change signal
facility_changed = QtCore.Signal()

# Layer filter signal
handle_filter_layers_byLayer = QtCore.Signal(list)

# Job changed signal
job_changed = QtCore.Signal()
```

### Signal Flow Example

```python
# User double-clicks job
JobMonitorTree.itemDoubleClicked ->
    emit view_object(job) ->
        MonitorJobDetails.__setJob(job) ->
            LayerMonitorTree.setJob(job)
            FrameMonitor.setJob(job)
        JobGraph.setJob(job) ->
            createGraph()
```

## Performance Metrics

### RPC Call Frequency

| Operation | Frequency | Data Volume |
|-----------|-----------|-------------|
| Job list refresh | 10 seconds | ~50-200 jobs |
| Layer fetch | On job selection | ~5-50 layers |
| Frame fetch | On demand | 500 frames max |
| Log read | On frame click | Single file |
| Graph update | 20 seconds | Layer count |

### Memory Usage

| Component | Typical Usage | Maximum |
|-----------|--------------|---------|
| Job cache | 10-50 MB | 200 MB |
| Frame data | 5-20 MB | 100 MB |
| Log buffer | 1-5 MB | 20 MB |
| Graph nodes | 1-10 MB | 50 MB |

## Configuration Files

### Settings Storage

Location: `~/.config/opencue/cuegui.ini`

```ini
[MonitorJobs]
columnWidths = 470,20,20,80,90,60,50,50,60,55,50,100,100,0
columnVisibility = true,true,true,true,true,true,true,true,true,true,true,true,true,true
jobs = Job.id1:timestamp,Job.id2:timestamp
loadFinished = false
grpDependentCb = true
autoLoadMineCb = true

[MonitorJobDetails]
splitterSize = 300,400
frameColumnWidths = 60,70,250,100,55,55,120,55,20,55,70,70,60,60,70,100,100,0
layerColumnWidths = 0,250,100,100,150,45,60,45,40,60,40,40,40,53,40,40,40,65,100,100,45,45
```

## Error Handling

### RPC Error Recovery

```python
def safeRpcCall(func, *args, **kwargs):
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except opencue.EntityNotFoundException:
            logger.warning(f"Entity not found: {args}")
            return None
        except opencue.CueException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))
                continue
            logger.error(f"RPC failed: {e}")
            raise
```

### Data Validation

```python
def validateJobName(name):
    # Pattern: show-shot-user_descriptor
    pattern = r'^[a-z0-9_]+-[a-z0-9\.]+-[a-z0-9_]+.*$'
    return re.match(pattern, name, re.IGNORECASE)

def validateFrameRange(range_str):
    try:
        FileSequence.FrameSet(range_str)
        return True
    except:
        return False
```

## Extension Points

### Custom Column Addition

```python
# In JobMonitorTree.__init__()
self.addColumn("CustomField", 100, id=50,
    data=lambda job: job.customData(),
    sort=lambda job: job.customSort(),
    tip="Custom field tooltip"
)
```

### Custom Delegates

```python
class CustomProgressDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        # Custom rendering logic
        progress = index.data()
        # Draw custom progress visualization
```

### Plugin Hooks

```python
# Register custom action
menuActions.addAction("Custom Action", self.customHandler)

# Add to context menu
def customHandler(self, rpcObjects):
    for obj in rpcObjects:
        # Perform custom operation
        pass
```

## Debugging and Profiling

### Enable Debug Logging

```python
# In cuegui/Logger.py
logging.basicConfig(level=logging.DEBUG)
```

### RPC Call Tracing

```python
# Enable RPC debug mode
os.environ['OPENCUE_DEBUG_RPC'] = '1'
```
