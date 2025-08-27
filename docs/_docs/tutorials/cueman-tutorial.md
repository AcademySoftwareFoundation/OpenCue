---
title: "Cueman Tutorial"
nav_order: 53
parent: "Tutorials"
layout: default
date: 2025-08-06
description: >
  Learn how to use Cueman for efficient OpenCue job management with 
  practical examples and real-world scenarios.
---

# Cueman Tutorial

This tutorial will guide you through using Cueman for OpenCue job management with practical examples and real-world scenarios.

## Prerequisites

Before starting this tutorial, ensure you have:
- Access to an OpenCue server
- Cueman installed (`pip install opencue-cueman`)
- Environment variables configured:
  ```bash
  export OPENCUE_HOSTS="your-cuebot-server:8443"
  export OPENCUE_FACILITY="your-facility-code"
  ```

## Part 1: Basic Operations

### Getting Help

Start by exploring Cueman's capabilities:

```bash
# Display all available commands
cueman -h

# Running without arguments also shows help
cueman
```

### Viewing Job Information

Let's start with basic job inspection:

```bash
# List all jobs (using cueadmin)
cueadmin -lj

# Get detailed information about a specific job
cueman -info show_shot_lighting_v001
```

Example output:
```
------------------------------------------------------------
job: show_shot_lighting_v001

   start time: 08/03 21:08
        state: IN_PROGRESS
     services: arnold, nuke
Min/Max cores: 8.00 / 100.00

total number of frames: 250
                  done: 158
               running: 15
       waiting (ready): 75
                failed: 2
```

### Listing Frames

View frames with different levels of detail:

```bash
# List all frames
cueman -lf show_shot_lighting_v001

# List only running frames
cueman -lf show_shot_lighting_v001 -state RUNNING

# List frames 1-50
cueman -lf show_shot_lighting_v001 -range 1-50
```

## Part 2: Job Management

### Pausing and Resuming Jobs

Control job execution:

```bash
# Pause a single job
cueman -pause show_shot_lighting_v001

# Pause multiple jobs
cueman -pause show_shot_001,show_shot_002,show_shot_003

# Pause all test jobs using wildcards
cueman -pause "test_*"

# Resume specific jobs
cueman -resume show_shot_001,show_shot_002
```

### Setting Job Parameters

Configure job behavior:

```bash
# Set maximum retries to 5
cueman -retries show_shot_lighting_v001 5

# Enable auto-eat (automatically eat dead frames)
cueman -autoeaton show_shot_lighting_v001

# Disable auto-eat
cueman -autoeatoff show_shot_lighting_v001
```

## Part 3: Frame Operations

### Managing Running Frames

```bash
# Kill all running frames in a job
cueman -kill show_shot_lighting_v001

# Kill only frames running longer than 6 hours
cueman -kill show_shot_lighting_v001 -duration gt6

# Kill frames using more than 16GB memory
cueman -kill show_shot_lighting_v001 -memory gt16
```

### Retrying Failed Frames

```bash
# Retry all dead frames
cueman -retry show_shot_lighting_v001 -state DEAD

# Retry specific frame range
cueman -retry show_shot_lighting_v001 -range 1-50 -state DEAD

# Retry frames on specific layer
cueman -retry show_shot_lighting_v001 -layer render_layer -state DEAD
```

### Eating Frames

Mark frames as completed without running them:

```bash
# Eat all waiting frames
cueman -eat show_shot_lighting_v001 -state WAITING

# Eat specific problematic frames
cueman -eat show_shot_lighting_v001 -range 45,67,89

# Eat all frames in preview layer
cueman -eat show_shot_lighting_v001 -layer preview_layer
```

## Part 4: Advanced Filtering

### Combining Multiple Filters

Cueman's power comes from combining filters:

```bash
# List running frames on render_layer using more than 8GB
cueman -lf show_shot_lighting_v001 \
  -state RUNNING \
  -layer render_layer \
  -memory gt8

# Kill frames running more than 12 hours with high memory
cueman -kill show_shot_lighting_v001 \
  -duration gt12 \
  -memory gt16

# Retry dead frames in specific range on specific layer
cueman -retry show_shot_lighting_v001 \
  -state DEAD \
  -range 1-100 \
  -layer heavy_sim
```

### Working with Memory Filters

```bash
# List frames using 2-4 GB
cueman -lf show_shot_lighting_v001 -memory 2-4

# List frames using less than 2 GB
cueman -lf show_shot_lighting_v001 -memory lt2

# Kill frames using more than 32 GB
cueman -kill show_shot_lighting_v001 -memory gt32
```

### Working with Duration Filters

```bash
# List frames running 1-2 hours
cueman -lf show_shot_lighting_v001 -duration 1-2

# List frames running more than 3.5 hours
cueman -lf show_shot_lighting_v001 -duration gt3.5

# Kill frames stuck for more than 24 hours
cueman -kill show_shot_lighting_v001 -duration gt24
```

## Part 5: Frame Manipulation

### Staggering Frames

Prevent resource spikes by staggering frame starts:

```bash
# Stagger frames 1-100 by 5 frame increments
cueman -stagger show_shot_lighting_v001 1-100 5

# Stagger simulation frames to avoid concurrent starts
cueman -stagger show_shot_lighting_v001 1-50 10 -layer sim_layer
```

### Reordering Frames

Control execution priority:

```bash
# Move frames 50-100 to front of queue
cueman -reorder show_shot_lighting_v001 50-100 FIRST

# Move frames 1-49 to back of queue
cueman -reorder show_shot_lighting_v001 1-49 LAST

# Reverse frame order for debugging
cueman -reorder show_shot_lighting_v001 1-100 REVERSE
```

## Part 6: Real-World Scenarios

### Scenario 1: Morning Farm Cleanup

Start your day by cleaning up overnight issues:

```bash
# 1. Check for stuck frames from overnight
cueman -lf "*" -duration gt12

# 2. Kill frames stuck for more than 12 hours
for job in show_shot_001 show_shot_002; do
    echo "Checking $job for stuck frames..."
    cueman -kill $job -duration gt12
done

# 3. Retry the killed frames
for job in show_shot_001 show_shot_002; do
    cueman -retry $job -state DEAD
done

# 4. Clean up test jobs
cueman -term "test_*_overnight" -force
```

### Scenario 2: Emergency Priority Change

Client needs urgent delivery:

```bash
# 1. Pause all non-critical jobs
cueman -pause "dev_*,test_*,rnd_*" -force

# 2. Move hero frames to front
cueman -reorder hero_shot_final 1-100 FIRST

# 3. Increase retry limit for critical job
cueman -retries hero_shot_final 10

# 4. Kill and retry any stuck hero frames
cueman -kill hero_shot_final -duration gt2
cueman -retry hero_shot_final -state DEAD
```

### Scenario 3: Memory Crisis Management

Handle out-of-memory situations:

```bash
# 1. Identify high memory frames
echo "=== High Memory Frames ==="
cueman -lf show_heavy_sim -memory gt16

# 2. Kill frames using excessive memory
cueman -kill show_heavy_sim -memory gt32

# 3. Analyze failure patterns
cueman -lf show_heavy_sim -state DEAD

# 4. Eat problematic frames if necessary
cueman -eat show_heavy_sim -range 145,267,389 -force

# 5. Retry remaining dead frames
cueman -retry show_heavy_sim -state DEAD
```

### Scenario 4: Weekend Batch Processing

Set up jobs for weekend processing:

```bash
# 1. Pause all jobs
cueman -pause "*"

# 2. Resume jobs in priority order with delays
cueman -resume "hero_*"
sleep 600  # Wait 10 minutes

cueman -resume "show1_*"
sleep 600

cueman -resume "show2_*"
sleep 600

# 3. Set conservative retry limits
for job in $(cueadmin -lj | grep show_ | awk '{print $1}'); do
    cueman -retries $job 3
    cueman -autoeaton $job
done
```

### Scenario 5: Debugging Frame Failures

Investigate systematic failures:

```bash
# 1. Get overview of failed frames
job="show_shot_problem_v001"
cueman -info $job

# 2. List all dead frames with details
echo "=== Dead Frames ==="
cueman -lf $job -state DEAD

# 3. Check if failures are memory-related
echo "=== High Memory Dead Frames ==="
cueman -lf $job -state DEAD -memory gt8

# 4. Check if failures are in specific layer
echo "=== Dead Frames by Layer ==="
for layer in render_layer sim_layer comp_layer; do
    echo "Layer: $layer"
    cueman -lf $job -state DEAD -layer $layer | wc -l
done

# 5. Retry frames selectively
cueman -retry $job -state DEAD -range 1-50
sleep 300  # Wait 5 minutes

# 6. If still failing, eat and continue
cueman -eat $job -range 45 -force
```

## Part 7: Monitoring and Reporting

### Process Monitoring

Track active processes:

```bash
# List all running processes
cueman -lp show_shot_lighting_v001

# Monitor high memory processes
cueman -lp show_shot_lighting_v001 -memory gt8

# Monitor long-running processes
cueman -lp show_shot_lighting_v001 -duration gt2
```

### Layer Analysis

Understand job structure:

```bash
# List all layers with statistics
cueman -ll show_shot_lighting_v001

# Check specific layer progress
cueman -lf show_shot_lighting_v001 -layer render_layer | \
  awk '{print $2}' | sort | uniq -c
```

## Part 8: Best Practices

### 1. Always Preview Before Acting

```bash
# First, see what will be affected
cueman -lf show_shot_001 -state RUNNING -duration gt6

# Review the output, then act if correct
cueman -kill show_shot_001 -state RUNNING -duration gt6
```

### 2. Use Specific Filters

```bash
# Too broad - might affect unintended frames
cueman -kill show_shot_001

# Better - specific targeting
cueman -kill show_shot_001 -layer sim_layer -range 1-50 -state RUNNING
```

### 3. Document Your Actions

```bash
# Add comments when terminating jobs
cueman -term failed_test_001
# Then document in your tracking system why it was terminated
```

### 4. Test on Small Sets First

```bash
# Test on a few frames first
cueman -retry show_shot_001 -state DEAD -range 1-5

# If successful, apply to all
cueman -retry show_shot_001 -state DEAD
```

## Part 9: Troubleshooting

### Debugging Connection Issues

```bash
# Enable verbose logging
cueman -v -info show_shot_001

# Specify server explicitly
cueman -server cuebot.example.com:8443 -lf show_shot_001

# Check environment
echo "OPENCUE_HOSTS: $OPENCUE_HOSTS"
echo "OPENCUE_FACILITY: $OPENCUE_FACILITY"
```

### Common Error Messages

**Job doesn't exist:**
```bash
$ cueman -lf nonexistent_job
Error: Job 'nonexistent_job' does not exist.
```

**No frames match criteria:**
```bash
$ cueman -kill show_shot_001 -state SUCCEEDED
No frames found matching criteria
```

## Summary

You've learned how to:
- Perform basic job and frame operations
- Use advanced filtering for precise control
- Combine filters for complex selections
- Handle real-world production scenarios
- Monitor and troubleshoot render farm issues

Cueman provides capabilities for OpenCue management. Start with simple operations and gradually incorporate more advanced features as you become comfortable with the tool.

## Next Steps

- Explore the [Cueman Reference](/OpenCue/docs/reference/tools/cueman/) for complete command documentation
- Practice with test jobs before using on production
- Create scripts combining Cueman commands for automated workflows
- Continue to the [Developer Guide](/docs/developer-guide/) to learn about contributing to OpenCue or developing applications that integrate with it