---
title: "Cueman - CLI Job Management Tool"
nav_order: 46
parent: "Command Line Tools"
grand_parent: "Reference"
layout: default
date: 2025-08-06
description: >
  Cueman is a command-line job management tool for OpenCue that provides 
  efficient job control operations with advanced filtering and batch capabilities.
---

# Cueman - CLI Job Management Tool

Cueman is a command-line interface for managing OpenCue jobs, frames, and processes. It provides streamlined operations for job control, frame management, and batch processing with advanced filtering capabilities.

## Overview

Cueman extends the functionality of `cueadmin` and the OpenCue Python API, enabling users to efficiently manage render farm operations through an intuitive command-line interface.

### Key Features

- **Job Control**: Pause, resume, and terminate jobs with batch operations
- **Frame Management**: Retry, kill, eat, and manipulate frames with precision
- **Smart Filtering**: Filter by state, memory, duration, layers, and ranges
- **Process Monitoring**: View and analyze running processes
- **Batch Operations**: Handle multiple jobs with wildcards and lists
- **Frame Manipulation**: Stagger and reorder frames for optimal scheduling

## Installation

### Prerequisites

- OpenCue server running and accessible
- Python 3.7 or higher
- OpenCue Python packages installed

### Install from PyPI

```bash
pip install opencue-cueman
```

### Install from Source

```bash
cd OpenCue/cueman
pip install .
```

### Configuration

Set up your environment variables:

```bash
export OPENCUE_HOSTS="your-cuebot-server:8443"
export OPENCUE_FACILITY="your-facility-code"
```

## Quick Start

1. **Verify installation:**
   ```bash
   cueman -h  # Shows help message
   ```

2. **List available jobs:**
   ```bash
   cueadmin -lj  # Lists all jobs
   ```

3. **Get job information:**
   ```bash
   cueman -info job_name
   ```

4. **List frames:**
   ```bash
   cueman -lf job_name
   ```

## Command Reference

### Global Options

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `-v, --verbose` | Enable verbose logging |
| `-server HOSTNAME` | Specify OpenCue server address |
| `-facility CODE` | Specify facility code |
| `-force` | Skip confirmation prompts |

### Display Commands

#### List Frames (`-lf`)

Display frames for a job with detailed information:

```bash
cueman -lf job_name [filters]
```

Example output:
```
Frame                    Status      Host         Start       End         Runtime   Mem    Retry  Exit
0001-render_layer       SUCCEEDED   host01       08/03 21:08 08/03 21:08 00:00:12  2.5G   0      0
0002-render_layer       RUNNING     host02       08/03 21:08 --/-- --:-- 00:05:33  4.2G   0      -1
```

#### List Processes (`-lp`)

Monitor active processes:

```bash
cueman -lp job_name [filters]
```

#### List Layers (`-ll`)

View layer information:

```bash
cueman -ll job_name
```

#### Get Job Info (`-info`)

Display comprehensive job details:

```bash
cueman -info job_name
```

### Job Operations

#### Pause Jobs

```bash
cueman -pause job1,job2,job3
cueman -pause "show_*"  # Wildcard support
```

#### Resume Jobs

```bash
cueman -resume job1,job2
```

#### Terminate Jobs

```bash
cueman -term job1,job2
cueman -term job1,job2 -force  # Skip confirmation
```

#### Set Maximum Retries

```bash
cueman -retries job_name 5
```

#### Auto-Eat Management

```bash
cueman -autoeaton job1,job2   # Enable auto-eat
cueman -autoeatoff job1,job2  # Disable auto-eat
```

### Frame Operations

#### Kill Frames

Stop currently executing frames:

```bash
cueman -kill job_name                      # All running frames
cueman -kill job_name -range 1-50          # Specific range
cueman -kill job_name -layer render_layer  # Specific layer
cueman -kill job_name -memory gt16         # High memory frames
```

#### Retry Frames

Requeue frames for execution:

```bash
cueman -retry job_name                    # All frames
cueman -retry job_name -state DEAD        # Dead frames only
cueman -retry job_name -range 1-50        # Specific range
```

#### Eat Frames

Mark frames as succeeded without running:

```bash
cueman -eat job_name                      # All frames
cueman -eat job_name -state WAITING       # Waiting frames
cueman -eat job_name -layer preview       # Specific layer
```

#### Mark Done

Resolve dependencies without running:

```bash
cueman -done job_name -range 1-100
```

### Frame Manipulation

#### Stagger Frames

Add delays between frame starts:

```bash
cueman -stagger job_name 1-100 5  # Stagger by 5 frame increments
```

#### Reorder Frames

Change execution order:

```bash
cueman -reorder job_name 50-100 FIRST    # Move to front
cueman -reorder job_name 1-49 LAST       # Move to back
cueman -reorder job_name 1-100 REVERSE   # Reverse order
```

## Filtering Options

### State Filter

Filter by frame state:

```bash
# Available states: WAITING, RUNNING, SUCCEEDED, DEAD, EATEN, DEPEND
cueman -lf job_name -state RUNNING WAITING
cueman -kill job_name -state RUNNING
```

### Range Filter

Target specific frame numbers:

```bash
cueman -lf job_name -range 1-100           # Continuous range
cueman -lf job_name -range 1,3,5,7,9       # Individual frames
cueman -lf job_name -range 1-10,20,30-40   # Mixed ranges
```

### Layer Filter

Work with specific layers:

```bash
cueman -lf job_name -layer render_layer
cueman -lf job_name -layer render comp     # Multiple layers
```

### Memory Filter

Filter by memory usage (in GB):

```bash
cueman -lf job_name -memory 2-4    # Range: 2-4 GB
cueman -lf job_name -memory lt2    # Less than 2 GB
cueman -lf job_name -memory gt16   # Greater than 16 GB
```

### Duration Filter

Filter by runtime (in hours):

```bash
cueman -lf job_name -duration 1-2      # Range: 1-2 hours
cueman -lf job_name -duration gt3.5    # More than 3.5 hours
cueman -lf job_name -duration lt0.5    # Less than 0.5 hours
```

### Pagination

Handle large result sets:

```bash
cueman -lf job_name -page 2        # Second page (default 1000/page)
cueman -lf job_name -limit 500     # Custom page size
```

## Common Workflows

### Handling Stuck Frames

```bash
# Find frames running more than 12 hours
cueman -lf job_name -duration gt12

# Kill and retry them
cueman -kill job_name -duration gt12
cueman -retry job_name -state DEAD
```

### Memory Management

```bash
# Find high memory frames
cueman -lf job_name -memory gt16

# Kill frames using too much memory
cueman -kill job_name -memory gt32

# Retry with adjusted settings
cueman -retry job_name -state DEAD
```

### Batch Job Management

```bash
# Pause multiple jobs
cueman -pause "show_shot_*,show_comp_*"

# Terminate test jobs
cueman -term "test_*" -force

# Resume jobs in batches
cueman -resume "hero_*,client_*"
```

### Complex Frame Selection

```bash
# Retry specific frames on specific layers
cueman -retry job_name -layer render -range 1-50,100-150

# Kill high memory, long-running frames
cueman -kill job_name -memory gt16 -duration gt6
```

## Best Practices

1. **Preview Before Destructive Operations**
   ```bash
   # List what will be affected
   cueman -lf job_name -state RUNNING -duration gt6
   
   # Then execute if correct
   cueman -kill job_name -state RUNNING -duration gt6
   ```

2. **Use Specific Filters**
   - Avoid broad operations that might affect unintended frames
   - Combine filters for precise targeting
   - Test on small jobs before production use

3. **Batch Similar Operations**
   - Group related jobs for efficient management
   - Use wildcards and comma-separated lists
   - Plan maintenance windows for batch operations

4. **Monitor Before Acting**
   - Use `-info` to check job state
   - Review frame lists with `-lf` before operations
   - Enable verbose logging (`-v`) for debugging

## Troubleshooting

### Common Issues

**No command specified:**
```bash
# Error: No command specified
cueman job_name  # Missing command flag

# Correct usage
cueman -lf job_name
```

**Job doesn't exist:**
```bash
$ cueman -lf nonexistent_job
Error: Job 'nonexistent_job' does not exist.
```

**Connection errors:**
```bash
# Specify server explicitly
cueman -server cuebot.example.com:8443 -lf job_name

# Enable verbose for debugging
cueman -v -info job_name
```

### Getting Help

```bash
cueman -h          # Show all commands
cueman --help      # Same as -h
cueman             # Running without args shows help
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENCUE_CONFIG_FILE` | Path to OpenCue configuration file |
| `OPENCUE_HOSTS` | Comma-separated list of OpenCue servers |
| `OPENCUE_FACILITY` | Default facility code |

## Safety Guidelines

- Frame operations apply to ALL matching frames - use filters carefully
- The `-force` flag skips confirmation prompts - use with caution
- Preview operations with `-lf` before running destructive commands
- Memory values are in GB (e.g., `gt16` = greater than 16GB)
- Duration values are in hours (e.g., `gt12` = greater than 12 hours)

## Additional Resources

- [Cueman Tutorial](/docs/tutorials/cueman-tutorial/) - Tutorial with real-world scenarios
- [Cueman Reference](/docs/reference/commands/cueman/) - Related command-line tool
- [Cueman GitHub](https://github.com/AcademySoftwareFoundation/OpenCue/tree/master/cueman) - Source code and documentation
- [OpenCue Documentation](/docs/) - Complete OpenCue documentation
