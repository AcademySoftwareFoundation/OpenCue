---
title: "CueGUI: CueCommander Administration System"
layout: default
parent: User Guides
nav_order: 26
linkTitle: "CueCommander Administration Guide"
date: 2025-01-13
description: >
  Comprehensive guide to using CueCommander for OpenCue render farm administration
---

# CueGUI: CueCommander Administration System

CueGUI is the graphical user interface for OpenCue, divided into two main workspace views:

- **Cuetopia**: The artist-focused view for monitoring and managing render jobs
- **CueCommander**: The administrator-focused view for system monitoring and host management

CueCommander is the administrator-focused workspace within CueGUI, providing comprehensive tools for managing and monitoring OpenCue render farms. While Cuetopia serves artists and production users, CueCommander empowers system administrators, render wranglers, Production Services and Resources (PSR) team, and pipeline Technical Directors (TDs) with advanced control over allocations, hosts, services, and system resources.

## Introduction

CueCommander is designed for render farm administrators who need deep visibility and control over the OpenCue infrastructure. It provides specialized windows for managing compute resources, troubleshooting issues, and optimizing farm performance. The interface exposes administrative functions that directly affect farm operations, making it essential for maintaining efficient render operations at scale.

### Target Audience

- **System Administrators**: Managing farm infrastructure and resources
- **Render Wranglers / Production Services and Resources (PSR) team**: Monitoring and troubleshooting active jobs and stuck frames
- **Pipeline Technical Directors (TDs)**: Configuring services, limits, and allocations
- **Operations Teams**: Overseeing facility-wide render capacity and subscriptions

### Core Capabilities

- Real-time monitoring of jobs, hosts, and resource allocation
- Management of allocations, limits, and service configurations
- Troubleshooting tools for stuck frames and problematic jobs
- Resource redirection and optimization features
- Subscription management and visualization
- Show configuration and administration

## System Overview

CueCommander shares the same application framework as Cuetopia but presents administrator-specific plugins. The interface consists of:

### Application Layout

1. **Menu Bar**: Access to File, Edit, View/Plugins, Window, and Help menus
2. **Plugin Windows**: Each administrative function runs in its own independent window
3. **Tab Navigation**: Bottom tabs allow quick switching between open plugins
4. **Status Bar**: Displays connection status and current facility

### Window Management

- All windows are dockable/detachable and can be arranged to suit workflow preferences
- Window states are saved between sessions
- Multiple instances of the same plugin can be opened
- Windows can be floated or tabbed together

---

## Plugin Windows

### 1. Allocations

**How to Open**: Go to **View/Plugins** > **Cuecommander** > **Allocations**

The Allocations window provides centralized management of render farm resource allocations, allowing administrators to monitor and control how compute resources are distributed across different departments, shows, or facilities.

![Allocations Interface](/assets/images/cuegui/cuecommander/allocations.png)

#### Purpose

Manages the assignment of compute resources (cores and hosts) to specific allocations, which determine render capacity available to different shows or departments. Allocations are fundamental to OpenCue's resource management, ensuring fair distribution of farm resources.

#### Key Features

**Allocation Table Columns**:
- **Name**: Allocation identifier (e.g., "cloud.general", "local.desktop")
- **Tag**: Allocation tag for categorization
- **Cores**: Total cores assigned to the allocation
- **Idle**: Currently available/unused cores
- **Locked**: Cores locked from use
- **Down**: Cores on hosts marked as down
- **Repair**: Cores on hosts in repair state
- **Hosts**: Total number of hosts in allocation
- **Locked (Hosts)**: Number of locked hosts
- **Down (Hosts)**: Number of down hosts
- **Repair (Hosts)**: Number of hosts in repair

**Interactive Features**:
- Drag-and-drop hosts between allocations
- Real-time resource utilization updates
- Context menu actions for allocation management
- Automatic refresh every 60 seconds

#### Usage Instructions

1. **Monitor Resource Distribution**:
   - Review core counts across allocations
   - Identify underutilized allocations (high idle counts)
   - Check for hosts in problematic states (down/repair)

2. **Reassign Hosts**:
   - Select hosts from one allocation
   - Drag to target allocation
   - Confirm the transfer when prompted

3. **Manage Allocation States**:
   - Right-click for context menu options
   - Lock/unlock allocations as needed
   - Modify allocation properties

#### Common Use Cases

- **Capacity Planning**: Review allocation utilization before launching large jobs
- **Troubleshooting**: Identify allocations with high numbers of down/repair hosts
- **Resource Balancing**: Move idle resources to allocations with high demand
- **Maintenance**: Lock allocations during scheduled maintenance windows

---

### 2. Limits

**How to Open**: Go to **View/Plugins** > **Cuecommander** > **Limits**

The Limits window manages render limits that control concurrent resource usage across the farm, preventing resource exhaustion and ensuring stable operations.

![Limits Interface](/assets/images/cuegui/cuecommander/limites.png)

#### Purpose

Configures and monitors system-wide limits that restrict how many frames can run simultaneously for specific resource types. Limits prevent jobs from overwhelming shared resources like licenses, storage systems, or databases.

#### Key Features

**Limit Configuration Panel**:
- **Limit Name**: Identifier for the limit (e.g., "arnold_licenses")
- **Max Value**: Maximum concurrent usage allowed
- **Current Running**: Active usage count

**Control Actions**:
- **Refresh**: Update current usage statistics
- **Add Limit**: Create new resource limits
- **Edit**: Modify existing limit values
- **Delete**: Remove limits (with confirmation)

#### Usage Instructions

1. **Create a New Limit**:
   - Click "Add Limit" button
   - Enter limit name and maximum value
   - Specify associated resources or services

2. **Monitor Usage**:
   - Watch "Current Running" vs "Max Value"
   - Identify limits approaching capacity
   - Review historical usage patterns

3. **Adjust Limits**:
   - Select limit and click Edit
   - Modify max value based on available resources
   - Apply changes immediately

#### Common Use Cases

- **License Management**: Limit concurrent software license usage
- **I/O Protection**: Prevent storage system overload
- **Database Connections**: Control simultaneous database queries
- **Network Bandwidth**: Manage render output bandwidth usage

---

### 3. Monitor Cue

**How to Open**: Go to **View/Plugins** > **Cuecommander** > **Monitor Cue**

Monitor Cue provides a hierarchical view of the entire render farm structure, displaying shows, groups, and jobs in an expandable tree format with administrative controls.

![Monitor Cue Interface](/assets/images/cuegui/cuecommander/monitor_cue.png)

#### Purpose

Offers comprehensive visibility into the show/group/job hierarchy with administrative actions for managing render jobs at all levels. This is the primary tool for understanding farm-wide job distribution and status.

#### Key Features

**Tree View Components**:
- **Shows Dropdown**: Filter by specific shows
- **Expand/Collapse Controls**: Navigate complex hierarchies
- **Job Status Indicators**: Visual status for each job
- **Resource Metrics**: Cores, memory, and runtime statistics

**Toolbar Actions**:
- **Clear**: Remove completed jobs from view
- **Select Jobs**: Multi-select for batch operations
- **Eat Dead Frames**: Mark failed frames as complete
- **Retry Dead Frames**: Requeue failed frames
- **Kill Jobs**: Terminate selected jobs
- **Pause/Unpause**: Control job execution

**Statistics Columns**:
- **Run**: Currently running frames
- **Cores**: Allocated cores
- **Gpus**: GPU resources in use
- **Wait**: Frames waiting to run
- **Depend**: Frames with unmet dependencies
- **Total**: Total frame count
- **Min/Max/Avg**: Frame runtime statistics
- **Priority**: Job priority values
- **Age**: Time since job submission

#### Usage Instructions

1. **Navigate Hierarchy**:
   - Select show from dropdown
   - Expand groups to see jobs
   - Use toolbar buttons for quick expand/collapse

2. **Manage Jobs**:
   - Select multiple jobs with Ctrl/Cmd+Click
   - Right-click for context menu
   - Use toolbar for common actions

3. **Monitor Performance**:
   - Sort by resource usage columns
   - Identify long-running jobs
   - Check dependency bottlenecks

#### Common Use Cases

- **Farm Overview**: Quick assessment of active shows and job distribution
- **Bulk Operations**: Kill or pause multiple jobs simultaneously
- **Priority Management**: Adjust priorities across job groups
- **Dependency Resolution**: Identify and resolve job dependencies

---

### 4. Monitor Hosts

**How to Open**: Go to **View/Plugins** > **Cuecommander** > **Monitor Hosts**

Monitor Hosts provides detailed information about render nodes, their status, resource utilization, and running processes, essential for farm health monitoring.

![Monitor Hosts Interface](/assets/images/cuegui/cuecommander/monitor_hosts.png)

#### Purpose

Enables real-time monitoring and management of render hosts (nodes), including their hardware specifications, current load, and running processes. Critical for identifying and resolving host-specific issues.

#### Key Features

**Host Table (Top Panel)**:
- **Name**: Host identifier
- **Load %**: Current CPU utilization
- **Swap**: Swap memory usage
- **Physical**: Physical memory state
- **GPU Memory**: GPU memory statistics
- **Idle/Total Memory**: Memory availability
- **Temp Available**: Temporary disk space
- **Cores**: CPU core information
- **Idle GPU/Total GPU**: GPU availability
- **Ping**: Network responsiveness
- **Boot Time**: Last boot timestamp
- **Hardware**: Host hardware configuration
- **Locked**: Lock status
- **Thread Mode**: Threading configuration
- **OS**: Operating system details
- **Auto-refresh**: Toggle automatic updates

**Process Table (Bottom Panel)**:
- **Name**: Running frame/process name
- **Cores**: Allocated cores
- **Memory Reserved/Used**: Memory allocation
- **GPU Used**: GPU memory usage
- **Age**: Process runtime
- **Unbooked**: Unaccounted resources
- **Job**: Parent job name

**Filter Controls**:
- **Clear**: Reset all filters
- **Filter Allocation**: Show hosts in specific allocation
- **Filter HardwareState**: Filter by hardware status
- **Filter LockState**: Show locked/unlocked hosts
- **Filter OS**: Filter by operating system

#### Usage Instructions

1. **Monitor Host Health**:
   - Check load percentages for overutilization
   - Review memory and swap usage
   - Identify hosts with high ping times

2. **Manage Host States**:
   - Right-click hosts for context menu
   - Lock hosts for maintenance
   - Set thread modes for optimization
   - Reboot or repair problematic hosts

3. **Process Investigation**:
   - Select host to see running processes
   - Identify stuck or long-running frames
   - Kill problematic processes

#### Common Use Cases

- **Performance Troubleshooting**: Identify overloaded or underperforming hosts
- **Maintenance Planning**: Lock hosts before updates or repairs
- **Resource Optimization**: Adjust thread modes for better utilization
- **Issue Resolution**: Kill stuck processes or reboot unresponsive hosts

---

### 5. Redirect

**How to Open**: Go to **View/Plugins** > **Cuecommander** > **Redirect**

The Redirect window enables administrators to dynamically reassign running processes from one job to another, useful for priority management and resource optimization.

![Redirect Interface](/assets/images/cuegui/cuecommander/redirect.png)

#### Purpose

Allows real-time redirection of compute resources (procs) from lower-priority jobs to higher-priority ones without killing running frames. This advanced feature helps manage urgent deadlines and optimize resource utilization.

#### Key Features

**Redirect Configuration**:
- **Show Selector**: Choose show context
- **Include Groups**: Option to show job groups
- **Require Services**: Filter by required services

**Resource Filters**:
- **Allocations**: Target specific allocations
- **Minimum Cores**: Set minimum core requirements
- **Max Cores**: Limit maximum cores to redirect
- **Minimum Memory**: Memory threshold
- **Result Limit**: Cap number of redirections
- **Proc Hour Cutoff**: Age limit for processes

**Job Selection**:
- **Source Job**: Job to redirect from
- **Target Job**: Job to redirect to
- **Clear/Redirect Buttons**: Execute or reset operation

**Status Display**:
- Shows redirect operation results
- Lists affected frames and hosts
- Provides success/failure feedback

#### Usage Instructions

1. **Setup Redirect**:
   - Select show and configure filters
   - Choose source job (redirect from)
   - Choose target job (redirect to)
   - Set resource constraints

2. **Execute Redirect**:
   - Review settings
   - Click "Redirect" button
   - Monitor operation status
   - Verify successful transfers

3. **Monitor Results**:
   - Check redirected proc count
   - Verify target job receives resources
   - Ensure source job continues properly

#### Common Use Cases

- **Emergency Priority**: Redirect resources to urgent deadline jobs
- **Resource Balancing**: Move resources from idle to active jobs
- **Service Optimization**: Redirect based on service requirements
- **Scheduled Redirects**: Time-based resource reallocation

---

### 6. Services

**How to Open**: Go to **View/Plugins** > **Cuecommander** > **Facility Service Defaults**

The Services window manages service configurations that define software and hardware requirements for render jobs across the facility.

![Services Interface](/assets/images/cuegui/cuecommander/services.png)

#### Purpose

Configures facility-wide service definitions that specify resource requirements for different render engines, software packages, and job types. Services ensure jobs run on appropriate hardware with necessary resources.

#### Key Features

**Service List Panel** (Left):
- Lists all configured services
- Shows service names alphabetically
- Allows selection for editing

**Service Configuration Panel** (Right):
- **Name**: Service identifier
- **Threadable**: Whether service supports threading
- **Min Threads**: Minimum thread count (100 = 1 thread)
- **Max Threads**: Maximum thread count
- **Min Memory MB**: Minimum RAM requirement
- **Min Gpu Memory MB**: Minimum GPU memory
- **Timeout**: Frame timeout in minutes
- **Timeout LLU**: Timeout for last log update
- **Out-Of-Memory (OOM) Increase MB**: Memory increase on out-of-memory

**Tags Section**:
- Service tags for categorization
- Checkbox selection for multiple tags
- Categories: general, desktop, util, splathw, massive

**Control Buttons**:
- **New**: Create new service
- **Del**: Delete selected service
- **Save**: Apply configuration changes
- **Custom Tags**: Add custom service tags

#### Usage Instructions

1. **Create Service**:
   - Click "New" button
   - Enter service name and requirements
   - Set memory and thread limits
   - Select appropriate tags
   - Save configuration

2. **Modify Service**:
   - Select service from list
   - Adjust parameters
   - Update tag selections
   - Click Save to apply

3. **Delete Service**:
   - Select service
   - Click Del button
   - Confirm deletion

#### Common Use Cases

- **Software Configuration**: Define requirements for render engines
- **Resource Templates**: Create standard service profiles
- **Memory Management**: Set appropriate Out-Of-Memory (OOM) thresholds
- **Performance Tuning**: Optimize thread counts for efficiency

---

### 7. Shows

**How to Open**: Go to **View/Plugins** > **Cuecommander** > **Shows**

The Shows window provides administrative control over show configurations, allowing creation, modification, and management of show-level settings.

![Shows Interface](/assets/images/cuegui/cuecommander/shows.png)

#### Purpose

Manages show definitions within OpenCue, including creation of new shows, configuration of show-specific settings, and monitoring of show-level statistics and resources.

#### Key Features

**Shows Table**:
- **Show Name**: Show identifier
- **Cores Run**: Currently running cores
- **Frames Run**: Active frame count
- **Frames Pending**: Waiting frames
- **Jobs**: Total job count

**Control Elements**:
- **Create Show Button**: Launch show creation dialog
- **Context Menu**: Right-click actions
- **Auto-refresh**: Periodic updates

#### Usage Instructions

1. **Create New Show**:
   - Click "Create Show" button
   - Enter show details in dialog
   - Configure allocations and limits
   - Submit creation request

2. **Manage Existing Shows**:
   - Right-click for context menu
   - Modify show properties
   - View show statistics
   - Archive completed shows

3. **Monitor Show Activity**:
   - Review resource usage
   - Check pending frame counts
   - Track job distribution

#### Common Use Cases

- **Show Setup**: Initialize new productions
- **Resource Allocation**: Assign capacity to shows
- **Show Archival**: Clean up completed productions
- **Capacity Planning**: Review show resource requirements

---

### 8. Stuck Frame

**How to Open**: Go to **View/Plugins** > **Cuecommander** > **Stuck Frame**

The Stuck Frame window helps identify and resolve frames that appear to be stuck or running abnormally long, preventing job completion.

![Stuck Frame Interface](/assets/images/cuegui/cuecommander/stuck_frame.png)

#### Purpose

Provides specialized tools for detecting frames that are stuck, hung, or running far longer than expected. Enables targeted intervention to resolve problematic frames without affecting entire jobs.

#### Key Features

**Search Filters Section**:
- **Layer Service**: Filter by service type
- **Exclude Keywords**: Skip frames matching patterns
- **% of Run Since LLU**: Percentage of runtime since last log
- **Min LLU**: Minimum time since last log update
- **% of Average Completion Time**: Compare to average runtime
- **Total Runtime**: Minimum total runtime threshold
- **Enable**: Activate specific filter

**Results Table**:
- **Name**: Frame identifier
- **Comment**: Frame comments/notes
- **Frame Host**: Host running the frame
- **LLU**: Last log update time
- **Runtime %Stuc**: Stuck percentage indicator
- **Average Last Line**: Last log output

**Control Actions**:
- **Search**: Execute filter search
- **Refresh**: Update results
- **Clear**: Reset search criteria
- **Auto-refresh**: Toggle automatic updates
- **Notification**: Enable alerts for stuck frames

#### Usage Instructions

1. **Configure Filters**:
   - Set service-specific thresholds
   - Add exclude patterns for known long-runners
   - Adjust LLU and runtime percentages
   - Enable desired filter combinations

2. **Search for Stuck Frames**:
   - Click Search to apply filters
   - Review results table
   - Sort by stuck percentage
   - Examine last log lines

3. **Resolve Stuck Frames**:
   - Select problematic frames
   - Right-click for context menu
   - Kill, retry, or eat frames
   - Add comments for tracking

#### Common Use Cases

- **Daily Monitoring**: Regular checks for stuck frames
- **Troubleshooting**: Identify patterns in stuck frames
- **Preventive Maintenance**: Catch problems before job failure
- **Performance Analysis**: Review frames exceeding expected runtime

---

### 9. Subscription Graphs

**How to Open**: Go to **View/Plugins** > **Cuecommander** > **Subscription Graphs**

Subscription Graphs provides visual representation of resource allocation and consumption across shows and allocations.

![Subscription Graphs Interface](/assets/images/cuegui/cuecommander/subscription_graphs.png)

#### Purpose

Visualizes subscription relationships between shows and allocations, displaying real-time resource utilization through interactive graphs. Essential for understanding resource distribution patterns.

#### Key Features

**Graph Display**:
- **Shows Dropdown**: Select show to visualize
- **Allocation Bars**: Horizontal bars showing allocation usage
- **Color Coding**: Visual distinction between allocations
- **Real-time Updates**: Live resource consumption display

**Visualization Elements**:
- Resource usage percentages
- Allocation capacity indicators
- Show subscription levels
- Burst capacity visualization

#### Usage Instructions

1. **Select Show**:
   - Choose from shows dropdown
   - Graph updates automatically
   - View all subscribed allocations

2. **Analyze Usage**:
   - Review bar lengths for consumption
   - Identify underutilized allocations
   - Check burst usage patterns

3. **Compare Allocations**:
   - Visual comparison of allocation sizes
   - Relative usage across subscriptions
   - Capacity planning insights

#### Common Use Cases

- **Capacity Review**: Visual assessment of resource distribution
- **Subscription Planning**: Identify needed subscription adjustments
- **Usage Patterns**: Understand show resource consumption
- **Optimization**: Find underutilized subscriptions

---

### 10. Subscriptions

**How to Open**: Go to **View/Plugins** > **Cuecommander** > **Subscriptions**

The Subscriptions window manages the relationships between shows and allocations, controlling how resources are assigned and prioritized.

![Subscriptions Interface](/assets/images/cuegui/cuecommander/subscriptions.png)

#### Purpose

Configures and manages subscriptions that link shows to allocations, determining resource access and priority. Critical for controlling how render capacity is distributed across productions.

#### Key Features

**Subscription Management**:
- Show selection interface
- Allocation assignment controls
- Priority configuration
- Burst capacity settings

**Subscription Properties**:
- Size: Guaranteed resource allocation
- Burst: Additional capacity when available
- Priority: Subscription priority level
- Active: Enable/disable subscriptions

#### Usage Instructions

1. **Create Subscription**:
   - Select show and allocation
   - Set size and burst values
   - Configure priority
   - Activate subscription

2. **Modify Subscriptions**:
   - Adjust size allocations
   - Change burst allowances
   - Update priorities
   - Enable/disable as needed

3. **Monitor Usage**:
   - Review active subscriptions
   - Check utilization levels
   - Identify unused subscriptions

#### Common Use Cases

- **Production Setup**: Configure new show subscriptions
- **Resource Reallocation**: Adjust subscriptions for changing needs
- **Priority Management**: Set subscription priorities for deadlines
- **Capacity Optimization**: Balance subscriptions across shows

---

## Tips & Best Practices

### Performance Optimization

1. **Window Management**:
   - Close unused plugin windows to reduce memory usage
   - Use tab grouping for related windows
   - Set appropriate refresh intervals

2. **Filter Usage**:
   - Apply filters to reduce data volume
   - Save filter presets for common queries
   - Use regex patterns efficiently

3. **Batch Operations**:
   - Group similar actions together
   - Use multi-select for bulk changes
   - Schedule maintenance during low-activity periods

### Workflow Combinations

1. **Troubleshooting Workflow**:
   - Start with Monitor Cue for job overview
   - Check Stuck Frame for problematic frames
   - Use Monitor Hosts to identify host issues
   - Apply Redirect to rebalance resources

2. **Capacity Management**:
   - Review Allocations for resource distribution
   - Check Subscription Graphs for visual analysis
   - Adjust Subscriptions based on usage
   - Monitor with Shows window

3. **Maintenance Workflow**:
   - Lock hosts in Monitor Hosts
   - Set allocations to maintenance mode
   - Configure service limits appropriately
   - Monitor progress in Monitor Cue

### Critical Warnings

⚠️ **High-Impact Operations**:
- Killing jobs removes all running frames immediately
- Allocation changes affect all shows using them
- Service modifications impact all jobs using that service
- Host locks prevent any job execution on those nodes

⚠️ **Resource Management**:
- Avoid oversubscribing allocations beyond capacity
- Monitor memory limits to prevent Out-Of-Memory (OOM) kills
- Set appropriate timeouts to catch stuck frames
- Balance subscriptions to prevent starvation

⚠️ **System Stability**:
- Test service changes on non-production jobs first
- Coordinate host maintenance with production schedules
- Document all configuration changes
- Maintain backup of service and limit configurations

---

## Troubleshooting

### Common Issues and Solutions

**Issue: Jobs not picking up after allocation change**
- Solution: Check subscription is active and has sufficient size
- Verify hosts are in correct allocation
- Ensure no limits are blocking execution

**Issue: Frames continuously failing**
- Solution: Check service memory requirements
- Review frame logs for specific errors
- Verify software licenses are available
- Check host compatibility

**Issue: Uneven resource distribution**
- Solution: Review subscription priorities
- Check for allocation locks
- Verify burst settings are appropriate
- Balance subscription sizes

**Issue: Plugin windows not updating**
- Solution: Check network connectivity
- Verify Cuebot connection
- Restart plugin or application
- Check refresh settings

**Issue: Cannot modify allocations/services**
- Solution: Verify administrator permissions
- Check for database locks
- Ensure Cuebot is responding
- Review system logs for errors

### Diagnostic Steps

1. **Check System Status**:
   - Verify Cuebot connectivity
   - Review system resource availability
   - Check database responsiveness

2. **Review Logs**:
   - Examine Cuebot logs for errors
   - Check RQD logs on problematic hosts
   - Review job/frame logs for patterns

3. **Test Incrementally**:
   - Make small configuration changes
   - Test on single jobs/hosts first
   - Monitor impact before scaling

---

## References

### Related Documentation

- [CueGUI: Cuetopia Monitoring Guide](/docs/user-guides/cuetopia-monitoring-guide)

### Command-Line Equivalents

Many CueCommander operations have CLI equivalents using `cueadmin`:

```bash
# Allocation management
cueadmin -la                    # List allocations
cueadmin -lh -alloc <name>     # List hosts in allocation

# Host management  
cueadmin -lh                    # List all hosts
cueadmin -lock <host>          # Lock host
cueadmin -unlock <host>        # Unlock host

# Service management
cueadmin -lv                    # List default services
cueadmin -lv <show>            # List show-specific service overrides

# Show management
cueadmin -ls                    # List shows
cueadmin -create-show <name>   # Create show

# Subscription management
cueadmin -lb <show>            # List show subscriptions
cueadmin -lba <alloc>          # List all subscriptions to an allocation
```

### Python API Reference

CueCommander operations can be automated using the OpenCue Python API:

```python
import opencue

# Allocation operations
allocations = opencue.api.getAllocations()
alloc = opencue.api.findAllocation("local.general")
alloc.reparentHosts(["host1", "host2"])

# Host operations
hosts = opencue.api.getHosts()
host = opencue.api.findHost("rendernode01")
host.lock()

# Service operations (Note: Service management is done via API, not CLI)
services = opencue.api.getDefaultServices()
service = opencue.api.createService("custom_service")  # No CLI equivalent

# Show operations
shows = opencue.api.getShows()
show = opencue.api.findShow("production")
```
