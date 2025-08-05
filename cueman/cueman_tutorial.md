# Cueman Tutorial

Cueman is a command-line job management tool for OpenCue that provides efficient job control operations. This tutorial will guide you through its features with practical examples and real-world scenarios.

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Getting Started](#getting-started)
3. [Basic Commands](#basic-commands)
4. [Job Management](#job-management)
5. [Frame Operations](#frame-operations)
6. [Advanced Filtering](#advanced-filtering)
7. [Frame Manipulation](#frame-manipulation)
8. [Real-World Scenarios](#real-world-scenarios)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## Installation & Setup

### Prerequisites
- OpenCue server running and accessible
- Python 3.7 or higher
- OpenCue Python packages installed

### Installation
```bash
# Install from PyPI
pip install opencue-cueman

# Or install from source
cd OpenCue/cueman
pip install .
```

### Configuration
Set up your environment variables:
```bash
export OPENCUE_HOSTS="your-cuebot-server:8443"
export OPENCUE_FACILITY="your-facility-code"
```

## Getting Started

### Display Help
```bash
# Show all available commands and options
cueman -h
cueman --help

# Running without arguments also shows help
cueman
```

### Common Global Options
- `-h, --help`: Show help message and exit
- `-v, --verbose`: Enable verbose logging for debugging
- `-server HOSTNAME`: Specify OpenCue server address(es)
- `-facility CODE`: Specify facility code
- `-force`: Skip confirmation prompts for destructive operations

### Enable Verbose Logging
```bash
# Useful for debugging connection issues
cueman -v -info job_name
```

## Basic Commands

### 1. List Frames (`-lf`)
Display frames for a job with detailed information:

```bash
cueman -lf job_name
```

Example output:
```
Frame                               Status      Host            Start         End          Runtime     Mem   Retry  Exit
------------------------------------------------------------------------------------------------------------------------
0001-render_layer                   SUCCEEDED   host01/8.00/0   08/03 21:08   08/03 21:08  00:00:12    2.5G      0     0
0002-render_layer                   RUNNING     host02/8.00/0   08/03 21:08   --/-- --:--  00:05:33    4.2G      0    -1
0003-render_layer                   WAITING     /0.00/0         --/-- --:--   --/-- --:--               0K       0    -1
0004-render_layer                   DEAD        host03/8.00/0   08/03 21:09   08/03 21:10  00:01:23    512M      3     1
```

### 2. List Running Processes (`-lp`)
Monitor active processes on the render farm:

```bash
cueman -lp job_name
```

Example output:
```
Host       Cores   Memory                   Job                            / Frame                          Start        Runtime
172.18.0.4 8.00    4.2G of 8.0G (52.50%)   show_shot_lighting_v001       / 0046-render_layer             08/03 21:19  00:05:33
172.18.0.5 8.00    6.1G of 8.0G (76.25%)   show_shot_lighting_v001       / 0050-render_layer             08/03 21:19  00:04:27
```

### 3. List Layers (`-ll`)
View layer information for a job:

```bash
cueman -ll job_name
```

Example output:
```
Job: show_shot_lighting_v001 has 3 layers

Layer                          Total    Done     Running  Waiting  Failed
---------------------------------------------------------------------------
render_layer                   100      58       15       25       2
comp_layer                     50       0        0        50       0
preview_layer                  100      100      0        0        0
   tags: gpu | heavy | production
```

### 4. Get Job Information (`-info`)
Display comprehensive job details:

```bash
cueman -info job_name
```

Example output:
```
------------------------------------------------------------
job: show_shot_lighting_v001

   start time: 08/03 21:08
        state: IN_PROGRESS
         type: 3D
 architecture: x86_64
     services: arnold, nuke
Min/Max cores: 8.00 / 100.00

total number of frames: 250
                  done: 158
               running: 15
       waiting (ready): 75
      waiting (depend): 0
                failed: 2
   total frame retries: 6

this is a Opencue job with 3 layers

render_layer  (100 frames, 58 done)
   average frame time: 00:12:34
   average ram usage: 4.5GB
   tags: gpu | heavy
```

## Job Management

### Pause Jobs
Temporarily stop job execution:

```bash
# Pause single job
cueman -pause job_name

# Pause multiple jobs
cueman -pause job1,job2,job3

# Pause with wildcards
cueman -pause "show_*_lighting_*"
```

Example:
```bash
cueman -pause show_shot_001,show_shot_002
```
Output:
```
Pausing Job: show_shot_001
---
Pausing Job: show_shot_002
---
```

### Resume Jobs
Resume paused jobs:

```bash
cueman -resume job1,job2
```

### Terminate Jobs
Permanently stop and remove jobs:

```bash
# With confirmation prompt
cueman -term job1,job2

# Skip confirmation (use with caution!)
cueman -term job1,job2 -force
```

### Set Maximum Retries
Control how many times frames can retry:

```bash
cueman -retries job_name 5
```

### Auto-Eat Management
Automatically mark dead frames as eaten:

```bash
# Enable auto-eat
cueman -autoeaton job1,job2

# Disable auto-eat
cueman -autoeatoff job1,job2
```

## Frame Operations

### Kill Running Frames
Stop currently executing frames:

```bash
# Kill all running frames
cueman -kill job_name

# Kill specific frames
cueman -kill job_name -range 1-50

# Kill frames on specific layer
cueman -kill job_name -layer render_layer

# Kill frames with high memory usage
cueman -kill job_name -memory gt16
```

### Retry Frames
Requeue frames for execution:

```bash
# Retry all frames
cueman -retry job_name

# Retry dead frames only
cueman -retry job_name -state DEAD

# Retry specific range
cueman -retry job_name -range 1-50 -state DEAD
```

### Eat Frames
Mark frames as succeeded without running:

```bash
# Eat all frames
cueman -eat job_name

# Eat waiting frames
cueman -eat job_name -state WAITING

# Eat specific layer
cueman -eat job_name -layer preview_layer
```

### Mark Frames as Done
Resolve dependencies without running frames:

```bash
cueman -done job_name -range 1-100
```

## Advanced Filtering

### State Filters
Filter frames by execution state:

```bash
# Available states: WAITING, RUNNING, SUCCEEDED, DEAD, EATEN, DEPEND

# List only running and waiting frames
cueman -lf job_name -state RUNNING WAITING

# Kill only running frames
cueman -kill job_name -state RUNNING

# Retry only dead frames
cueman -retry job_name -state DEAD
```

### Range Filters
Target specific frame numbers:

```bash
# Continuous range
cueman -lf job_name -range 1-100

# Individual frames
cueman -lf job_name -range 1,3,5,7,9

# Mixed ranges
cueman -lf job_name -range 1-10,20,30-40,100
```

### Layer Filters
Work with specific layers:

```bash
# Single layer
cueman -lf job_name -layer render_layer

# Multiple layers
cueman -lf job_name -layer render_layer comp_layer

# Kill frames in specific layer
cueman -kill job_name -layer heavy_sim -range 1-50
```

### Memory Filters
Filter by memory usage:

```bash
# Range: 2-4 GB
cueman -lf job_name -memory 2-4

# Less than 2 GB
cueman -lf job_name -memory lt2

# Greater than 16 GB
cueman -lf job_name -memory gt16

# Kill high memory frames
cueman -kill job_name -memory gt32
```

### Duration Filters
Filter by runtime:

```bash
# Range: 1-2 hours
cueman -lf job_name -duration 1-2

# More than 3.5 hours
cueman -lf job_name -duration gt3.5

# Less than 0.5 hours
cueman -lf job_name -duration lt0.5

# Kill stuck frames (running > 12 hours)
cueman -kill job_name -duration gt12
```

### Pagination
Handle large result sets:

```bash
# Default: 1000 frames per page
cueman -lf job_name -page 2

# Custom page size
cueman -lf job_name -limit 500

# Combine with filters
cueman -lf job_name -state WAITING -limit 100 -page 3
```

## Frame Manipulation

### Stagger Frames
Add delays between frame starts:

```bash
# Stagger frames 1-100 by 5 frame increments
cueman -stagger job_name 1-100 5

# Stagger specific layer
cueman -stagger job_name 1-50 10 -layer sim_layer
```

### Reorder Frames
Change frame execution order:

```bash
# Move frames to front of queue
cueman -reorder job_name 50-100 FIRST

# Move frames to back of queue
cueman -reorder job_name 1-49 LAST

# Reverse frame order
cueman -reorder job_name 1-100 REVERSE

# Reorder specific layer
cueman -reorder job_name 1-50 FIRST -layer hero_layer
```

## Real-World Scenarios

### Scenario 1: Handling Stuck Frames
Frames running too long often indicate problems:

```bash
# Step 1: Find frames running more than 12 hours
cueman -lf job_name -duration gt12

# Step 2: Check their memory usage
cueman -lf job_name -duration gt12 -memory gt0

# Step 3: Kill stuck frames
cueman -kill job_name -duration gt12

# Step 4: Retry them with adjusted settings
cueman -retry job_name -state DEAD
```

### Scenario 2: Memory Management
Handle out-of-memory failures:

```bash
# Find high memory frames
cueman -lf job_name -memory gt16

# Kill frames using too much memory
cueman -kill job_name -memory gt32

# Check which frames failed
cueman -lf job_name -state DEAD

# Retry with memory limits adjusted
cueman -retry job_name -state DEAD -layer heavy_render
```

### Scenario 3: Priority Handling
Manage urgent shots:

```bash
# Pause non-critical jobs
cueman -pause "test_*,dev_*" -force

# Move hero frames to front
cueman -reorder hero_shot_final 1-100 FIRST

# Resume critical jobs first
cueman -resume "hero_*,client_*"
```

### Scenario 4: Batch Operations
Efficient farm management:

```bash
# Morning cleanup: terminate overnight test jobs
cueman -term "test_*_overnight" -force

# Pause all lighting jobs for maintenance
cueman -pause "*_lighting_*"

# Resume in batches
cueman -resume "show1_*"
sleep 300  # Wait 5 minutes
cueman -resume "show2_*"
```

### Scenario 5: Failed Frame Analysis
Investigate and fix failures:

```bash
# List all dead frames with details
cueman -lf job_name -state DEAD

# Check if it's memory related
cueman -lf job_name -state DEAD -memory gt8

# Retry with specific range
cueman -retry job_name -state DEAD -range 1-50

# If still failing, eat problematic frames
cueman -eat job_name -range 45,67,89 -force
```

## Best Practices

### 1. Always Preview Before Destructive Operations
```bash
# List what will be affected
cueman -lf job_name -state RUNNING -duration gt6

# Then kill if correct
cueman -kill job_name -state RUNNING -duration gt6
```

### 2. Use Specific Filters
```bash
# Bad: Too broad
cueman -kill job_name

# Good: Specific targeting
cueman -kill job_name -layer sim_layer -range 1-50 -state RUNNING
```

### 3. Batch Similar Operations
```bash
# Efficient: Single command for multiple jobs
cueman -pause "show_shot_*" -force

# Inefficient: Multiple commands
cueman -pause show_shot_001
cueman -pause show_shot_002
cueman -pause show_shot_003
```

### 4. Monitor Before Acting
```bash
# Check job state first
cueman -info job_name

# List frames to verify filters
cueman -lf job_name -state DEAD -layer heavy_sim

# Then perform operation
cueman -retry job_name -state DEAD -layer heavy_sim
```

### 5. Use Auto-Eat Wisely
```bash
# Good for test jobs
cueman -autoeaton "test_*"

# Avoid for production
cueman -autoeatoff "hero_*,final_*"
```

## Troubleshooting

### Connection Issues
```bash
# Test with explicit server
cueman -server cuebot01:8443 -info test_job

# Enable verbose mode
cueman -v -lf job_name

# Check environment
echo $OPENCUE_HOSTS
```

### Permission Errors
Some operations require elevated permissions:
- Job termination
- Auto-eat settings
- Priority changes

Contact your system administrator if you encounter permission errors.

### Common Error Messages

**Job does not exist:**
```bash
$ cueman -info nonexistent_job
Error: Job 'nonexistent_job' does not exist.
```
Solution: Verify job name with `cueadmin -lj | grep pattern`

**No frames match criteria:**
```bash
$ cueman -lf job_name -state RUNNING
# (No output)
```
Solution: Broaden your search criteria or check job state

**Connection timeout:**
```bash
Error: Unable to connect to OpenCue server
```
Solution: Check server address and network connectivity

### Performance Tips

1. **Use pagination for large jobs:**
   ```bash
   cueman -lf huge_job -limit 500 -page 1
   ```

2. **Combine filters to reduce results:**
   ```bash
   cueman -lf job_name -state DEAD -layer render -range 1-1000
   ```

3. **Use wildcards carefully:**
   ```bash
   # This might match too many jobs
   cueman -pause "*"
   
   # Be more specific
   cueman -pause "test_shot_*"
   ```

## Advanced Tips

### Shell Scripting with Cueman
```bash
#!/bin/bash
# Monitor and restart stuck frames

JOBS=$(cueadmin -lj -state IN_PROGRESS | grep "show_")

for job in $JOBS; do
    echo "Checking $job for stuck frames..."
    
    # Find frames running > 8 hours
    STUCK=$(cueman -lf $job -duration gt8 -state RUNNING | wc -l)
    
    if [ $STUCK -gt 0 ]; then
        echo "Found $STUCK stuck frames in $job"
        cueman -kill $job -duration gt8 -force
        cueman -retry $job -state DEAD
    fi
done
```

### Combining with Other Tools
```bash
# Use with cueadmin for complete workflow
cueadmin -lj | grep "PAUSED" | while read job; do
    cueman -resume $job
done

# Monitor specific shows
watch -n 30 'cueman -lf show_hero_shot -state RUNNING,DEAD'
```

## Summary

Cueman provides powerful command-line control over OpenCue jobs. Key takeaways:

- Always use filters to target specific frames
- Preview operations before executing destructive commands
- Combine multiple filters for precise control
- Use `-force` flag carefully
- Monitor jobs before and after operations

For the latest updates and additional documentation, refer to the OpenCue documentation at https://www.opencue.io/
