---
title: "Filters and Actions"
nav_order: 14
parent: Concepts
layout: default
date: 2025-10-15
description: >
  Understanding OpenCue filters and actions for automated job management and resource allocation
---

# Filters and Actions

## Overview

Filters and actions are OpenCue's automation system for managing jobs, allocating resources, and enforcing pipeline policies. When jobs are submitted to OpenCue, filters evaluate job properties and automatically apply configured actions, enabling hands-free job management at scale.

## What Are Filters?

A **filter** is a rule-based system that:
1. **Evaluates** incoming jobs against specified criteria (matchers)
2. **Executes** configured actions when criteria match
3. **Runs** in a defined order to apply policies consistently

Filters enable pipeline engineers and administrators to:
- Automatically organize jobs into groups
- Enforce resource allocation policies
- Set priorities based on job characteristics
- Configure layer-specific requirements
- Implement show-specific workflows

### Filter Components

Every filter consists of three main components:

#### 1. Filter Properties

- **Name**: Descriptive identifier (e.g., "Arnold GPU Jobs")
- **Type**: Match logic (MATCH_ALL or MATCH_ANY)
- **Order**: Execution priority (lower numbers run first)
- **Enabled**: Active/inactive status

#### 2. Matchers

Matchers define the conditions under which a filter applies. They evaluate job properties such as:

- **Job Name**: Pattern matching against job identifier
- **Show**: Which production/project the job belongs to
- **User**: Who submitted the job
- **Service**: Rendering application (Arnold, Blender, Maya, etc.)
- **Shot**: Specific shot identifier
- **Layer Name**: Layer naming patterns
- **Priority**: Job priority level
- **Facility**: Data center or location

**Match Types:**
- `CONTAINS` - Text is found within the property
- `DOES_NOT_CONTAIN` - Text is not found
- `IS` - Exact match
- `IS_NOT` - Does not exactly match
- `REGEX` - Regular expression pattern match
- `BEGINS_WITH` - Starts with specified text
- `ENDS_WITH` - Ends with specified text

**Match Logic:**
- **MATCH_ALL** (AND): Every matcher must match for the filter to trigger
- **MATCH_ANY** (OR): Any single matcher can trigger the filter

#### 3. Actions

Actions are operations executed when matchers succeed. They modify job properties, layer configurations, or workflow behavior.

### Filter Interface

Filters are managed through the **CueCommander > Monitor Cue** window in CueGUI:

![CueCommander Filters Window](/assets/images/cuegui/cuecommander/cuecommander_filters_window.png)

**Figure:** The Filters management interface in CueCommander. The left panel shows the list of configured filters with their enabled status, names, and match types. The right side displays the matchers (top right) and actions (bottom right) for the selected filter. This interface allows you to create, edit, and organize all filters for a show.

## What Are Actions?

An **action** is an automated operation that modifies a job or its layers. Actions fall into several categories:

### Job-Level Actions

Modify properties of the entire job:

- **MOVE_JOB_TO_GROUP**: Organize jobs into management groups
- **PAUSE_JOB**: Hold jobs from execution
- **SET_JOB_PRIORITY**: Control scheduling priority
- **SET_JOB_MIN_CORES**: Minimum core allocation
- **SET_JOB_MAX_CORES**: Maximum core allocation
- **STOP_PROCESSING**: Halt filter chain evaluation

### Layer-Level Actions

Configure specific layer types within jobs. OpenCue supports three layer types:

#### Render Layers

Primary rendering operations (frames, images, sequences):

- **SET_ALL_RENDER_LAYER_TAGS**: Host targeting tags
- **SET_ALL_RENDER_LAYER_MEMORY**: Memory requirements
- **SET_ALL_RENDER_LAYER_MIN_CORES**: Minimum cores per frame
- **SET_ALL_RENDER_LAYER_MAX_CORES**: Maximum cores per frame

#### Utility Layers

Supporting operations (cache generation, scene prep, post-processing):

- **SET_ALL_UTIL_LAYER_TAGS**: Host requirements for utilities
- **SET_ALL_UTIL_LAYER_MEMORY**: Utility memory allocation
- **SET_ALL_UTIL_LAYER_MIN_CORES**: Minimum utility cores
- **SET_ALL_UTIL_LAYER_MAX_CORES**: Maximum utility cores

#### Pre-Processing Layers

Initial setup tasks (validation, dependency checks, environment prep):

- **SET_ALL_PRE_LAYER_TAGS**: Pre-processing host tags
- **SET_ALL_PRE_LAYER_MEMORY**: Pre-processing memory
- **SET_ALL_PRE_LAYER_MIN_CORES**: Minimum pre-processing cores
- **SET_ALL_PRE_LAYER_MAX_CORES**: Maximum pre-processing cores

### Optimization Actions

- **SET_MEMORY_OPTIMIZER**: Enable dynamic memory adjustment

## How Filters Work

### Filter Execution Flow

When a job is submitted to OpenCue:

```
1. Job Submission
   ├─→ Cuebot receives job
   └─→ Filter evaluation begins

2. Filter Evaluation (in order)
   ├─→ Filter 1: Check matchers
   │   ├─→ Match? Execute actions
   │   └─→ No match? Skip to next filter
   ├─→ Filter 2: Check matchers
   │   └─→ ...
   └─→ Continue until STOP_PROCESSING or end

3. Job Dispatch
   └─→ Job configured with all applied actions
```

### Filter Order

Filters execute in numerical order (lowest to highest). This allows you to:

1. **Apply general policies first** (order: 10)
2. **Override with specific rules** (order: 20)
3. **Apply final configurations** (order: 30)

**Example:**
```
Order 10: All jobs → Set default priority 500
Order 20: Hero shots → Set priority 900, STOP_PROCESSING
Order 30: Test jobs → Set priority 100
```

Result: Hero shots get priority 900 and skip order 30 filter. Other jobs continue through all filters.

### STOP_PROCESSING

The `STOP_PROCESSING` action prevents subsequent filters from evaluating. Use cases:

- **Performance**: Skip unnecessary filter checks
- **Policy Enforcement**: Prevent overrides of critical settings
- **Conflict Avoidance**: Stop before conflicting filters

## Common Use Cases

### Use Case 1: Department-Based Organization

**Scenario:** Automatically organize jobs by department using groups

**What are Groups?**

Groups are organizational folders within OpenCue for managing and tracking jobs. Think of them as folders where you can organize jobs by:
- Department (lighting-group, fx-group, comp-group)
- Priority level (hero-group, priority-group, background-group)
- Show phase (preproduction-group, production-group, finals-group)

Shows are the top-level container (like a project), while groups are organizational folders within a show.

**Creating Groups:**

Before using MOVE_JOB_TO_GROUP actions, create the target groups:
1. In CueGUI, open CueCommander (**Window** > **Open Windows: CueCommander**)
2. Select **Views/Plugins** > **OpenCuecommander** > **Monitor Cue**
3. Right-click on a show name (or existing group) in the Show/Root Group tree
4. Select **"Create Group..."**
5. Name your group (e.g., "lighting-group")

**Example Filter Configuration:**

```
Filter: "Lighting Department"
├── Matcher: Job name begins with "light_"
└── Action: MOVE_JOB_TO_GROUP → "lighting-group"

Filter: "Compositing Department"
├── Matcher: Job name begins with "comp_"
└── Action: MOVE_JOB_TO_GROUP → "compositing-group"

Note: Create "lighting-group" and "compositing-group" first via
      CueCommander > Monitor Cue > Right-click show > Create Group
```

### Use Case 2: Renderer-Specific Configuration

**Note:** Typically the Service itself can assign these settings by default. The filter can be used, then to override the service settings for some other criteria, like artist or job name.

**Scenario:** Arnold renders need GPU hosts and high memory

```
Filter: "Arnold GPU Requirements"
├── Matcher: Service is "arnold"
├── Action: SET_ALL_RENDER_LAYER_TAGS → "gpu,arnold_license"
├── Action: SET_ALL_RENDER_LAYER_MEMORY → 16777216 (16GB)
└── Action: SET_MEMORY_OPTIMIZER → true
```

### Use Case 3: Priority Management

**Scenario:** Hero shots get priority, tests get deprioritized

```
Filter: "Hero Shot Priority" (Order: 10)
├── Matcher: Job name contains "hero"
├── Action: SET_JOB_PRIORITY → 900
└── Action: STOP_PROCESSING

Filter: "Test Job Priority" (Order: 20)
├── Matcher: Job name starts with "test_"
└── Action: SET_JOB_PRIORITY → 100
```

### Use Case 4: Resource Limits by User

**Scenario:** Limit junior artists to prevent farm overuse

```
Filter: "Junior Artist Limits"
├── Matcher: User matches "junior_.*" (regex)
├── Action: SET_JOB_MAX_CORES → 10.0
└── Action: SET_ALL_RENDER_LAYER_MEMORY → 4194304 (4GB)
```

### Use Case 5: Multi-Stage Pipeline Jobs

**Scenario:** Complex jobs with pre-processing, utilities, and rendering

```
Filter: "Pipeline Job Configuration"
├── Matcher: Job name contains "pipeline"
├── Action: SET_ALL_PRE_LAYER_MIN_CORES → 2.0
├── Action: SET_ALL_PRE_LAYER_TAGS → "fast_cpu"
├── Action: SET_ALL_UTIL_LAYER_MEMORY → 8388608 (8GB)
├── Action: SET_ALL_UTIL_LAYER_TAGS → "fast_storage"
└── Action: SET_ALL_RENDER_LAYER_MIN_CORES → 8.0
```

## Layer Types Explained

### Render Layers

**Purpose:** Primary output generation (rendered frames, images)

**Characteristics:**
- Typically the most resource-intensive
- Usually the majority of frames in a job
- Often GPU-accelerated
- High memory requirements for complex scenes

**Typical Operations:**
- 3D rendering (Arnold, V-Ray, RenderMan)
- Compositing final outputs
- Image sequence generation

**Filter Strategy:** Allocate maximum resources, target high-performance hosts

### Utility Layers

**Purpose:** Supporting operations that assist rendering

**Characteristics:**
- Pre/post-processing tasks
- Cache generation and management
- Data transformation
- Moderate resource requirements

**Typical Operations:**
- Alembic cache generation
- Geometry baking
- Texture processing
- Scene file conversion

**Filter Strategy:** Moderate resources, may need fast storage access

### Pre-Processing Layers

**Purpose:** Initial job setup and validation

**Characteristics:**
- Run before render layers
- Quick execution (seconds to minutes)
- Low to moderate resource needs
- Critical for job success

**Typical Operations:**
- Asset validation
- Dependency checking
- Environment setup
- License availability checks

**Filter Strategy:** Low resource allocation, fast execution hosts

## Filter Design Patterns

### Pattern: Show-Based Configuration

Apply consistent settings across all jobs in a show:

```
Filter: "Show XYZ Configuration"
├── Matcher: Show is "xyz-production"
├── Action: SET_JOB_MIN_CORES → 4.0
├── Action: SET_ALL_RENDER_LAYER_MEMORY → 8388608
└── Action: SET_ALL_RENDER_LAYER_TAGS → "fast_network"
```

### Pattern: Staged Resource Allocation

Different resources for different layer types:

```
Filter: "Staged Pipeline Resources"
├── Matcher: Job name matches ".*_pipeline_.*"
├── Action: SET_ALL_PRE_LAYER_MAX_CORES → 2.0
├── Action: SET_ALL_UTIL_LAYER_MAX_CORES → 4.0
└── Action: SET_ALL_RENDER_LAYER_MIN_CORES → 8.0
```

### Pattern: Time-Based Automation

Pause jobs during specific hours (implemented via custom matcher):

```
Filter: "Daytime Test Job Pause"
├── Matcher: Job name starts with "test_"
└── Action: PAUSE_JOB → true
```

### Pattern: Fail-Safe Limits

Prevent any single job from monopolizing resources:

```
Filter: "Global Resource Ceiling" (Order: 999)
├── Matcher: Job name matches ".*" (all jobs)
└── Action: SET_JOB_MAX_CORES → 100.0
```

## Best Practices

### Filter Organization

1. **Use descriptive names**: "Arnold GPU Jobs" vs "Filter_1"
2. **Order strategically**: General rules first, specific rules second
3. **Document complex matchers**: Comment regex patterns
4. **Test before production**: Use test jobs to verify behavior

### Matcher Design

1. **Be specific**: Narrow matchers reduce unintended matches
2. **Use appropriate match types**: REGEX for patterns, IS for exact matches
3. **Combine matchers**: Use MATCH_ALL for precise targeting
4. **Consider wildcards**: Job name patterns should account for variations

### Action Configuration

1. **Set realistic values**: Don't over-allocate resources
2. **Use layer-specific actions**: Target the right layer type
3. **Memory in kilobytes**: Remember conversion (1GB = 1048576 KB)
4. **Validate core counts**: Ensure max >= min

### Performance

1. **Minimize filter count**: Consolidate related rules
2. **Use STOP_PROCESSING**: Prevent unnecessary evaluations
3. **Order efficiently**: Most common matches first
4. **Disable unused filters**: Keep only active rules enabled

## Filter Administration

### Who Manages Filters?

Typically managed by:
- **Production Services and Resources (PSRs) Teams**: Overall farm policies
- **Pipeline Engineers**: Overall filter strategy
- **Show Supervisors**: Show-specific configurations
- **System Administrators**: Resource policies and limits
- **Technical Directors**: Specialized workflow rules

### When to Create Filters

Consider filters when:
- Multiple jobs need consistent configuration
- Resource allocation requires automation
- Department workflows have specific requirements
- Manual configuration becomes error-prone
- Scaling to many jobs makes manual setup impractical

### Filter Lifecycle

1. **Design**: Identify automation opportunity
2. **Create**: Build matchers and actions in CueGUI
3. **Test**: Verify with test jobs
4. **Deploy**: Enable for production use
5. **Monitor**: Track effectiveness and edge cases
6. **Refine**: Adjust based on operational experience

## Troubleshooting Filters

### Filter Not Triggering

**Symptoms:** Jobs don't receive expected configuration

**Check:**
- Filter is enabled
- Matchers correctly configured
- Job properties match criteria
- Filter order allows execution
- Previous filter didn't use STOP_PROCESSING

### Conflicting Filters

**Symptoms:** Unexpected job configuration

**Causes:**
- Multiple filters modify same property
- Filter order causes overrides
- MATCH_ANY too broad

**Solutions:**
- Review filter execution order
- Use STOP_PROCESSING to prevent conflicts
- Make matchers more specific
- Consolidate related filters

### Performance Issues

**Symptoms:** Slow job submission

**Causes:**
- Too many active filters
- Complex regex matchers
- Inefficient filter order

**Solutions:**
- Disable unused filters
- Simplify matchers where possible
- Order most common matches first
- Use STOP_PROCESSING to short-circuit

## Security Considerations

Filters can enforce security policies:

- **Resource Quotas**: Prevent resource exhaustion
- **User Restrictions**: Limit capabilities by user
- **Show Isolation**: Keep shows in separate groups
- **Priority Enforcement**: Prevent priority abuse

**Example Security Filter:**
```
Filter: "Enforce Maximum Cores"
├── Matcher: All jobs (universal)
├── Action: SET_JOB_MAX_CORES → 50.0
└── Order: 999 (runs last)
```

## Integration with Pipeline

Filters integrate with broader pipeline automation:

### Submission Tools

Job submission tools can leverage filters:
- Set job names to trigger specific filters
- Tag jobs with show/user for automatic grouping
- Rely on filters for resource configuration

### Monitoring

Track filter effectiveness:
- Monitor filter execution logs
- Measure resource utilization by filter
- Identify filters that need tuning

### Custom Integration

API access enables:
- Programmatic filter management
- Dynamic filter creation
- Integration with external systems

## What's Next?

To learn more about filters:

- **[Using Filters User Guide](/docs/user-guides/using-filters/)** - User Guides: Practical filter usage
- **[Filter Actions Reference](/docs/reference/filter-actions-reference/)** - Reference: Complete filter actions documentation
- **[Filter Tutorial](/docs/tutorials/filter-tutorial/)** - Tutorials: Step-by-step filter examples
- **[Filter Development](/docs/developer-guide/filter-development/)** - Developer Guide: Filter Development

## Summary

Filters and actions provide powerful automation for OpenCue job management:

- **Matchers** evaluate job properties against criteria
- **Actions** automatically configure jobs and layers
- **Layer types** (Render, Utility, Pre) enable granular control
- **Filter order** determines execution sequence
- **Best practices** ensure effective automation
- **Use cases** span department organization, resource allocation, and policy enforcement

Well-designed filters reduce manual intervention, enforce consistency, and optimize farm utilization across production pipelines.
