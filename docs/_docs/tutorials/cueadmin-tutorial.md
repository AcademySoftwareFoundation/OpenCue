---
title: "CueAdmin Tutorial"
nav_order: 69
parent: "Tutorials"
layout: default
date: 2025-08-11
description: >
  Learn how to use CueAdmin for OpenCue administration with 
  practical examples and real-world scenarios.
---

# CueAdmin Tutorial

This tutorial will guide you through using CueAdmin for OpenCue administration with practical examples and real-world scenarios.

## Prerequisites

Before starting this tutorial, ensure you have:
- Administrative access to an OpenCue server
- CueAdmin installed (`pip install opencue-cueadmin`)
- Environment variables configured:
  ```bash
  export OPENCUE_HOSTS="your-cuebot-server:8443"
  export OPENCUE_FACILITY="your-facility-code"
  ```

## Part 1: Basic Operations

### Getting Help

Start by exploring CueAdmin's capabilities:

```bash
# Display all available commands
cueadmin -h

# Enable verbose mode for detailed output
cueadmin -v -ls
```

### Querying System State

Let's begin with basic system inspection:

```bash
# List all shows
cueadmin -ls
```

Example output:
```
Show         Active  Default Min  Default Max  Dispatching  Booking
production   Yes     1.00         100.00       Yes          Yes
development  Yes     1.00         50.00        Yes          Yes
test         No      1.00         10.00        No           No
```

```bash
# List all allocations
cueadmin -la
```

Example output:
```
Allocation            Tag       Billable  Cores    Idle     Running  Down     Locked
main.production      desktop   Yes       1000     200      750      50       0
main.render         render    Yes       5000     1000     3500     500      0
main.development    dev       No        500      100      350      50       0
```

```bash
# List hosts with filters
cueadmin -lh -state UP | head -10
```

### Understanding Subscriptions

View how shows subscribe to allocations:

```bash
# List subscriptions for a show
cueadmin -lb production

# List all subscriptions to an allocation
cueadmin -lba main.render
```

## Part 2: Show Management

### Creating a New Show

Let's create and configure a new show:

```bash
# Step 1: Create the show
cueadmin -create-show tutorial_show
# Confirm: Create new show tutorial_show? [y/n] y

# Step 2: Configure core limits
cueadmin -default-min-cores tutorial_show 1
cueadmin -default-max-cores tutorial_show 50

# Step 3: Verify the show was created
cueadmin -ls | grep tutorial_show
```

### Managing Show State

Control show availability:

```bash
# Disable a show (prevents new jobs)
cueadmin -disable-show tutorial_show
# Confirm: Disable show tutorial_show? [y/n] y

# Check show status
cueadmin -ls | grep tutorial_show

# Re-enable the show
cueadmin -enable-show tutorial_show
# Confirm: Enable show tutorial_show? [y/n] y
```

### Controlling Dispatching and Booking

Fine-tune show behavior:

```bash
# Disable dispatching (stops sending frames to hosts)
cueadmin -dispatching tutorial_show OFF
# Confirm: Disable dispatching on show:tutorial_show? [y/n] y

# Disable booking (prevents new proc assignments)
cueadmin -booking tutorial_show OFF
# Confirm: Disable booking on show:tutorial_show? [y/n] y

# Re-enable both
cueadmin -dispatching tutorial_show ON
cueadmin -booking tutorial_show ON
```

### Archiving Shows

Archive inactive shows to consolidate resources:

```bash
# First, create a target show for archived content (e.g., training)
cueadmin -create-show training_show -force

# Set up minimal resources for the training show
cueadmin -create-sub training_show main.general 10 20 -force

# Archive a wrapped show to the training show
cueadmin -archive-show old_production training_show
# Confirm: Archive show old_production to training_show? [y/n] y

# Verify the archive
cueadmin -ls | grep old_production
# You should see old_production_archive in the list

# Now jobs submitted to "old_production" will run on training_show's allocations
```

**When to Use Archiving:**
- **Wrapped Shows**: Shows that have completed production but may need occasional reruns
- **Legacy Content**: Old shows that might be used for training or reference
- **Resource Consolidation**: Redirecting multiple old shows to a single training allocation

**What Happens:**
- Original show is renamed with `_archive` suffix
- An alias is created pointing to the target show
- Jobs submitted to the archived show run on the target show's allocations

## Part 3: Allocation Management

### Creating Allocations

Set up a new allocation:

```bash
# Create allocation with facility, name, and tag
cueadmin -create-alloc main tutorial desktop
# Confirm: Create new allocation main.tutorial, with tag desktop? [y/n] y

# Verify creation
cueadmin -la | grep tutorial
```

### Managing Allocation Tags

Update allocation properties:

```bash
# Change allocation tag
cueadmin -tag-alloc main.tutorial "workstation"
# Confirm: Re-tag allocation main.tutorial with workstation? [y/n] y

# Verify the change
cueadmin -la | grep tutorial
```

### Renaming Allocations

```bash
# Rename allocation (new name without facility prefix)
cueadmin -rename-alloc main.tutorial tutorial_renamed
# Confirm: Rename allocation from main.tutorial to tutorial_renamed? [y/n] y

# Verify
cueadmin -la | grep tutorial_renamed
```

## Part 4: Subscription Management

### Creating Subscriptions

Connect shows to allocations:

```bash
# Create subscription: show, allocation, size, burst
cueadmin -create-sub tutorial_show main.render 100 150
# Confirm: Create subscription for show:tutorial_show on alloc:main.render? [y/n] y

# Verify subscription
cueadmin -lb tutorial_show
```

### Adjusting Subscription Resources

Modify subscription limits:

```bash
# Increase guaranteed cores
cueadmin -size tutorial_show main.render 200

# Set burst as absolute value
cueadmin -burst tutorial_show main.render 300

# Set burst as percentage of size
cueadmin -burst tutorial_show main.render 50%
```

### Removing Subscriptions

```bash
# Delete subscription
cueadmin -delete-sub tutorial_show main.render
# Confirm: Delete tutorial_show's subscription to main.render? [y/n] y
```

## Part 5: Host Administration

### Viewing Host Information

```bash
# List all hosts
cueadmin -lh | head -10

# Filter by state
cueadmin -lh -state UP | tail -n +2 | wc -l      # Count UP hosts (excluding header)
cueadmin -lh -state DOWN            # List DOWN hosts
cueadmin -lh -state REPAIR          # List hosts needing repair

# Filter by allocation
cueadmin -lh -alloc main.render | head -10

# Filter by name pattern
cueadmin -lh render | grep render01
```

### Locking and Unlocking Hosts

Control host availability:

```bash
# Lock specific hosts
cueadmin -host render01 render02 -lock

# Lock hosts by pattern
cueadmin -hostmatch test_render -lock

# Verify locked state
cueadmin -lh test_render

# Unlock hosts
cueadmin -hostmatch test_render -unlock
```

### Moving Hosts Between Allocations

```bash
# Move single host
cueadmin -host render01 -move main.development
# Confirm: Move 1 hosts to main.development? [y/n] y

# Move multiple hosts by pattern
cueadmin -hostmatch old_farm -move main.legacy
# Confirm: Move 25 hosts to main.legacy? [y/n] y

# Verify the move
cueadmin -lh -alloc main.development | grep render01
```

### Managing Host Hardware State

```bash
# Mark host for repair
cueadmin -host broken_render01 -repair
# Confirm: Set 1 hosts into the Repair state? [y/n] y

# After repair, mark as fixed
cueadmin -host broken_render01 -fixed
# Confirm: Set 1 hosts into the Up state? [y/n] y
```

### Safe Reboot

Gracefully reboot hosts:

```bash
# Schedule safe reboot (waits for idle)
cueadmin -host render01 -safe-reboot
# Confirm: Lock and reboot 1 hosts when idle? [y/n] y

# Batch safe reboot
cueadmin -hostmatch rack_a -safe-reboot
# Confirm: Lock and reboot 20 hosts when idle? [y/n] y
```

## Part 6: Process Monitoring

### Viewing Running Processes

```bash
# List all processes
cueadmin -lp | head -20

# Filter by show
cueadmin -lp production | head -10

# Filter by host
cueadmin -lp -host render01

# Filter by memory usage
cueadmin -lp -memory gt16           # Processes using >16GB
cueadmin -lp -memory 8-16           # Processes using 8-16GB

# Filter by duration
cueadmin -lp -duration gt6          # Running >6 hours

# Combine filters
cueadmin -lp production -memory gt32 -duration gt12
```

### Getting Log Paths

```bash
# Get log paths for a show
cueadmin -ll production -limit 10

# Get logs for specific job
cueadmin -ll -job shot_001_lighting

# Get logs on specific host
cueadmin -ll -host render01
```

## Part 7: Job Management

### Listing Jobs

View jobs in your system:

```bash
# List all jobs
cueadmin -lj

# List jobs matching a pattern
cueadmin -lj shot_
cueadmin -lj lighting comp

# List detailed job information
cueadmin -lji
cueadmin -lji shot_001
```

### Pausing and Resuming Jobs

Control job execution:

```bash
# Pause a single job
cueadmin -pause shot_001_lighting

# Pause multiple jobs
cueadmin -pause shot_001_lighting shot_002_comp shot_003_fx

# Resume a job
cueadmin -unpause shot_001_lighting

# Resume multiple jobs
cueadmin -unpause shot_001_lighting shot_002_comp
```

### Killing Jobs

Terminate job execution:

```bash
# Kill a single job (with confirmation)
cueadmin -kill old_test_job
# Confirm: Kill 1 job(s)? [y/n] y

# Kill multiple jobs
cueadmin -kill test_job1 test_job2 test_job3
# Confirm: Kill 3 job(s)? [y/n] y

# Kill with force flag (skip confirmation)
cueadmin -kill old_test_job -force

# Kill all jobs (DANGER - requires force flag)
cueadmin -kill-all -force
```

### Retrying Failed Frames

Rerun dead frames:

```bash
# Retry dead frames for a single job
cueadmin -retry failed_render_job
# Confirm: Retry dead frames for 1 job(s)? [y/n] y

# Retry for multiple jobs
cueadmin -retry job1 job2 job3
# Confirm: Retry dead frames for 3 job(s)? [y/n] y

# Retry with force flag
cueadmin -retry failed_render_job -force

# Retry all jobs (DANGER - requires force flag)
cueadmin -retry-all -force
```

### Managing Job Dependencies

Remove blocking dependencies:

```bash
# Drop all dependencies for a job
cueadmin -drop-depends blocked_job
# Confirm: Drop all dependencies for 1 job(s)? [y/n] y

# Drop dependencies for multiple jobs
cueadmin -drop-depends job1 job2 job3
# Confirm: Drop all dependencies for 3 job(s)? [y/n] y

# Drop with force flag
cueadmin -drop-depends blocked_job -force
```

### Adjusting Job Resources

Configure job core requirements:

```bash
# Set minimum cores for a job
cueadmin -set-min-cores heavy_render 8.0
# Confirm: Set min cores for job:heavy_render to 8.00? [y/n] y

# Set maximum cores
cueadmin -set-max-cores heavy_render 64.0
# Confirm: Set max cores for job:heavy_render to 64.00? [y/n] y

# Set with force flag
cueadmin -set-min-cores heavy_render 8.0 -force
cueadmin -set-max-cores heavy_render 64.0 -force

# Fractional cores are supported
cueadmin -set-min-cores light_job 0.5 -force
cueadmin -set-max-cores light_job 4.0 -force
```

### Setting Job Priority

Adjust scheduling priority:

```bash
# Set job priority (higher = more important)
# Default priority is typically 100
cueadmin -priority urgent_shot 250
# Confirm: Set priority for job:urgent_shot to 250? [y/n] y

# Lower priority for background work
cueadmin -priority background_job 50 -force

# Negative priorities are allowed
cueadmin -priority low_priority_job -10 -force

# Set with force flag
cueadmin -priority urgent_shot 250 -force
```

### Job Management Workflow Example

Complete workflow for managing a problematic job:

```bash
# 1. Check job status
cueadmin -lji problematic_job

# 2. Pause the job to investigate
cueadmin -pause problematic_job

# 3. Drop dependencies if blocked
cueadmin -drop-depends problematic_job -force

# 4. Adjust resources to reduce errors
cueadmin -set-min-cores problematic_job 4.0 -force
cueadmin -set-max-cores problematic_job 32.0 -force

# 5. Retry failed frames
cueadmin -retry problematic_job -force

# 6. Resume the job
cueadmin -unpause problematic_job

# 7. Boost priority if urgent
cueadmin -priority problematic_job 200 -force

# 8. Monitor progress
cueadmin -lji problematic_job
```

## Part 8: Advanced Workflows

### Setting Up Production Infrastructure

Complete workflow for production setup:

```bash
# 1. Create production show
cueadmin -create-show production_2025

# 2. Configure show parameters
cueadmin -default-min-cores production_2025 2
cueadmin -default-max-cores production_2025 200

# 3. Create dedicated allocation
cueadmin -create-alloc main prod2025 "production"

# 4. Move hosts to new allocation
cueadmin -hostmatch prod2025 -move main.prod2025

# 5. Create subscriptions
cueadmin -create-sub production_2025 main.prod2025 500 750
cueadmin -create-sub production_2025 main.render 200 400

# 6. Enable the show
cueadmin -enable-show production_2025

# 7. Verify setup
cueadmin -ls | grep production_2025
cueadmin -lb production_2025
cueadmin -lh -alloc main.prod2025 | tail -n +2 | wc -l
```

### Emergency Response Procedure

Handle production issues:

```bash
# 1. Check current state
cueadmin -ls | grep production
cueadmin -lp production -memory gt32 -duration gt6

# 2. Pause problematic show
cueadmin -dispatching production OFF
cueadmin -booking production OFF

# 3. Identify problem hosts
cueadmin -lp -memory gt64 | awk '{print $2}' | sort -u > problem_hosts.txt

# 4. Lock problem hosts
for host in $(cat problem_hosts.txt); do
    cueadmin -host $host -lock
done

# 5. Move to quarantine
cueadmin -create-alloc main quarantine "problematic"
for host in $(cat problem_hosts.txt); do
    cueadmin -host $host -move main.quarantine
done

# 6. Resume production
cueadmin -dispatching production ON
cueadmin -booking production ON

# 7. Monitor recovery
watch -n 10 'cueadmin -lp production | head -20'
```

### Facility Migration

Move resources between facilities:

```bash
# 1. Create new facility allocation
cueadmin -create-alloc new_facility render "gpu"

# 2. List source hosts
cueadmin -lh -alloc old_facility.render > migration_hosts.txt

# 3. Lock source hosts
cueadmin -hostmatch old_facility -lock

# 4. Transfer hosts
cueadmin -transfer old_facility.render new_facility.render
# Confirm: Transfer hosts from from old_facility.render to new_facility.render? [y/n] y

# 5. Update subscriptions
for show in $(cueadmin -lba old_facility.render | awk '{print $1}'); do
    echo "Migrating subscription for $show"
    cueadmin -delete-sub $show old_facility.render
    cueadmin -create-sub $show new_facility.render 100 150
done

# 6. Verify migration
cueadmin -lh -alloc new_facility.render | tail -n +2 | wc -l
cueadmin -lba new_facility.render

# 7. Clean up old allocation
cueadmin -delete-alloc old_facility.render
```

## Part 9: Monitoring and Maintenance

### Daily Health Checks

```bash
#!/bin/bash
# Daily health check script

echo "=== OpenCue Daily Health Check ==="
echo "Date: $(date)"
echo

echo "=== Show Status ==="
cueadmin -ls

echo -e "\n=== Allocation Summary ==="
cueadmin -la

echo -e "\n=== Host Status Summary ==="
echo "UP hosts: $(cueadmin -lh -state UP | tail -n +2 | wc -l)"
echo "DOWN hosts: $(cueadmin -lh -state DOWN | tail -n +2 | wc -l)"
echo "REPAIR hosts: $(cueadmin -lh -state REPAIR | tail -n +2 | wc -l)"

echo -e "\n=== Long Running Processes ==="
cueadmin -lp -duration gt12 -limit 10

echo -e "\n=== High Memory Processes ==="
cueadmin -lp -memory gt32 -limit 10
```

### Resource Optimization

```bash
# Find underutilized allocations
for alloc in $(cueadmin -la | tail -n +2 | awk '{print $1}'); do
    idle=$(cueadmin -la | grep $alloc | awk '{print $5}')
    total=$(cueadmin -la | grep $alloc | awk '{print $4}')
    if [ "$total" -gt 0 ]; then
        util=$(echo "scale=2; (($total - $idle) / $total) * 100" | bc)
        echo "$alloc: ${util}% utilized"
    fi
done

# Rebalance subscriptions based on usage
# (Would require additional scripting to implement fully)
```

## Part 10: Rollback and Recovery

### Safe Rollback Procedure

Always prepare for rollback:

```bash
# Before making changes, document current state
cueadmin -ls > shows_backup_$(date +%Y%m%d).txt
cueadmin -la > allocations_backup_$(date +%Y%m%d).txt
cueadmin -lh > hosts_backup_$(date +%Y%m%d).txt

# Make your changes
cueadmin -create-show test_show
cueadmin -create-sub test_show main.render 100 150

# If rollback needed
cueadmin -delete-sub test_show main.render -force
cueadmin -delete-show test_show -force

# Verify rollback
diff shows_backup_$(date +%Y%m%d).txt <(cueadmin -ls)
```

## Part 11: Best Practices

### Command Patterns

```bash
# Always verify before destructive operations
cueadmin -lh -hostmatch pattern    # Check what will be affected
cueadmin -hostmatch pattern -lock  # Then execute

# Use verbose mode for troubleshooting
cueadmin -v -create-sub show allocation size burst

# Batch operations efficiently
# Good: Single command
cueadmin -hostmatch render -lock

# Avoid: Multiple commands
for i in {1..100}; do
    cueadmin -host render$i -lock
done
```

### Safety Checklist

Before any major operation:

1. **Check current state**
   ```bash
   cueadmin -ls              # Shows
   cueadmin -la              # Allocations
   cueadmin -lh | tail -n +2 | wc -l      # Host count (excluding header)
   ```

2. **Document the change**
   ```bash
   echo "$(date): About to create show X" >> admin_log.txt
   ```

3. **Test on small scale**
   ```bash
   # Test pattern on one host first
   cueadmin -host test_render01 -lock
   # Then apply to all
   cueadmin -hostmatch test_render -lock
   ```

4. **Monitor after change**
   ```bash
   watch -n 5 'cueadmin -lp | head -20'
   ```

## Troubleshooting

### Common Issues and Solutions

**Connection refused:**
```bash
# Check server is specified correctly
cueadmin -server cuebot.example.com:8443 -ls

# Verify environment variables
echo $OPENCUE_HOSTS
echo $OPENCUE_FACILITY
```

**Permission denied:**
```bash
# Most operations require admin privileges
# Check with your OpenCue administrator
```

**No hosts found:**
```bash
# Check pattern matching
cueadmin -lh | grep your_pattern    # Test pattern
cueadmin -hostmatch your_pattern -lh # Use in command
```

**Allocation not empty:**
```bash
# Cannot delete non-empty allocation
cueadmin -lh -alloc main.old_alloc  # List hosts
# Move or delete hosts first
cueadmin -transfer main.old_alloc main.other_alloc
```

### Getting Help

```bash
# Built-in help
cueadmin -h

# Check command syntax
cueadmin -h | grep -A2 "create-sub"

# Enable verbose for debugging
cueadmin -v -your-command
```

## Summary

You've learned how to:
- Query and monitor OpenCue resources
- Manage jobs (pause, kill, retry, adjust resources, set priorities)
- Create and manage shows
- Configure allocations and subscriptions
- Administer hosts
- Monitor processes
- Handle emergency situations
- Perform migrations and maintenance

Remember to always:
- Test commands on small sets first
- Use confirmation prompts (avoid `-force` in production)
- Document your changes
- Monitor the system after changes

## Next Steps

- Explore the [CueAdmin Reference](/docs/reference/tools/cueadmin/) for complete command documentation
- Practice with test shows and allocations before working on production
- Learn about [CueAdmin development and testing](/docs/reference/tools/cueadmin/#development-and-testing) if you want to contribute
- Continue to the [Developer Guide](/docs/developer-guide/) to learn about contributing to OpenCue

## Development and Contributing

CueAdmin is actively developed with:
- **Comprehensive test suite** with tests covering job management, allocation management, host operations, subscriptions, and integration workflows
- **Modern testing infrastructure** using pytest, coverage reporting, and CI/CD integration
- **Development tools** including linting, formatting, and multi-Python version testing

To contribute or run tests locally:

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run the test suite
pytest --cov=cueadmin --cov-report=term-missing

# Format and lint code
black cueadmin tests && isort cueadmin tests
pylint cueadmin tests
```
