---
title: "Using CueGUI for Job Monitoring"
layout: default
parent: Tutorials
nav_order: 49
linkTitle: "Using CueGUI for Job Monitoring" 
date: 2025-01-29
description: >
  Master the CueGUI interface for monitoring jobs, managing frames, and troubleshooting render issues
---

# Using CueGUI for Job Monitoring

CueGUI is the primary desktop application for monitoring and managing OpenCue jobs. This tutorial will teach you how to effectively use CueGUI's features for production render management.

## What You'll Learn

- Navigating the CueGUI interface
- Monitoring job progress and states
- Managing frames and layers
- Using the search and filtering features
- Accessing and interpreting frame logs
- Managing hosts and allocations
- Customizing the interface for your workflow

## Prerequisites

- OpenCue environment with CueGUI installed
- At least one job submitted to the system
- Basic understanding of OpenCue concepts (jobs, layers, frames)

## Launching CueGUI

### Starting CueGUI

```bash
# Launch CueGUI
cuegui

# Launch with specific configuration
cuegui --config /path/to/custom/cuegui.yaml

# Launch with debug logging
cuegui --debug
```

### Initial Setup

1. **Configure Cuebot Connection**:
   - Go to **Edit** → **Preferences** → **Cuebot**
   - Set the Cuebot hostname (default: `localhost`)
   - Test the connection

2. **Set Update Intervals**:
   - **Job Refresh**: 10 seconds (for active monitoring)
   - **Frame Refresh**: 5 seconds (when viewing frame details)

## Main Interface Overview

### Layout Components

CueGUI consists of several key areas:

1. **Menu Bar**: File, Edit, View, Tools, Help
2. **Toolbar**: Quick actions and view toggles
3. **Job List**: Main table showing all jobs
4. **Details Panels**: Show layers and frames for selected jobs
5. **Status Bar**: Connection status and update information

### Default Views

- **Cuetopia**: Job monitoring and artist interface
- **CueCommander**: System administration interface

## Job Monitoring Workflow

### Understanding Job States

Jobs progress through several states:

- **Pending**: Job submitted but not yet dispatched
- **Running**: Frames are actively processing
- **Finished**: All frames completed successfully
- **Dead**: Job encountered errors and stopped

### Job List Management

#### Viewing Jobs

1. **All Jobs View**:
   - Shows all jobs in the system
   - Color-coded by state (Green=Finished, Yellow=Running, Red=Dead)

2. **My Jobs View**:
   ```python
   # Show only your jobs
   Menu: View → Show My Jobs Only
   ```

3. **Job Search**:
   ```
   # Search by job name
   Search box: "render-shot010"
   
   # Search by show
   Search: "show:demo-project"
   
   # Search by user  
   Search: "user:artist01"
   ```

#### Job Information Columns

Key columns to understand:

- **Job Name**: Unique identifier for the job
- **Show/Shot**: Project context
- **User**: Who submitted the job
- **State**: Current job status
- **Progress**: Frames completed/total
- **Runtime**: How long the job has been running
- **Priority**: Job priority (higher numbers run first)

### Monitoring Job Progress

#### Real-time Updates

1. **Auto-refresh**: CueGUI automatically updates job status
2. **Manual Refresh**: Press **F5** or click refresh button
3. **Pause Updates**: Click the pause button to stop auto-refresh

#### Progress Indicators

```
Job Progress: [████████████████████████████████] 100% (240/240)
              |                                |
              └─ Visual progress bar          └─ Completed/Total frames
```

## Layer and Frame Management

### Viewing Layer Details

1. **Select a Job**: Click on a job in the main list
2. **Layer Panel**: Bottom panel shows layers within the job
3. **Layer Information**:
   - Layer name and type
   - Frame range and chunk size
   - Resource requirements
   - Dependency relationships

### Frame-Level Monitoring

#### Frame States

- **Waiting**: Frame queued but not started
- **Running**: Frame currently processing
- **Finished**: Frame completed successfully
- **Dead**: Frame failed and stopped
- **Eaten**: Frame manually marked as complete

#### Frame Details View

1. **Double-click a Layer**: Opens frame details window
2. **Frame Information**:
   - Frame number and state
   - Host assignment
   - Start/end times
   - Resource usage

### Frame Log Analysis

#### Accessing Logs

```
Method 1: Right-click frame → "View Log"
Method 2: Double-click frame → Log tab
Method 3: Select frame → View menu → "Show Log"
```

#### Understanding Log Content

```bash
# Typical log structure
[timestamp] INFO: Frame started on host render01
[timestamp] INFO: Command: /usr/local/blender/blender -b scene.blend -f 001
[timestamp] INFO: Environment: BLENDER_USER_SCRIPTS=/shared/scripts
[timestamp] INFO: Working directory: /shared/projects/demo
[timestamp] INFO: Starting render process...
[timestamp] INFO: Render completed successfully
[timestamp] INFO: Frame finished with exit code 0
```

#### Common Log Patterns

**Successful Frame**:
```
Frame finished with exit code 0
```

**Failed Frame**:
```
Frame failed with exit code 1
ERROR: Could not open scene file
```

**Resource Issues**:
```
WARNING: Low memory detected
ERROR: Out of disk space
```

## Job Management Actions

### Job-Level Actions

Right-click on a job to access:

1. **Kill Job**: Stop all running frames
2. **Pause Job**: Prevent new frames from starting
3. **Resume Job**: Allow paused job to continue
4. **Set Priority**: Change job priority (0-1000)
5. **Show Properties**: View detailed job information

### Frame-Level Actions

Right-click on frames for:

1. **Retry Frame**: Re-run a failed frame
2. **Kill Frame**: Stop a running frame
3. **Eat Frame**: Mark frame as complete (skip)
4. **View Log**: Open frame log viewer

### Bulk Operations

Select multiple frames (Ctrl+click or Shift+click):

```
# Retry all failed frames in a layer
1. Select layer
2. Ctrl+A (select all frames)
3. Right-click → "Retry Dead Frames"

# Kill all running frames
1. Select running frames
2. Right-click → "Kill Frames"
```

## Advanced CueGUI Features

### Host Monitoring

#### Host View

1. **Switch to CueCommander**: View → CueCommander
2. **Host List**: Shows all render nodes
3. **Host Information**:
   - Host name and allocation
   - CPU and memory usage
   - Currently running frames
   - Host state (Up/Down/Repair)

#### Host Filtering

The Host Monitor includes several filtering options:

- **Host Name**: Filter by hostname using regex patterns
- **Allocation**: Filter by host allocation
- **Hardware State**: Filter by UP, DOWN, REPAIR states
- **Lock State**: Filter by OPEN, LOCKED, NIMBY_LOCKED
- **OS**: Filter hosts by operating system (Linux, Windows, macOS, etc.)

The OS filter initially displays "Not Loaded" and dynamically populates with the actual operating systems found in your host environment once hosts are loaded.

#### Host Management

```
Right-click host:
├── Reboot Host
├── Lock/Unlock Host
├── Set Host Tags
└── View Host Details
```

### Custom Views and Layouts

#### Saving Layouts

1. **Arrange Panels**: Resize and position panels as desired
2. **Save Layout**: View → Save Layout As...
3. **Load Layout**: View → Load Layout

#### Custom Columns

1. **Right-click Column Header**: Choose which columns to display
2. **Reorder Columns**: Drag column headers
3. **Sort Options**: Click headers to sort data

### Search and Filtering

#### Advanced Search Syntax

```bash
# Job name contains "render"
name:render

# Jobs from specific show
show:demo-project

# Jobs by user
user:artist01

# Jobs with specific state
state:running

# Jobs with priority above 100
priority:>100

# Combine criteria
show:demo-project AND user:artist01 AND state:running
```

#### Saved Searches

1. **Create Search**: Enter search criteria
2. **Save Search**: Search → Save Search As...
3. **Quick Access**: Saved searches appear in dropdown

## Troubleshooting with CueGUI

### Identifying Problems

#### Job Issues

1. **Job Stuck in Pending**:
   - Check if hosts are available
   - Verify resource requirements
   - Check allocation settings

2. **Frames Failing**:
   - Examine frame logs for error messages
   - Check resource usage patterns
   - Verify file paths and permissions

3. **Slow Performance**:
   - Monitor host resource usage
   - Check network connectivity
   - Review job chunk sizes

#### Host Issues

1. **Host Not Responding**:
   - Check host state in Host view
   - Verify RQD is running on host
   - Test network connectivity

2. **Host Resource Problems**:
   - Monitor memory and CPU usage
   - Check disk space availability
   - Review host configuration

### Performance Optimization

#### CueGUI Settings

```yaml
# ~/.config/opencue/cuegui.yaml
cuegui:
  update_interval: 10  # Seconds between refreshes
  max_jobs_display: 500  # Limit jobs shown
  enable_sound: false  # Disable notification sounds
  
  # Column widths
  columns:
    job_name: 200
    state: 80
    progress: 120
```

#### Workflow Tips

1. **Use Filters**: Don't monitor all jobs simultaneously
2. **Pause Updates**: When analyzing specific issues
3. **Close Unused Views**: Reduce system load
4. **Bookmark Searches**: Save time with common queries

## Integration with Production Pipeline

### Custom Plugins

CueGUI supports custom plugins:

```python
# Example plugin structure
/shared/cuegui/plugins/
├── __init__.py
├── custom_monitor.py
└── production_tools.py
```

### External Tool Integration

#### Launching External Applications

```python
# Add custom menu items
Menu: Tools → Launch RV Player
Menu: Tools → Open Shotgun Page
Menu: Tools → Sync Deadline Jobs
```

## Best Practices

### Daily Monitoring Workflow

1. **Morning Check**:
   - Review overnight jobs
   - Check for failed frames
   - Monitor resource usage

2. **During Production**:
   - Track active job progress
   - Respond to frame failures quickly
   - Manage job priorities

3. **End of Day**:
   - Queue overnight jobs
   - Check resource availability
   - Clean up completed jobs

### Team Collaboration

1. **Shared Views**: Save and share useful layouts
2. **Priority Management**: Coordinate job priorities
3. **Resource Planning**: Monitor allocation usage
4. **Communication**: Use job comments for team updates

## Keyboard Shortcuts

Essential shortcuts for efficient monitoring:

```
F5              - Refresh view
Ctrl+F          - Open search
Ctrl+A          - Select all
Delete          - Kill selected frames
Space           - Pause/resume updates
Ctrl+L          - View frame logs
Ctrl+R          - Retry failed frames
Ctrl+K          - Kill selected items
```

## Next Steps

You've mastered the CueGUI interface for:
- Job and frame monitoring
- Log analysis and troubleshooting  
- Host management and resource monitoring
- Advanced search and filtering
- Production workflow optimization

**Continue your learning**:
- [Managing Jobs and Frames](/docs/tutorials/managing-jobs-frames/) - Advanced job management techniques
- [Creating Multi-Layer Jobs](/docs/tutorials/multi-layer-jobs/) - Complex pipeline workflows
- [DCC Integration Tutorial](/docs/tutorials/dcc-integration/) - Integration with Maya, Blender, etc.

## Troubleshooting CueGUI

### Common Issues

1. **CueGUI Won't Start**:
   ```bash
   # Check Python environment
   python -c "import PySide2"
   
   # Verify OpenCue installation
   python -c "import opencue"
   ```

2. **Connection Problems**:
   ```bash
   # Test Cuebot connectivity
   telnet cuebot-hostname 8443
   ```

3. **Performance Issues**:
   - Reduce update frequency
   - Limit number of displayed jobs
   - Close unused views and panels