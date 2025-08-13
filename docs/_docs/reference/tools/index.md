---
title: "Command Line Tools"
nav_order: 44
parent: "Reference"
has_children: true
layout: default
date: 2025-08-06
description: >
  Reference documentation for OpenCue command-line tools including 
  cueadmin, cueman, and other CLI utilities.
---

# Command Line Tools

OpenCue provides several command-line tools for managing and interacting with the render farm. These tools offer capabilities for job management, system administration, and automation.

## Available Tools

### [CueAdmin](/docs/reference/tools/cueadmin/)
The primary administrative tool for OpenCue, providing comprehensive control over shows, allocations, hosts, subscriptions, and system resources.

### [Cueman](/docs/reference/tools/cueman/)
A job management tool that extends cueadmin with advanced filtering, batch operations, and user-friendly features for efficient farm management.

### [PyCueRun](/docs/reference/commands/pycuerun/)
A tool for submitting and running Python-based jobs on the OpenCue render farm.

## Quick Comparison

| Tool | Primary Use | Key Features |
|------|------------|--------------|
| **cueadmin** | System administration | Host management, show configuration, allocation control |
| **cueman** | Job and frame management | Advanced filtering, batch operations, frame manipulation |
| **pycuerun** | Job submission | Python script execution, dependency management |

## Getting Started

All command-line tools require:
1. OpenCue Python packages installed
2. Environment variables configured:
   ```bash
   export OPENCUE_HOSTS="your-cuebot-server:8443"
   export OPENCUE_FACILITY="your-facility-code"
   ```

## Common Operations

### View Help
All tools support help flags:
```bash
cueadmin -h
cueman -h
pycuerun -h
```

### List Jobs
```bash
cueadmin -lj              # Using cueadmin
cueman -info job_name     # Using cueman for details
```

### Manage Frames
```bash
cueman -lf job_name       # List frames
cueman -retry job_name    # Retry failed frames
cueman -kill job_name     # Kill running frames
```

## Best Practices

1. **Start with Read Operations**: Use list and info commands to understand current state
2. **Use Filters**: Apply specific filters to target exact resources
3. **Test First**: Try commands on test jobs before production
4. **Enable Verbose Mode**: Use `-v` flag for debugging
5. **Document Actions**: Keep logs of administrative actions

## Environment Setup

Configure your shell environment for optimal use:

```bash
# Add to ~/.bashrc or ~/.zshrc
export OPENCUE_HOSTS="cuebot1:8443,cuebot2:8443"
export OPENCUE_FACILITY="main"

# Optional: Create aliases for common operations
alias cue-jobs='cueadmin -lj'
alias cue-hosts='cueadmin -lh'
alias cue-info='cueman -info'
```

## Scripting and Automation

Command-line tools can be combined in scripts:

```bash
#!/bin/bash
# Example: Daily maintenance script

# Clean up overnight test jobs
for job in $(cueadmin -lj | grep test_ | awk '{print $1}'); do
    cueman -term $job -force
done

# Retry failed production frames
for job in $(cueadmin -lj | grep prod_ | awk '{print $1}'); do
    cueman -retry $job -state DEAD
done
```

## Troubleshooting

### Connection Issues
```bash
# Test connection by listing shows (if successful, connection works)
cueadmin -ls

# Specify server explicitly
cueman -server cuebot.example.com:8443 -lf job_name
```

### Permission Errors
Some operations require administrative privileges. Contact your OpenCue administrator if you encounter permission errors.

## Additional Resources

- [OpenCue Python API Documentation](https://github.com/AcademySoftwareFoundation/OpenCue/tree/master/pycue)
- [OpenCue User Guides](/docs/user-guides/)
- [OpenCue Tutorials](/docs/tutorials/)