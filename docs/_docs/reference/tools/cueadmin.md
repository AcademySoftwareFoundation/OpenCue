---
title: "CueAdmin - CLI Administration Tool"
nav_order: 45
parent: "Command Line Tools"
grand_parent: "Reference"
layout: default
date: 2025-08-11
description: >
  CueAdmin is a command-line administration tool for OpenCue that provides 
  comprehensive control over shows, allocations, hosts, and system resources.
---

# CueAdmin - CLI Administration Tool

CueAdmin is the command-line interface for administering OpenCue deployments. It provides control over shows, allocations, hosts, subscriptions, and system resources through an intuitive command-line interface.

## Overview

CueAdmin is the administrative counterpart to Cueman, focusing on system-level operations and infrastructure management rather than job control. It's the essential tool for OpenCue administrators and power users who need to manage render farm resources.

### Key Features

- **Show Management**: Create, configure, and control shows
- **Allocation Control**: Manage resource allocations and facility resources
- **Host Administration**: Lock, unlock, move, and configure render hosts
- **Subscription Management**: Configure show subscriptions to allocations
- **Resource Monitoring**: Query procs, hosts, and system state
- **Batch Operations**: Apply changes to multiple entities simultaneously
- **Safety Features**: Confirmation prompts for destructive operations

## Installation

### Prerequisites

- OpenCue server running and accessible
- Python 3.7 or higher
- OpenCue Python packages installed

### Install from PyPI

```bash
pip install opencue-cueadmin
```

### Install from Source

```bash
cd OpenCue/cueadmin
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
   cueadmin -h  # Shows help message
   ```

2. **List shows:**
   ```bash
   cueadmin -ls
   ```

3. **List allocations:**
   ```bash
   cueadmin -la
   ```

4. **List hosts:**
   ```bash
   cueadmin -lh
   ```

## Command Reference

### Global Options

| Option | Description | Example |
|--------|-------------|---------|
| `-h, --help` | Show help message and exit | `cueadmin -h` |
| `-v, -verbose` | Enable verbose logging | `cueadmin -v -ls` |
| `-server HOSTNAME` | Specify cuebot address(es) | `cueadmin -server cuebot1:8443` |
| `-facility CODE` | Specify facility code | `cueadmin -facility main` |
| `-force` | Skip confirmation prompts | `cueadmin -force -delete-show test` |

### Query Commands

#### List Jobs (`-lj`, `-laj`)

Display jobs with optional name filtering:

```bash
cueadmin -lj                  # List all jobs
cueadmin -lj shot_             # List jobs matching "shot_"
cueadmin -lj render comp       # Multiple patterns
```

#### List Job Info (`-lji`)

Display detailed job information:

```bash
cueadmin -lji                  # All jobs with details
cueadmin -lji shot_lighting    # Specific job pattern
```

#### List Shows (`-ls`)

Display all configured shows:

```bash
cueadmin -ls
```

Example output:
```
Show         Active  Default Min  Default Max  Dispatching  Booking
production   Yes     1.00         100.00       Yes          Yes
development  Yes     1.00         50.00        Yes          Yes
test         No      1.00         10.00        No           No
```

#### List Allocations (`-la`)

Display resource allocations:

```bash
cueadmin -la
```

Example output:
```
Allocation            Tag       Billable  Cores    Idle     Running  Down     Locked
main.production       desktop   Yes       1000     200      750      50       0
main.render          render    Yes       5000     1000     3500     500      0
main.development     dev       No        500      100      350      50       0
```

#### List Hosts (`-lh`)

Display hosts with filtering options:

```bash
cueadmin -lh                        # All hosts
cueadmin -lh render                 # Hosts matching "render"
cueadmin -lh -state UP              # Only UP hosts
cueadmin -lh -state DOWN REPAIR     # DOWN or REPAIR hosts
cueadmin -lh -alloc main.render     # Hosts in specific allocation
```

#### List Subscriptions (`-lb`)

Display show subscriptions:

```bash
cueadmin -lb production             # Subscriptions for production show
cueadmin -lb production development # Multiple shows
```

#### List All Subscriptions (`-lba`)

Display all subscriptions to an allocation:

```bash
cueadmin -lba main.render
```

#### List Processes (`-lp`, `-lap`)

Monitor running processes:

```bash
cueadmin -lp                        # All processes
cueadmin -lp production             # Processes for show
cueadmin -lp -host render01         # Processes on specific host
cueadmin -lp -memory gt16           # High memory processes
cueadmin -lp -limit 100             # Limit results
```

#### List Log Paths (`-ll`, `-lal`)

Display frame log paths:

```bash
cueadmin -ll production             # Logs for show
cueadmin -ll -job shot_001          # Logs for specific job
cueadmin -ll -host render01         # Logs on specific host
```

#### List Services (`-lv`)

Display default services or show overrides:

```bash
cueadmin -lv                        # Default services
cueadmin -lv production             # Show-specific services
```

### Show Operations

#### Create Show

```bash
cueadmin -create-show new_show
cueadmin -create-show new_show -force  # Skip confirmation
```

#### Delete Show

```bash
cueadmin -delete-show old_show
cueadmin -delete-show old_show -force
```

#### Enable/Disable Show

```bash
cueadmin -enable-show production
cueadmin -disable-show maintenance
```

#### Configure Dispatching

Control frame dispatching:

```bash
cueadmin -dispatching production ON    # Enable dispatching
cueadmin -dispatching production OFF   # Disable dispatching
```

#### Configure Booking

Control new proc assignment:

```bash
cueadmin -booking production ON        # Enable booking
cueadmin -booking production OFF       # Disable booking
```

#### Set Core Limits

Configure default core requirements:

```bash
cueadmin -default-min-cores production 2     # Minimum 2 cores
cueadmin -default-max-cores production 100   # Maximum 100 cores
```

### Allocation Operations

#### Create Allocation

```bash
cueadmin -create-alloc main render desktop
# Creates: main.render with tag "desktop"
```

#### Delete Allocation

```bash
cueadmin -delete-alloc main.old_render
# Note: Allocation must be empty
```

#### Rename Allocation

```bash
cueadmin -rename-alloc main.old_name new_name
# Note: New name should not include facility prefix
```

#### Transfer Hosts

Move all hosts between allocations:

```bash
cueadmin -transfer main.source main.destination
```

#### Tag Allocation

Update allocation tag:

```bash
cueadmin -tag-alloc main.render "high_priority"
```

### Host Operations

#### Select Hosts

Two methods for host selection:

```bash
# By exact names
cueadmin -host render01 render02 render03 -lock

# By pattern matching
cueadmin -hostmatch render -lock  # All hosts containing "render"
```

#### Lock/Unlock Hosts

```bash
cueadmin -host render01 render02 -lock      # Lock specific hosts
cueadmin -hostmatch test -unlock            # Unlock all test hosts
```

#### Move Hosts

Change host allocation:

```bash
cueadmin -host render01 -move main.production
cueadmin -hostmatch old_farm -move main.legacy
```

#### Delete Hosts

Remove hosts from system:

```bash
cueadmin -host old_render01 -delete-host
cueadmin -hostmatch decommissioned -delete-host -force
```

#### Safe Reboot

Lock and reboot when idle:

```bash
cueadmin -host render01 -safe-reboot
cueadmin -hostmatch rack_a -safe-reboot
```

#### Hardware State

Set repair or fixed state:

```bash
cueadmin -host broken01 -repair     # Mark as needing repair
cueadmin -host fixed01 -fixed       # Mark as fixed/UP
```

#### Thread Mode

Configure threading behavior:

```bash
cueadmin -host render01 -thread auto      # Automatic threading
cueadmin -host render01 -thread all       # Use all cores
cueadmin -host render01 -thread variable  # Variable threading
```

### Subscription Operations

#### Create Subscription

```bash
cueadmin -create-sub production main.render 100 150
# Show: production
# Allocation: main.render
# Size: 100 cores guaranteed
# Burst: 150 cores maximum
```

#### Delete Subscription

```bash
cueadmin -delete-sub production main.render
```

#### Adjust Size

Set guaranteed cores:

```bash
cueadmin -size production main.render 200
```

#### Adjust Burst

Set burst capacity:

```bash
cueadmin -burst production main.render 300    # Absolute value
cueadmin -burst production main.render 50%    # Percentage of size
```

## Filtering Options

### Memory Filter

Filter processes by memory usage (in GB):

```bash
cueadmin -lp -memory 8-16          # Range: 8-16 GB
cueadmin -lp -memory lt4           # Less than 4 GB
cueadmin -lp -memory gt32          # Greater than 32 GB
```

### Duration Filter

Filter processes by runtime (in hours):

```bash
cueadmin -lp -duration 1-2         # Range: 1-2 hours
cueadmin -lp -duration gt6         # More than 6 hours
cueadmin -lp -duration lt0.5       # Less than 30 minutes
```

### State Filter

Filter hosts by hardware state:

```bash
cueadmin -lh -state UP              # Only UP hosts
cueadmin -lh -state DOWN            # Only DOWN hosts
cueadmin -lh -state REPAIR          # Hosts needing repair
```

### Allocation Filter

Filter by allocation:

```bash
cueadmin -lh -alloc main.render     # Hosts in allocation
cueadmin -lp -alloc main.render     # Processes in allocation
```

### Job Filter

Filter processes or logs by job:

```bash
cueadmin -lp -job shot_001_lighting
cueadmin -ll -job shot_001_comp
```

### Result Limits

Limit query results:

```bash
cueadmin -lp -limit 100             # First 100 processes
cueadmin -ll -limit 50              # First 50 log paths
```

## Common Workflows

### Setting Up a New Show

```bash
# 1. Create the show
cueadmin -create-show new_production

# 2. Configure core limits
cueadmin -default-min-cores new_production 1
cueadmin -default-max-cores new_production 100

# 3. Create subscriptions to allocations
cueadmin -create-sub new_production main.render 500 750
cueadmin -create-sub new_production main.workstation 100 150

# 4. Enable the show
cueadmin -enable-show new_production
```

### Managing Resource Allocation

```bash
# 1. Check current allocations
cueadmin -la

# 2. Check subscription details
cueadmin -lb production

# 3. Adjust subscription sizes
cueadmin -size production main.render 600
cueadmin -burst production main.render 900

# 4. Monitor resource usage
cueadmin -lp production -limit 50
```

### Host Maintenance

```bash
# 1. Identify hosts needing maintenance
cueadmin -lh -state DOWN

# 2. Lock hosts for maintenance
cueadmin -hostmatch rack_a -lock

# 3. Set repair state
cueadmin -hostmatch rack_a -repair

# 4. After maintenance, mark as fixed
cueadmin -hostmatch rack_a -fixed

# 5. Unlock hosts
cueadmin -hostmatch rack_a -unlock
```

### Emergency Response

```bash
# 1. Disable show dispatching during issue
cueadmin -dispatching production OFF

# 2. Check running processes
cueadmin -lp production -memory gt32

# 3. Move problematic hosts
cueadmin -hostmatch problem -move main.quarantine

# 4. Re-enable dispatching
cueadmin -dispatching production ON
```

### Facility Migration

```bash
# 1. Create new allocation
cueadmin -create-alloc new_facility render gpu

# 2. Transfer hosts to new allocation
cueadmin -transfer old_facility.render new_facility.render

# 3. Update subscriptions
cueadmin -delete-sub production old_facility.render
cueadmin -create-sub production new_facility.render 1000 1500

# 4. Clean up old allocation
cueadmin -delete-alloc old_facility.render
```

## Best Practices

1. **Always Preview Operations**
   ```bash
   # Check current state before changes
   cueadmin -lh -alloc main.render    # Before moving hosts
   cueadmin -lb production          # Before modifying subscriptions
   ```

2. **Use Confirmation Prompts**
   - Avoid `-force` flag for production operations
   - Review confirmation messages carefully
   - Document reasons for forced operations

3. **Batch Similar Operations**
   ```bash
   # Good: Single command for multiple hosts
   cueadmin -hostmatch render -lock
   
   # Avoid: Multiple individual commands
   cueadmin -host render01 -lock
   cueadmin -host render02 -lock
   ```

4. **Monitor After Changes**
   ```bash
   # After allocation changes
   cueadmin -la
   cueadmin -lh -alloc main.new_alloc
   
   # After show changes
   cueadmin -ls
   cueadmin -lb show_name
   ```

5. **Use Verbose Mode for Debugging**
   ```bash
   cueadmin -v -create-sub production main.render 100 150
   ```

## Safety Guidelines

### Production-Impacting Commands

These commands can significantly affect production:

- **Show Operations**: `-delete-show`, `-disable-show`, `-dispatching OFF`, `-booking OFF`
- **Allocation Operations**: `-delete-alloc`, `-transfer`
- **Host Operations**: `-delete-host`, `-lock`, `-move`
- **Subscription Operations**: `-delete-sub`, `-size` (reducing)

### Safe Commands

These commands are read-only and safe to run:

- All list commands (`-ls`, `-la`, `-lh`, `-lj`, `-lb`, `-lp`, `-ll`, `-lv`)
- All query operations with filters
- Help command (`-h`)

### Confirmation Best Practices

1. **Always confirm host counts**:
   ```bash
   # Check how many hosts will be affected
   cueadmin -hostmatch pattern -lh | wc -l
   ```

2. **Verify show state before deletion**:
   ```bash
   cueadmin -ls  # Ensure show is disabled
   cueadmin -lj | grep show_name  # Check for running jobs
   ```

3. **Test patterns on small sets**:
   ```bash
   cueadmin -hostmatch test_pattern -lh  # Verify pattern matches
   ```

## Troubleshooting

### Common Issues

**Connection errors:**
```bash
# Specify server explicitly
cueadmin -server cuebot.example.com:8443 -ls

# Enable verbose for debugging
cueadmin -v -ls
```

**Permission denied:**
```bash
# Most administrative operations require elevated permissions
# Contact your OpenCue administrator for access
```

**No results returned:**
```bash
# Check filters are correct
cueadmin -v -lh -state UP  # Verbose will show query details

# Verify facility setting
cueadmin -facility main -ls
```

**Operation failed:**
```bash
# Check prerequisites
cueadmin -la  # Verify allocation exists
cueadmin -ls  # Verify show exists
```

### Getting Help

```bash
cueadmin -h          # Show all commands
cueadmin --help      # Same as -h
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENCUE_CONFIG_FILE` | Path to OpenCue configuration file | `/etc/opencue/config.yaml` |
| `OPENCUE_HOSTS` | Comma-separated list of OpenCue servers | `cuebot1:8443,cuebot2:8443` |
| `OPENCUE_FACILITY` | Default facility code | `main` |

## Return Codes

CueAdmin returns the following exit codes:

- `0`: Success
- `1`: General error or operation failed
- `2`: Invalid arguments or command syntax

## Additional Resources

- [CueAdmin Tutorial](/docs/tutorials/cueadmin-tutorial/) - Step-by-step tutorial with practical examples
- [CueAdmin Reference](/docs/reference/tools/cueadmin/) - Related command-line tool
- [CueAdmin GitHub](https://github.com/AcademySoftwareFoundation/OpenCue/tree/master/cueadmin) - Source code
- [OpenCue Documentation](/docs/) - Complete OpenCue documentation
