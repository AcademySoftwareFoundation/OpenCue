---
title: "CueGUI: Cuetopia Monitoring System"
layout: default
parent: User Guides
nav_order: 32
linkTitle: "Cuetopia Monitoring Guide"
date: 2025-01-07
description: >
  Comprehensive guide to using Cuetopia monitoring plugins in CueGUI
---

# CueGUI: Cuetopia Monitoring System

CueGUI is the graphical user interface for OpenCue, divided into two main workspace views:

- **Cuetopia**: The artist-focused view for monitoring and managing render jobs
- **CueCommander**: The administrator-focused view for system monitoring and host management

This guide provides comprehensive documentation for Cuetopia, which includes the Monitor Jobs, Monitor Job Details, and Job Graph plugins used by artists and system administrators to track render job progress and troubleshoot issues.

## Table of Contents
1. [Monitor Jobs Plugin](#monitor-jobs-plugin)
   - [Job Color Organization](#job-color-organization)
2. [Monitor Job Details Plugin](#monitor-job-details-plugin)
3. [Job Graph Plugin](#job-graph-plugin)
4. [CueProgBar - Progress Bar Window](#cueprogbar---progress-bar-window)
5. [Filters and Search Capabilities](#filters-and-search-capabilities)
6. [Data Processing and Updates](#data-processing-and-updates)

---

## Monitor Jobs Plugin

**How to Open**: Go to **View/Plugins** > **Cuetopia** > **Monitor Jobs**

The Monitor Jobs plugin is the primary interface for monitoring active and completed render jobs. It provides a comprehensive overview of all jobs with real-time status updates.

![Monitor Jobs Interface](/assets/images/cuegui/cuetopia/cuetopia_monitor_jobs.png)

### Interface Components

#### Top Toolbars

The plugin uses two toolbars organized as follows:

##### First Toolbar (Search and Filter Controls)

1. **Load Button**: Triggers job search based on the text field content
2. **Search Text Field**: Accepts job search patterns:
   - Job names (supports wildcards and regex)
   - Show-shot patterns (e.g., `show-shot-username`)
   - User names to load all jobs for a user
   - Job UUIDs for direct job loading

3. **Clear (Clr) Button**: Clears the search field

4. **Autoload Mine Checkbox**: 
   - When checked, automatically loads jobs owned by the current user
   - Updates on application start and facility changes

5. **Load Finished Checkbox**:
   - Includes finished jobs in search results
   - Limited to jobs finished within the last 3 days
   - Jobs older than 3 days are moved to historical database

6. **Group By Dropdown**:
   - Clear: No grouping (flat list)
   - Dependent: Group by job dependencies
   - Show-Shot: Group by show and shot
   - Show-Shot-Username: Group by show, shot, and username

##### Second Toolbar (Action Buttons)

From left to right:

**Unmonitor** group:
1. **Finished** (eject icon): Removes all finished jobs from monitoring
2. **All** (eject icon): Clears all jobs from the monitor
3. **Selected** (eject icon): Removes selected jobs

**Job Actions**:
4. **Eat Dead Frames** (pac-man icon): Eats all dead frames for selected jobs to free scheduling resources
5. **Retry Dead Frames** (circular arrow): Retries all dead frames for selected jobs
6. **Kill Jobs** (X icon): Kill selected jobs and their running frames
7. **Pause Jobs** (pause icon): Pause selected job
8. **Unpause Jobs** (play icon): Unpause selected jobs

### Job Table Columns

The Monitor Jobs view displays the following columns:

Notes:
- **Dead frames**: Frames that have failed to render due to errors (crashed, timed out, or encountered fatal errors during processing). These frames need to be retried or eaten to proceed.
- **Eaten frames**: Frames manually marked as complete without re-rendering. Used to skip problematic frames that are acceptable as-is, will be fixed in compositing, or are not critical to the final output. This allows the job to continue without being blocked by problematic frames.

| Column | Description                                                                                                                                                                         | Data Source | Update Behavior |
|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|-----------------|
| **Job** | Full job name (show-shot-user_descriptor)                                                                                                                                           | `job.data.name` | Static |
| **State** | Current job state (Finished, In Progress, Paused, Failing, Dependency)                                                                                                              | Calculated from job stats | Real-time |
| **Done/Total** | Succeeded frames / Total frames                                                                                                                                                     | `job_stats.succeeded_frames` / `total_frames` | Real-time |
| **Running** | Number of currently running frames                                                                                                                                                  | `job_stats.running_frames` | Real-time |
| **Dead** | Number of dead/failed frames                                                                                                                                                        | `job_stats.dead_frames` | Real-time |
| **Eaten** | Number of eaten frames | `job_stats.eaten_frames` | On update |
| **Wait** | Number of waiting frames                                                                                                                                                            | `job_stats.waiting_frames` | Real-time |
| **MaxRss** | Maximum memory used by any frame                                                                                                                                                    | `job_stats.max_rss` | On update |
| **Age** | Time since job launch (HH:MM format)                                                                                                                                                | Calculated from `start_time` | Real-time |
| **Launched** | Job launch timestamp                                                                                                                                                                | `job.data.start_time` | Static |
| **Finished** | Job completion timestamp                                                                                                                                                            | `job.data.stop_time` | On completion |
| **Progress** | Visual progress bar                                                                                                                                                                 | Composite of all frame states | Real-time |

#### Additional Columns (Hidden by Default)

- **Comment Icon**: Shows if job has comments
- **Autoeat Icon**: Displays pac-man icon if auto-eating is enabled

### Job State Determination

The job state displayed follows this priority logic:

1. **Finished**: Job has completed all frames
2. **Paused**: Job is manually paused
3. **Failing**: Job has dead frames
4. **Dependency**: All pending frames are waiting on dependencies
5. **In Progress**: Default running state

### Progress Bar Visualization

The progress bar uses color coding to represent frame states:
- 🟢 **Green**: Successfully completed frames
- 🟡 **Yellow**: Currently running frames
- 🔴 **Red**: Dead/failed frames
- 🟣 **Purple**: Frames waiting on dependencies
- 🔵 **Light Blue**: Frames waiting to be dispatched

### Right-Click Context Menu

Right-clicking on a job provides these actions:
- View job details
- Manage dependencies
- Modify job properties
- Kill/pause/resume job
- Eat/retry frames
- Add comments
- Use local cores
- Set user color (see [Job Color Organization](#job-color-organization))

### Job Color Organization

The Monitor Jobs view allows you to organize jobs visually by applying background colors. This feature is particularly useful when working with many concurrent renders, allowing you to group jobs by project, priority, department, or any other categorization scheme.

#### Setting Job Colors

To apply a color to one or more jobs:

1. **Select Jobs**: Click on a job or use Ctrl+click to select multiple jobs
2. **Right-Click**: Open the context menu
3. **Choose Color**: Navigate to "Set user color" submenu

![Set User Color Menu with 15 Options](/assets/images/cuegui/cuetopia/job_user_colors_set_user_color_with_15_color_options.png)

#### Available Color Options

The system provides **15 predefined colors** with descriptive names:

- **Set Color 1 - Dark Blue**
- **Set Color 2 - Dark Yellow**  
- **Set Color 3 - Dark Green**
- **Set Color 4 - Dark Brown**
- **Set Color 5 - Purple**
- **Set Color 6 - Teal**
- **Set Color 7 - Orange**
- **Set Color 8 - Maroon**
- **Set Color 9 - Forest Green**
- **Set Color 10 - Lavender**
- **Set Color 11 - Crimson**
- **Set Color 12 - Navy**
- **Set Color 13 - Olive**
- **Set Color 14 - Plum**
- **Set Color 15 - Slate**

#### Custom Color Option

For complete flexibility, use the **"Set Custom Color (RGB)..."** option to create any color:

1. Select jobs and choose "Set Custom Color (RGB)..." from the menu
2. Enter RGB values (0-255 range) using the spinboxes
3. Preview the color in real-time as you adjust values
4. Click OK to apply the custom color

![Custom Color Dialog](/assets/images/cuegui/cuetopia/job_user_colors_set_user_color_with_set_custom_color.png)

#### Color Management

- **Clear Colors**: Use "Clear" option to remove color assignments
- **Persistent Colors**: Color assignments are saved and restored across CueGUI sessions
- **Multiple Selection**: Apply colors to multiple jobs simultaneously
- **Visual Organization**: Colors appear as background highlighting in the job list

#### Best Practices for Color Organization

- **Consistent Scheme**: Develop a facility-wide color coding standard
- **Project-Based**: Use different colors for different shows or projects
- **Priority-Based**: Use warmer colors (red, orange) for urgent jobs, cooler colors (blue, green) for routine work
- **Department-Based**: Assign colors by department (lighting, compositing, effects)
- **Status-Based**: Use colors to indicate job status or approval stages

---

## Monitor Job Details Plugin

**How to Open**: Go to **View/Plugins** > **Cuetopia** > **Monitor Job Details**

The Monitor Job Details plugin provides detailed information about a selected job's layers and frames. It can be opened manually from the menu or appears automatically when you double-click a job in the Monitor Jobs view.

![Job Details Interface](/assets/images/cuegui/cuetopia/cuetopia_monitor_jobs_details.png)

### Layout Structure

The plugin uses a vertical splitter with two main sections:

#### Top Section: Layer Monitor

Displays all layers in the selected job with the following columns:

| Column | Description | Data Processing |
|--------|-------------|-----------------|
| **Name** | Layer name (e.g., test_layer) | Direct from `layer.data.name` |
| **Services** | Services/applications used (e.g., shell) | Comma-joined list |
| **Limits** | Applied resource limits | Comma-joined list |
| **Range** | Frame range (e.g., 1-10) | With chunking info if applicable |
| **Cores** | Core requirement | Shows "ALL" for 0, "ALL-n" for negative |
| **Memory** | Memory reservation | Formatted as human-readable (e.g., 256M) |
| **Gpus** | GPU requirement | Integer count |
| **Gpu Memory** | GPU memory reservation | Formatted as human-readable |
| **MaxRss** | Peak memory usage | Historical maximum |
| **Total** | Total frame count | From `layer_stats.total_frames` |
| **Done** | Completed frames | From `layer_stats.succeeded_frames` |
| **Run** | Running frames | From `layer_stats.running_frames` |
| **Depend** | Dependent frames | From `layer_stats.depend_frames` |
| **Wait** | Waiting frames | From `layer_stats.waiting_frames` |
| **Eaten** | Eaten frames | From `layer_stats.eaten_frames` |
| **Dead** | Dead frames | From `layer_stats.dead_frames` |
| **Avg** | Average frame time | Formatted as HH:MM:SS |
| **Tags** | Resource tags | Pipe-separated list |
| **Progress** | Visual progress bar | Percentage complete |
| **Timeout** | Frame timeout | In HH:MM format |
| **Timeout LLU** | Last log update timeout | In HH:MM format |

#### Bottom Section: Frame Monitor

Shows detailed frame information with filtering controls:

##### Control Bar (Top of Frame Section)

1. **Refresh Button**: Manual refresh of frame list
2. **Clear Button**: Clears all active filters
3. **Page Navigation**: 
   - Previous (<) and Next (>) buttons
   - Page counter (e.g., "Page 1 of 1")
   - Limited to 500 frames per page

4. **Select Status Dropdown**: Quick selection by frame state
5. **Filter Layers Dropdown**: Filter frames by specific layers
6. **Filter Status Dropdown**: Filter by frame status

##### Frame Table Columns

| Column | Description | Special Handling |
|--------|-------------|------------------|
| **Order** | Dispatch order within layer | Sort priority |
| **Frame** | Frame number | Integer display |
| **Layer** | Parent layer name | Links to layer |
| **Status** | Frame state (SUCCEEDED, RUNNING, etc.) | Color-coded |
| **Cores** | Cores used/reserved | Decimal for running frames |
| **GPUs** | GPUs used | Integer count |
| **Host** | Current/last host | Hostname or "0K" if none |
| **Retries** | Retry count | Cumulative |
| **CheckP** | Checkpoint count | For resumable frames |
| **Runtime** | Frame runtime | HH:MM:SS format |
| **LLU** | Last log update | Time since last log write |
| **Memory** | Memory usage | Current if running, peak if not |
| **GPU Mem** | GPU memory usage | Current if running, peak if not |
| **Remain** | Estimated time remaining | Based on historical data |
| **Start Time** | Frame start timestamp | MM/DD HH:MM |
| **Stop Time** | Frame completion timestamp | MM/DD HH:MM |
| **Last Line** | Last log line | Truncated to fit |

### Frame Status Color Coding

Frames are color-coded by status:
- 🟢 **Green**: SUCCEEDED
- 🟡 **Yellow**: RUNNING
- 🔵 **Blue**: WAITING
- 🟣 **Purple**: DEPEND
- 🔴 **Red**: DEAD
- ⚫ **Gray**: EATEN

---

## Job Graph Plugin

**How to Open**: Go to **View/Plugins** > **Cuetopia** > **Job Graph**

The Job Graph plugin provides a visual node-based representation of job layers and their dependencies.

![Job Graph Interface](/assets/images/cuegui/cuetopia/cuetopia_job_graph.png)

### Graph Features

#### Node Representation

Each layer is displayed as a node with:
- **Node Color**: Reflects layer state
  - 🟢 **Green**: All frames completed
  - 🟡 **Yellow**: Frames running
  - 🔴 **Red**: Has dead frames
  - 🔵 **Blue**: Waiting for resources
  - 🟣 **Purple**: Waiting on dependencies
  - ⚫ **Gray**: Dependent on other layers

- **Node Information**:
  - Layer name
  - Frame count (done/total)
  - Running count
  - Progress bar

#### Dependency Connections

- **Arrows**: Show dependency flow
- **Direction**: Parent -> Child relationships
- **Line Style**: Solid for active dependencies

### Interaction

- **Selection**: Click to select layers
- **Multi-select**: Ctrl+click for multiple
- **Pan**: Middle-mouse drag
- **Zoom**: Mouse wheel
- **Auto-layout**: Automatically arranges nodes

### Context Menu

Right-click on nodes provides:
- View/modify dependencies
- Layer properties
- Frame management actions
- Resource allocation

---

## CueProgBar - Progress Bar Window

CueProgBar is a lightweight, standalone progress monitoring window that provides a visual representation of job frame status. It offers a minimalist interface for quick job monitoring without the overhead of the full CueGUI application.

### Launching CueProgBar

From CueGUI Job Context Menu:
   - Right-click on any job in the Monitor Jobs view
   - Select "Show Progress Bar" from the context menu
   - A separate progress bar window opens for that job

### Interface Overview

![CueProgBar Window Interface](/assets/images/cuegui/cueprogbar/cueprogbar_window.png)

The CueProgBar window consists of three main components:

1. **Visual Progress Bar**: A horizontal bar showing frame states through color coding
2. **Status Label**: Displays current progress (e.g., "150 of 200 done, 10 running")
3. **Job Name Label**: Shows the full job name

### Frame State Color Coding

The progress bar uses distinct colors to represent different frame states:

| State | Color | Description |
|-------|-------|-------------|
| **SUCCEEDED** | Green (#37C837) | Frames that completed successfully |
| **RUNNING** | Yellow (#C8C837) | Frames currently being processed |
| **WAITING** | Light Blue (#87CFEB) | Frames ready to run when resources are available |
| **DEPEND** | Purple (#A020F0) | Frames waiting on dependencies |
| **DEAD** | Red (#FF0000) | Frames that failed and exceeded retry attempts |
| **EATEN** | Dark Red (#960000) | Frames manually marked as complete |

![CueProgBar Color Legend](/assets/images/cuegui/cueprogbar/cueprogbar_colors.png)

### Interactive Features

#### Left-Click Menu

Clicking the left mouse button on the progress bar displays a breakdown of frame states:

![CueProgBar Frame Status Menu](/assets/images/cuegui/cueprogbar/cueprogbar_left_click.png)

- Shows count for each frame state
- Color-coded icons match the progress bar colors
- Only displays states with non-zero counts

#### Right-Click Context Menu

Right-clicking the progress bar reveals job control actions:

![CueProgBar Context Menu](/assets/images/cuegui/cueprogbar/cueprogbar_right_click.png)

Available actions include:

1. **Pause/Unpause Job**:
   - Toggles job execution state
   - Paused jobs show "Paused" overlay on the progress bar
   - Prevents new frames from starting while allowing running frames to complete

2. **Retry Dead Frames** (NEW):
   - Appears only when dead frames exist
   - Shows confirmation dialog with dead frame count
   - Retries all frames in DEAD state
   - Displays success/failure notification

   ![Retry Dead Frames Confirmation](/assets/images/cuegui/cueprogbar/cueprogbar_retry_confirm.png)

3. **Kill Job**:
   - Terminates the job and all running frames
   - Requires confirmation dialog
   - Logs the action with username and timestamp

### Window Features

#### Auto-Update
- Refreshes every 5 seconds (configurable)
- Updates frame counts and progress bar in real-time
- Stops updating when job completes

#### Window Title
The window title dynamically updates to show:
- **Percentage**: "75% job_name" (for running jobs)
- **DONE**: "DONE job_name" (for completed jobs)
- **ERR**: "ERR job_name" (when dead frames exist and no frames are running)

#### Visual Indicators
- **COMPLETE** overlay: Displayed when job finishes successfully
- **Paused** overlay: Shown when job is paused
- **Job Not Found** message: Appears if job is deleted or becomes inaccessible

### Use Cases

CueProgBar is ideal for:

1. **Quick Monitoring**: Artists who want to monitor specific jobs without full CueGUI
2. **Multi-Job Tracking**: Opening multiple progress bars for different jobs simultaneously
3. **Desktop Integration**: Minimal windows that can be arranged on secondary monitors
4. **Resource Efficiency**: Lower memory and CPU usage compared to full CueGUI

### Technical Details

#### Memory Usage
- Minimal memory footprint
- No layer or frame detail caching
- Simple RPC calls for job statistics only

#### Update Mechanism
```python
# Update cycle (every 5 seconds)
1. Fetch job statistics via RPC
2. Calculate frame state totals
3. Repaint progress bar
4. Update labels and title
```

### Best Practices

1. **Multiple Windows**: Open separate progress bars for critical jobs
2. **Window Arrangement**: Stack vertically for space-efficient monitoring
3. **Close When Done**: Windows can be safely closed without affecting jobs
4. **Retry Strategy**: Use "Retry Dead Frames" before marking jobs complete

---

## Filters and Search Capabilities

### Job Search Patterns

The search field supports multiple pattern types:

1. **Direct Job Name**: `testing-test_shot-username_test_job_name`
2. **Show-Shot Pattern**: `testing-test_shot`
3. **Username**: `username` (loads all user's jobs)
4. **Regular Expression**: `test.*shot.*`
5. **Job UUID**: `Job.f156be87-987a-48b9-b9da-774cd58674a3`

### Frame Filtering

#### Status Filters
- SUCCEEDED: Completed frames
- RUNNING: Currently executing
- WAITING: Ready to run
- DEPEND: Waiting on dependencies
- DEAD: Failed frames
- EATEN: Manually marked complete

#### Layer Filters
- Single layer selection
- Multiple layer selection (Ctrl+click)
- Applied via dropdown or double-click

#### Range Selection
- Visual slider at bottom of frame monitor
- Click and drag to select range
- Updates frame display in real-time

### Filter Combination

Filters are applied cumulatively:
1. Layer filter (if set)
2. Status filter (if set)
3. Range filter (if set)
4. Results limited to 500 frames

---

## Data Processing and Updates

### Update Mechanisms

#### Automatic Updates
- **Job Monitor**: 10-second refresh cycle
- **Layer Monitor**: Updates with job selection
- **Frame Monitor**: Updates on layer changes
- **Job Graph**: 20-second refresh cycle

#### Manual Updates
- Refresh button (available in each view)
- Updates on user actions
- Forced refresh on filter changes

### RPC Call Optimization

Each field update involves specific RPC calls to Cuebot:

1. **Job Data**: Single `getJob()` call retrieves:
   - Basic job properties
   - Job statistics
   - State information

2. **Layer Data**: `getLayers()` call fetches:
   - All layers for a job
   - Layer statistics
   - Resource requirements

3. **Frame Data**: `getFrames()` with search criteria:
   - Paginated results (500 frame limit)
   - Filtered by status/layer
   - Includes runtime statistics

### Performance Considerations

#### Caching Strategy
- Job list cached for session
- Layer data refreshed on job change
- Frame data paginated for performance
- Log data cached for 15 seconds

#### Memory Management
- Finished jobs removed after 3 days
- Maximum 200 jobs restored on startup
- Weak references prevent memory leaks
- Virtual scrolling for large lists

### Data Flow Architecture

```
User Action → CueGUI Widget → RPC Client → Cuebot Server → Database
                ↓                              ↓
           Local Cache ← ← ← ← ← ← ← Response Data
                ↓
           UI Update → Signal Emission → Connected Widgets Update
```

### Error Handling

- **Connection Loss**: Graceful degradation with cached data
- **RPC Failures**: Automatic retry with exponential backoff
- **Invalid Data**: Validation and sanitization at widget level
- **Performance Issues**: Pagination and lazy loading

---

## Best Practices

### Efficient Monitoring

1. **Use filters** to reduce data volume
2. **Group dependent jobs** for cleaner display
3. **Close unused detail views** to reduce updates
4. **Limit frame monitor** to relevant layers

### Troubleshooting Tips

1. **Slow updates**: Check network connection to Cuebot
2. **Missing jobs**: Verify within 3-day threshold
3. **Filter issues**: Use Clear button to reset
4. **Graph layout**: Use auto-layout to reorganize

### Mouse and Keyboard Interactions

- **Space**: Trigger updates across all views
- **Ctrl+Click**: Multi-select items in lists and tables
- **Double-click**: Open job details, frame logs, or other detailed views

---

## Advanced Features

### Custom Column Configuration

Users can customize displayed columns:
1. Right-click column headers
2. Select columns to show/hide
3. Drag to reorder columns
4. Resize by dragging borders

### Settings Persistence

CueGUI saves user preferences:
- Column configurations
- Filter settings
- Window layouts
- Search history
- Job monitoring list

Settings stored in: `~/.config/opencue/cuegui.ini`

### Plugin Integration

Cuetopia plugins integrate with other CueGUI components:
- **Log Viewer**: Double-click frames to view logs
- **Host Monitor**: View hosts running frames
- **Dependency Editor**: Modify job dependencies
- **Local Booking**: Allocate local resources

## References

### Related Documentation

- [CueGUI: CueCommander Administration System](/docs/user-guides/cuecommander-administration-guide)
