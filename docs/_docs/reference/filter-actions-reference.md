---
title: "Filter Actions Reference"
nav_order: 65
parent: Reference
layout: default
date: 2025-10-15
description: >
  Complete reference guide for OpenCue filter actions that automate job management and resource configuration
---

# Filter Actions Reference

## Overview

Filter actions are automated operations that execute when jobs match specific filter criteria in OpenCue. They enable automatic job management, resource allocation, and workflow optimization based on job properties like name, show, user, or service.

Filters are configured in CueGUI through **Views/Plugins** > **Cuecommander** > **Filters** plugin, where you can create matchers (conditions) and actions (operations) that apply to incoming jobs.

## How Filters Work

When a job is submitted to OpenCue:

1. **Matchers** evaluate job properties (name, show, user, etc.)
2. If matchers match, associated **Actions** execute automatically
3. Actions modify job properties or layer configurations
4. Filters run in priority order (configurable)

## Filter Action Types

OpenCue supports the following action types for automating job management:

### Job Management Actions

#### MOVE_JOB_TO_GROUP

Automatically moves jobs to a specific group based on filter criteria.

**What are Groups?**

Groups in OpenCue are organizational folders for tracking and managing jobs. Groups allow you to:
- Organize jobs by department (lighting, FX, compositing, etc.)
- Separate jobs by priority (hero shots, regular work, tests)
- Track resource usage per department or project phase
- Apply group-level resource policies

**How to Create Groups:**

1. Open CueGUI
2. Go to **Window** > **Open Windows: CueCommander**
3. Select **Views/Plugins** > **OpenCuecommander** > **Monitor Cue**
4. In the Show/Root Group tree, right-click on a show name or existing group
5. Select **"Create Group..."** from the context menu
6. Enter the group name (e.g., "lighting-group", "fx-group", "priority-group")
7. Click **OK**

**Use Cases:**
- Organize jobs by department (lighting, compositing, etc.)
- Separate test jobs from production jobs
- Group jobs by priority or resource requirements
- Track resource utilization by team

**Value Type:** `GROUP_TYPE` - Target group name (group must exist before filter runs)

**Example:**
```
Matcher: Job name contains "lighting"
Action: MOVE_JOB_TO_GROUP → "lighting-group"
Result: All lighting jobs automatically move to the lighting-group folder

Note: Ensure "lighting-group" exists before enabling this filter.
      Create groups in CueCommander > Monitor Cue > Right-click show > Create Group.
```

---

#### PAUSE_JOB

Automatically pauses jobs when they match filter criteria.

**Use Cases:**
- Hold jobs pending approval
- Pause test jobs during production hours
- Queue jobs for later execution

**Value Type:** `BOOLEAN_TYPE` - True to pause

**Example:**
```
Matcher: Job name starts with "test_"
Action: PAUSE_JOB → true
Result: All test jobs start in paused state
```

---

#### STOP_PROCESSING

Stops the filter processing chain for the matched job. Useful when you want to prevent subsequent filters from executing.

**Use Cases:**
- Short-circuit filter evaluation for specific jobs
- Prevent conflicting actions from other filters
- Optimize filter performance by stopping early

**Value Type:** `NONE_TYPE` - No value required

**Example:**
```
Matcher: Job name is "critical-hero-shot"
Action: STOP_PROCESSING
Result: Job matches but no further filters evaluate
```

---

### Job Resource Actions

#### SET_JOB_MIN_CORES

Sets the minimum number of CPU cores required for the job.

**Use Cases:**
- Ensure lightweight jobs don't reserve excessive resources
- Set baseline core requirements per show or user
- Optimize farm utilization

**Value Type:** `FLOAT_TYPE` - Minimum cores (e.g., 1.0, 2.0, 4.0)

**Example:**
```
Matcher: Show is "demo-project"
Action: SET_JOB_MIN_CORES → 2.0
Result: All demo-project jobs require minimum 2 cores
```

---

#### SET_JOB_MAX_CORES

Sets the maximum number of CPU cores the job can use.

**Use Cases:**
- Limit resource usage for background jobs
- Prevent single jobs from monopolizing the farm
- Enforce resource policies per department

**Value Type:** `FLOAT_TYPE` - Maximum cores (e.g., 10.0, 50.0, 100.0)

**Example:**
```
Matcher: User is "intern_user"
Action: SET_JOB_MAX_CORES → 10.0
Result: Intern users limited to 10 cores maximum
```

---

#### SET_JOB_PRIORITY

Sets the job priority value (higher values = higher priority).

**Use Cases:**
- Automatically prioritize hero shots
- Lower priority for test renders
- Set department-specific priorities

**Value Type:** `INTEGER_TYPE` - Priority value (typical range: 0-1000)

**Example:**
```
Matcher: Job name contains "hero"
Action: SET_JOB_PRIORITY → 900
Result: Hero shots get high priority (900)
```

---

### Render Layer Actions

These actions apply settings to all layers with the type "Render" within a job.

#### SET_ALL_RENDER_LAYER_TAGS

Sets tags for all render layers in the job.

**Use Cases:**
- Require specific hardware (GPU, high-memory hosts)
- Route renders to specific allocations
- Target hosts with special software

**Value Type:** `STRING_TYPE` - Comma-separated tags (e.g., "gpu,highprio")

**Example:**
```
Matcher: Service is "arnold"
Action: SET_ALL_RENDER_LAYER_TAGS → "gpu,arnold_license"
Result: Arnold render layers tagged for GPU hosts with licenses
```

---

#### SET_ALL_RENDER_LAYER_MEMORY

Sets minimum memory requirement for all render layers.

**Use Cases:**
- Allocate more memory for complex scenes
- Prevent out-of-memory failures
- Set memory requirements per show

**Value Type:** `INTEGER_TYPE` - Memory in KB (e.g., 4194304 = 4GB)

**Example:**
```
Matcher: Show is "high-res-project"
Action: SET_ALL_RENDER_LAYER_MEMORY → 16777216
Result: All render layers require 16GB memory minimum
```

**Note:** Memory is specified in kilobytes:
- 1 GB = 1048576 KB
- 2 GB = 2097152 KB
- 4 GB = 4194304 KB
- 8 GB = 8388608 KB
- 16 GB = 16777216 KB

---

#### SET_ALL_RENDER_LAYER_MIN_CORES

Sets minimum CPU cores for all render layers.

**Use Cases:**
- Ensure renders have sufficient processing power
- Set core requirements based on renderer type
- Optimize render performance

**Value Type:** `FLOAT_TYPE` - Minimum cores (e.g., 4.0, 8.0)

**Example:**
```
Matcher: Service is "maya"
Action: SET_ALL_RENDER_LAYER_MIN_CORES → 4.0
Result: Maya render layers require minimum 4 cores
```

---

#### SET_ALL_RENDER_LAYER_MAX_CORES

Sets maximum CPU cores for all render layers.

**Use Cases:**
- Prevent renders from using too many resources
- Ensure even distribution across the farm
- Limit resource usage for lower-priority shows

**Value Type:** `FLOAT_TYPE` - Maximum cores (e.g., 16.0, 32.0)

**Example:**
```
Matcher: Show is "background-show"
Action: SET_ALL_RENDER_LAYER_MAX_CORES → 8.0
Result: Background show renders limited to 8 cores
```

---

#### SET_ALL_RENDER_LAYER_CORES (Deprecated)

**Status:** Deprecated - Use `SET_ALL_RENDER_LAYER_MIN_CORES` and `SET_ALL_RENDER_LAYER_MAX_CORES` instead.

This action previously set both minimum and maximum cores simultaneously. It has been replaced by separate min/max actions for better control.

---

### Utility Layer Actions

These actions apply settings to all layers with the type "Util" within a job. Utility layers typically handle pre/post-processing tasks like scene preparation, cache generation, or cleanup operations.

#### SET_ALL_UTIL_LAYER_TAGS

Sets tags for all utility layers in the job.

**Use Cases:**
- Route utility tasks to specific hosts
- Require fast local storage for cache operations
- Target hosts with specific software versions

**Value Type:** `STRING_TYPE` - Comma-separated tags (e.g., "fast_storage,python3")

**Example:**
```
Matcher: Job name contains "cache_generation"
Action: SET_ALL_UTIL_LAYER_TAGS → "fast_storage,high_io"
Result: Cache utility layers run on hosts with fast storage
```

---

#### SET_ALL_UTIL_LAYER_MEMORY

Sets minimum memory requirement for all utility layers.

**Use Cases:**
- Allocate memory for scene processing
- Prevent failures during cache generation
- Support memory-intensive utility scripts

**Value Type:** `INTEGER_TYPE` - Memory in KB (e.g., 8388608 = 8GB)

**Example:**
```
Matcher: Job name contains "scene_prep"
Action: SET_ALL_UTIL_LAYER_MEMORY → 8388608
Result: Scene prep utility layers get 8GB memory
```

---

#### SET_ALL_UTIL_LAYER_MIN_CORES

Sets minimum CPU cores for all utility layers.

**Use Cases:**
- Ensure utility tasks have adequate processing power
- Speed up pre-processing operations
- Set baseline performance requirements

**Value Type:** `FLOAT_TYPE` - Minimum cores (e.g., 2.0, 4.0)

**Example:**
```
Matcher: Show is "vfx-show"
Action: SET_ALL_UTIL_LAYER_MIN_CORES → 2.0
Result: VFX utility layers require minimum 2 cores
```

---

#### SET_ALL_UTIL_LAYER_MAX_CORES

Sets maximum CPU cores for all utility layers.

**Use Cases:**
- Prevent utility tasks from using excessive resources
- Reserve cores for render layers
- Balance farm resource allocation

**Value Type:** `FLOAT_TYPE` - Maximum cores (e.g., 4.0, 8.0)

**Example:**
```
Matcher: Job name starts with "util_"
Action: SET_ALL_UTIL_LAYER_MAX_CORES → 4.0
Result: Utility tasks limited to 4 cores maximum
```

---

### Pre-Processing Layer Actions

These actions apply settings to all layers with the type "Pre" within a job. Pre-processing layers handle initial setup tasks like asset validation, dependency checking, or environment preparation before main processing begins.

#### SET_ALL_PRE_LAYER_TAGS

Sets tags for all pre-processing layers in the job.

**Use Cases:**
- Route pre-processing to coordinator hosts
- Require specific environment configurations
- Target hosts with validation tools

**Value Type:** `STRING_TYPE` - Comma-separated tags (e.g., "coordinator,validator")

**Example:**
```
Matcher: Show is "production-show"
Action: SET_ALL_PRE_LAYER_TAGS → "coordinator,fast_cpu"
Result: Pre-processing layers run on coordinator hosts
```

---

#### SET_ALL_PRE_LAYER_MEMORY

Sets minimum memory requirement for all pre-processing layers.

**Use Cases:**
- Allocate memory for asset validation
- Support dependency checking operations
- Prevent failures during setup

**Value Type:** `INTEGER_TYPE` - Memory in KB (e.g., 4194304 = 4GB)

**Example:**
```
Matcher: Job name contains "validate"
Action: SET_ALL_PRE_LAYER_MEMORY → 4194304
Result: Validation pre-layers get 4GB memory minimum
```

---

#### SET_ALL_PRE_LAYER_MIN_CORES

Sets minimum CPU cores for all pre-processing layers.

**Use Cases:**
- Ensure pre-processing completes quickly
- Allocate sufficient resources for validation
- Set baseline requirements for setup tasks

**Value Type:** `FLOAT_TYPE` - Minimum cores (e.g., 1.0, 2.0)

**Example:**
```
Matcher: User is "pipeline_user"
Action: SET_ALL_PRE_LAYER_MIN_CORES → 1.0
Result: Pipeline pre-processing layers get minimum 1 core
```

---

#### SET_ALL_PRE_LAYER_MAX_CORES

Sets maximum CPU cores for all pre-processing layers.

**Use Cases:**
- Prevent pre-processing from blocking renders
- Limit resource usage for setup tasks
- Balance farm resources efficiently

**Value Type:** `FLOAT_TYPE` - Maximum cores (e.g., 2.0, 4.0)

**Example:**
```
Matcher: Show is "small-project"
Action: SET_ALL_PRE_LAYER_MAX_CORES → 2.0
Result: Small project pre-layers limited to 2 cores
```

---

### Memory Optimizer Action

#### SET_MEMORY_OPTIMIZER

Enables or disables the memory optimizer for the job. The memory optimizer dynamically adjusts memory requirements based on actual usage patterns.

**Use Cases:**
- Enable smart memory management for unpredictable jobs
- Optimize resource utilization
- Reduce memory waste on the farm

**Value Type:** `BOOLEAN_TYPE` - True to enable optimizer

**Example:**
```
Matcher: Service is "blender"
Action: SET_MEMORY_OPTIMIZER → true
Result: Blender jobs use dynamic memory optimization
```

---

## Creating Filters in CueGUI

### Step 1: Open the Filters Plugin

1. Launch CueGUI
2. Go to **Views/Plugins** > **Cuecommander**
3. Select the **Filters** plugin

### Step 2: Create a Filter

1. Click **Create Filter**
2. Set filter name (e.g., "High-Priority Hero Shots")
3. Set filter type:
   - **MATCH_ALL**: All matchers must match (AND logic)
   - **MATCH_ANY**: Any matcher can match (OR logic)
4. Set filter order (lower numbers run first)
5. Enable/disable the filter

### Step 3: Add Matchers

Matchers define conditions for when the filter applies:

**Available Match Subjects:**
- `JOB_NAME`: Match against job name
- `SHOW`: Match against show name
- `SHOT`: Match against shot name
- `USER`: Match against submitting user
- `SERVICE_NAME`: Match against service (renderer)
- `PRIORITY`: Match against job priority
- `FACILITY`: Match against facility code
- `LAYER_NAME`: Match against layer names

**Match Types:**
- `CONTAINS`: Subject contains the text
- `DOES_NOT_CONTAIN`: Subject doesn't contain the text
- `IS`: Subject exactly matches
- `IS_NOT`: Subject doesn't match
- `REGEX`: Subject matches regular expression
- `BEGINS_WITH`: Subject starts with text
- `ENDS_WITH`: Subject ends with text

### Step 4: Add Actions

1. Click **Add Action**
2. Select action type from the dropdown
3. Configure action value based on type:
   - **Group actions**: Select target group
   - **String actions**: Enter tag names
   - **Integer actions**: Enter numeric values
   - **Float actions**: Enter decimal values
   - **Boolean actions**: Check/uncheck box

### Step 5: Test and Enable

1. Use **Test Filter** to verify behavior
2. Enable the filter for production use
3. Monitor filter execution in logs

---

## Best Practices

### Filter Organization

1. **Use Clear Names**: Name filters descriptively (e.g., "Arnold Jobs - GPU Tags")
2. **Order Matters**: Place most specific filters first, general filters last
3. **Group Related Filters**: Keep similar filters together in the order list

### Performance Considerations

1. **Use STOP_PROCESSING**: Prevent unnecessary filter evaluations
2. **Optimize Regex**: Simple matchers are faster than complex regex
3. **Limit Active Filters**: Disable unused filters

### Resource Management

1. **Set Realistic Limits**: Don't over-allocate resources
2. **Use Layer-Specific Actions**: Target specific layer types
3. **Balance Min/Max Values**: Ensure max >= min for core/memory settings

### Testing

1. **Test on Dev Jobs**: Verify filters work before production use
2. **Monitor First Runs**: Watch filter execution logs
3. **Iterate**: Adjust matchers and actions based on results

---

## Common Filter Patterns

### Pattern 1: Priority-Based Resource Allocation

```
Filter: "Hero Shots - High Priority"
├── Matcher: Job name contains "hero"
├── Action: SET_JOB_PRIORITY → 900
├── Action: SET_JOB_MIN_CORES → 10.0
└── Action: SET_ALL_RENDER_LAYER_MEMORY → 16777216 (16GB)
```

### Pattern 2: Department-Based Grouping

```
Filter: "Lighting Department Jobs"
├── Matcher: Job name begins with "light_"
├── Action: MOVE_JOB_TO_GROUP → "lighting-group"
└── Action: SET_ALL_RENDER_LAYER_TAGS → "gpu,high_memory"
```

### Pattern 3: Test Job Management

```
Filter: "Test Jobs - Limited Resources"
├── Matcher: Job name starts with "test_"
├── Action: PAUSE_JOB → true
├── Action: SET_JOB_PRIORITY → 100
└── Action: SET_JOB_MAX_CORES → 5.0
```

### Pattern 4: Renderer-Specific Configuration

```
Filter: "Arnold Renders - GPU Required"
├── Matcher: Service is "arnold"
├── Action: SET_ALL_RENDER_LAYER_TAGS → "gpu,arnold_license"
├── Action: SET_ALL_RENDER_LAYER_MEMORY → 12582912 (12GB)
└── Action: SET_MEMORY_OPTIMIZER → true
```

### Pattern 5: Multi-Layer Job Optimization

```
Filter: "Complex Pipeline Job Setup"
├── Matcher: Job name contains "pipeline"
├── Action: SET_ALL_PRE_LAYER_MIN_CORES → 2.0
├── Action: SET_ALL_PRE_LAYER_MAX_CORES → 4.0
├── Action: SET_ALL_UTIL_LAYER_MEMORY → 8388608 (8GB)
├── Action: SET_ALL_RENDER_LAYER_MIN_CORES → 8.0
└── Action: SET_ALL_RENDER_LAYER_TAGS → "gpu,fast_storage"
```

### Pattern 6: User-Based Resource Limits

```
Filter: "Junior Artist Limits"
├── Matcher: User is "junior_artist_*" (regex)
├── Action: SET_JOB_MAX_CORES → 10.0
├── Action: SET_JOB_PRIORITY → 200
└── Action: SET_ALL_RENDER_LAYER_MEMORY → 4194304 (4GB)
```

---

## Troubleshooting Filters

### Filter Not Triggering

**Check:**
1. Filter is enabled
2. Matchers are correctly configured
3. Filter order allows it to execute
4. Previous filter didn't use STOP_PROCESSING

### Actions Not Applied

**Check:**
1. Action values are within valid ranges
2. Value types match action requirements
3. Groups exist for MOVE_JOB_TO_GROUP actions
4. Check Cuebot logs for error messages

### Conflicting Filters

**Issue:** Multiple filters modify the same property
**Solution:**
1. Review filter order
2. Use STOP_PROCESSING in earlier filters
3. Consolidate related filters
4. Make matchers more specific

---

## All Filter Actions

### Core Actions

- `MOVE_JOB_TO_GROUP` - Job group management
- `PAUSE_JOB` - Job pause control
- `SET_JOB_MIN_CORES` - Job minimum cores
- `SET_JOB_MAX_CORES` - Job maximum cores
- `STOP_PROCESSING` - Filter chain control
- `SET_JOB_PRIORITY` - Job priority management
- `SET_MEMORY_OPTIMIZER` - Memory optimization

### Render Layer Actions

- `SET_ALL_RENDER_LAYER_TAGS` - Render layer tags
- `SET_ALL_RENDER_LAYER_MEMORY` - Render layer memory
- `SET_ALL_RENDER_LAYER_MIN_CORES` - Render layer minimum cores
- `SET_ALL_RENDER_LAYER_MAX_CORES` - Render layer maximum cores

### Pre-Processing Layer Actions

- `SET_ALL_PRE_LAYER_TAGS` - Pre-processing layer tag configuration
- `SET_ALL_PRE_LAYER_MEMORY` - Pre-processing layer memory settings
- `SET_ALL_PRE_LAYER_MIN_CORES` - Pre-processing layer minimum cores
- `SET_ALL_PRE_LAYER_MAX_CORES` - Pre-processing layer maximum cores

### Utility Layer Actions

- `SET_ALL_UTIL_LAYER_TAGS` - Utility layer tag configuration
- `SET_ALL_UTIL_LAYER_MEMORY` - Utility layer memory settings
- `SET_ALL_UTIL_LAYER_MIN_CORES` - Utility layer minimum cores
- `SET_ALL_UTIL_LAYER_MAX_CORES` - Utility layer maximum cores

### Deprecated

- `SET_ALL_RENDER_LAYER_CORES` - Replaced by separate min/max actions

## What's Next?

To learn more about filters:

- **[Filters and Actions](/docs/concepts/filters-and-actions/)** - Concepts: Filters and Actions
- **[Using Filters User Guide](/docs/user-guides/using-filters/)** - User Guides: Practical filter usage
- **[Filter Tutorial](/docs/tutorials/filter-tutorial/)** - Tutorials: Step-by-step filter examples
- **[Filter Development](/docs/developer-guide/filter-development/)** - Developer Guide: Filter Development
