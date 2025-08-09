---
title: "Managing Jobs and Frames"
layout: default
parent: Tutorials
nav_order: 50
linkTitle: "Managing Jobs and Frames"
date: 2025-01-29
description: >
  Learn advanced job management techniques including dependencies, priorities, and frame troubleshooting
---

# Managing Jobs and Frames

This tutorial covers advanced job and frame management techniques in OpenCue, including priority management, dependency handling, resource optimization, and troubleshooting strategies for production environments.

## What You'll Learn

- Advanced job priority and resource management
- Frame dependency strategies
- Troubleshooting failed frames
- Job optimization techniques
- Batch operations and automation
- Production workflow best practices

## Prerequisites

- Completed previous tutorials (Getting Started, Job Submission, CueGUI)
- Understanding of OpenCue job structure
- Access to OpenCue environment with multiple jobs

## Job Priority Management

### Understanding Priority Systems

OpenCue uses numerical priorities where higher numbers get precedence:

```
Priority Ranges:
├── 0-49    : Low priority (background jobs)
├── 50-99   : Normal priority (default)
├── 100-149 : High priority (urgent work)
└── 150+    : Critical priority (emergency fixes)
```

### Setting Job Priorities

#### During Job Submission

```python
# PyOutline script with priority
import outline

job = outline.Outline(
    name="urgent-render-v001",
    shot="shot010", 
    show="demo-project",
    user="artist01"
)

# Set high priority
job.set_priority(125)
```

#### After Job Submission

```bash
# Using CueAdmin
cueadmin -setpriority job-name 150

# Using CueGUI
# Right-click job → Properties → Set Priority
```

### Dynamic Priority Management

#### Automatic Priority Adjustment

```python
# Script to adjust priorities based on deadlines
import opencue
import time

def manage_priorities():
    jobs = opencue.api.getJobs()
    
    for job in jobs:
        if job.state() == opencue.compiled_proto.job_pb2.PENDING:
            # Increase priority for jobs waiting too long
            wait_time = time.time() - job.date_submitted()
            if wait_time > 3600:  # 1 hour
                new_priority = min(job.priority() + 10, 200)
                job.setPriority(new_priority)
                print(f"Increased priority for {job.name()} to {new_priority}")

# Run periodically
manage_priorities()
```

## Frame Dependency Management

### Layer Dependencies

#### Basic Dependencies

```python
import outline
import outline.modules.shell

job = outline.Outline("dependency-demo", shot="test", show="demo", user="student")

# Create layers
preprocess = outline.modules.shell.Shell("preprocess", command=["python", "prep.py"], range="1-10")
render = outline.modules.shell.Shell("render", command=["blender", "-f", "#IFRAME#"], range="1-10") 
composite = outline.modules.shell.Shell("composite", command=["nuke", "-f", "#IFRAME#"], range="1-10")

# Set up dependencies
render.depend_on(preprocess)      # Render waits for preprocess
composite.depend_on(render)       # Composite waits for render

job.add_layer(preprocess)
job.add_layer(render)
job.add_layer(composite)
```

#### Frame-by-Frame Dependencies

```python
# Each composite frame waits for corresponding render frame
composite.depend_on(render, opencue.DependType.FRAME_BY_FRAME)

# Composite waits for ALL render frames to complete
composite.depend_on(render, opencue.DependType.LAYER_ON_LAYER)
```

#### External Job Dependencies

```python
# Current job waits for another job to complete
job.depend_on_job("previous-job-name")

# Layer waits for layer in another job
current_layer.depend_on_job("other-job-name", "other-layer-name")
```

### Managing Dependencies in Production

#### Dependency Monitoring

```python
# Check dependency status
import opencue

def check_dependencies(job_name):
    job = opencue.api.findJob(job_name)
    
    for layer in job.getLayers():
        deps = layer.getWhatDependsOnThis()
        if deps:
            print(f"Layer {layer.name()} is blocking:")
            for dep in deps:
                print(f"  - {dep.dependentJob().name()}/{dep.dependentLayer().name()}")
```

#### Breaking Dependencies

```bash
# Remove dependency via CueAdmin
cueadmin -satisfy-dependency job-name layer-name

# In emergency situations
cueadmin -kill-dependency job-name layer-name
```

## Frame Troubleshooting Strategies

### Identifying Problem Patterns

#### Frame Failure Analysis

```python
# Analyze frame failure patterns
import opencue

def analyze_failures(job_name):
    job = opencue.api.findJob(job_name)
    
    failed_frames = []
    for layer in job.getLayers():
        for frame in layer.getFrames():
            if frame.state() == opencue.compiled_proto.job_pb2.DEAD:
                failed_frames.append({
                    'frame': frame.number(),
                    'layer': layer.name(),
                    'host': frame.lastResource(),
                    'exit_code': frame.exitStatus()
                })
    
    # Group by host to identify problem machines
    by_host = {}
    for frame in failed_frames:
        host = frame['host']
        if host not in by_host:
            by_host[host] = []
        by_host[host].append(frame)
    
    print("Failures by host:")
    for host, frames in by_host.items():
        print(f"  {host}: {len(frames)} failures")
```

### Common Failure Scenarios

#### Memory Issues

```python
# Detect memory-related failures
def check_memory_issues(job_name):
    job = opencue.api.findJob(job_name)
    
    for layer in job.getLayers():
        for frame in layer.getFrames():
            if frame.state() == opencue.compiled_proto.job_pb2.DEAD:
                if frame.exitStatus() == 9:  # SIGKILL often means OOM
                    print(f"Possible memory issue: Frame {frame.number()}")
                    print(f"  Memory used: {frame.usedMemory()} MB")
                    print(f"  Memory reserved: {frame.reservedMemory()} MB")
```

#### File System Issues

```bash
# Check for common file system problems
grep -i "permission denied\|no such file\|disk full" /path/to/frame/logs/*
```

#### Network Problems

```python
# Identify network-related failures
def check_network_issues(job_name):
    # Look for frames that fail on specific hosts
    # Check for timeout errors in logs
    # Monitor for connection refused errors
    pass
```

### Frame Recovery Strategies

#### Automatic Retry Logic

```python
# Custom retry strategy
import opencue
import time

def smart_retry(job_name, max_retries=3):
    job = opencue.api.findJob(job_name)
    
    for layer in job.getLayers():
        dead_frames = [f for f in layer.getFrames() 
                      if f.state() == opencue.compiled_proto.job_pb2.DEAD]
        
        for frame in dead_frames:
            if frame.retryCount() < max_retries:
                # Retry with different resource requirements
                if frame.exitStatus() == 9:  # Memory issue
                    # Increase memory requirement
                    layer.setMinMemory(layer.minimumMemory() * 1.5)
                
                frame.retry()
                print(f"Retrying frame {frame.number()}")
                time.sleep(1)  # Rate limiting
```

#### Selective Frame Management

```bash
# Retry specific frame ranges
cueadmin -retry-frames job-name layer-name 100-120

# Skip problematic frames
cueadmin -eat-frames job-name layer-name 115,118,119

# Kill and retry with different settings
cueadmin -kill-frames job-name layer-name 100-200
# Modify job resources then retry
```

## Resource Optimization

### Dynamic Resource Management

#### CPU Allocation Strategies

```python
# Adjust core allocation based on job type
import outline

def optimize_cores(layer, job_type):
    if job_type == "render":
        layer.set_min_cores(4)  # Minimum for good performance
        layer.set_max_cores(16)  # Don't monopolize hosts
    elif job_type == "simulation":
        layer.set_min_cores(8)   # CPU intensive
        layer.set_max_cores(32)  # Can use more cores effectively
    elif job_type == "composite":
        layer.set_min_cores(1)   # Usually single-threaded
        layer.set_max_cores(4)   # Limited benefit from more cores
```

#### Memory Management

```python
# Progressive memory allocation
def set_memory_requirements(layer, frame_complexity):
    base_memory = 2048  # 2GB base
    
    if frame_complexity == "simple":
        layer.set_min_memory(base_memory)
    elif frame_complexity == "complex":
        layer.set_min_memory(base_memory * 2)
    elif frame_complexity == "heavy":
        layer.set_min_memory(base_memory * 4)
        layer.set_max_cores(8)  # Limit cores to save memory for other jobs
```

### Service Tag Management

#### Service-Based Allocation

```python
# Target specific software versions
layer.set_service("maya2024")  # Specific Maya version
layer.set_service("gpu")       # GPU-enabled hosts
layer.set_service("highcpu")   # High CPU count hosts
layer.set_service("highmem")   # High memory hosts
```

#### Custom Service Tags

```bash
# Create custom host allocations
cueadmin -create-alloc facility workstation-pool workstation
cueadmin -tag-alloc workstation-pool "maya2024,highcpu"
```

## Batch Operations and Automation

### Bulk Job Management

#### Mass Job Operations

```python
# Kill all jobs from a specific user
import opencue

def kill_user_jobs(username):
    jobs = opencue.api.getJobs(user=[username])
    
    for job in jobs:
        if job.state() in [opencue.compiled_proto.job_pb2.PENDING, 
                          opencue.compiled_proto.job_pb2.RUNNING]:
            job.kill()
            print(f"Killed job: {job.name()}")
```

#### Batch Frame Operations

```python
# Retry all failed frames across multiple jobs
def retry_all_failures(show_name):
    jobs = opencue.api.getJobs(show=[show_name])
    
    for job in jobs:
        for layer in job.getLayers():
            dead_frames = [f for f in layer.getFrames() 
                          if f.state() == opencue.compiled_proto.job_pb2.DEAD]
            
            for frame in dead_frames:
                frame.retry()
                print(f"Retrying {job.name()}/{layer.name()}/frame{frame.number()}")
```

### Automated Monitoring Scripts

#### Job Health Monitor

```python
#!/usr/bin/env python3
# Production monitoring script

import opencue
import time
import smtplib
from email.mime.text import MIMEText

def monitor_job_health():
    """Monitor for stuck or problematic jobs"""
    
    jobs = opencue.api.getJobs()
    issues = []
    
    for job in jobs:
        # Check for jobs stuck in pending too long
        if job.state() == opencue.compiled_proto.job_pb2.PENDING:
            wait_time = time.time() - job.dateSubmitted()
            if wait_time > 1800:  # 30 minutes
                issues.append(f"Job {job.name()} stuck pending for {wait_time/60:.1f} minutes")
        
        # Check for high failure rate
        total_frames = len(job.getFrames())
        failed_frames = len([f for f in job.getFrames() 
                           if f.state() == opencue.compiled_proto.job_pb2.DEAD])
        
        if total_frames > 0 and failed_frames / total_frames > 0.5:
            issues.append(f"Job {job.name()} has {failed_frames}/{total_frames} failed frames")
    
    if issues:
        send_alert("\n".join(issues))

def send_alert(message):
    """Send email alert for issues"""
    # Implementation depends on your email setup
    pass

if __name__ == "__main__":
    monitor_job_health()
```

## Production Workflow Best Practices

### Job Lifecycle Management

#### Pre-Production Planning

```python
# Job template system
class JobTemplate:
    def __init__(self, job_type):
        self.job_type = job_type
        self.configure_defaults()
    
    def configure_defaults(self):
        if self.job_type == "animation_render":
            self.priority = 100
            self.min_cores = 4
            self.max_cores = 16
            self.min_memory = 4096
            self.service = "maya2024"
        elif self.job_type == "fx_simulation":
            self.priority = 120  # Higher priority
            self.min_cores = 16
            self.max_cores = 32
            self.min_memory = 16384
            self.service = "houdini"
    
    def create_job(self, name, shot, show, user):
        job = outline.Outline(name, shot=shot, show=show, user=user)
        job.set_priority(self.priority)
        return job
```

#### Production Phases

```python
# Different priorities for different production phases
PHASE_PRIORITIES = {
    "previs": 50,
    "animation": 75,
    "lighting": 100,
    "fx": 125,
    "final_comp": 150
}

def set_phase_priority(job_name, phase):
    job = opencue.api.findJob(job_name)
    job.setPriority(PHASE_PRIORITIES.get(phase, 50))
```

### Team Collaboration

#### Job Ownership and Handoffs

```python
# Transfer job ownership
def transfer_job(job_name, new_owner):
    job = opencue.api.findJob(job_name)
    job.setOwner(new_owner)
    
    # Add comment for tracking
    job.addComment(f"Job transferred to {new_owner}")
```

#### Status Communication

```python
# Automated status updates
def update_job_status(job_name, status_message):
    job = opencue.api.findJob(job_name)
    job.addComment(f"Status: {status_message}")
    
    # Could integrate with Slack, email, or other systems
    notify_team(job.name(), status_message)
```

### Performance Monitoring

#### Resource Utilization Tracking

```python
# Track resource efficiency
def analyze_resource_usage(job_name):
    job = opencue.api.findJob(job_name)
    
    total_core_hours = 0
    total_memory_hours = 0
    
    for layer in job.getLayers():
        for frame in layer.getFrames():
            if frame.state() == opencue.compiled_proto.job_pb2.SUCCEEDED:
                runtime_hours = frame.runTime() / 3600.0
                total_core_hours += frame.usedCores() * runtime_hours
                total_memory_hours += frame.usedMemory() * runtime_hours
    
    print(f"Job {job.name()} used:")
    print(f"  Core hours: {total_core_hours:.2f}")
    print(f"  Memory hours: {total_memory_hours:.2f} MB·h")
```

## Next Steps

You've mastered advanced job and frame management:
- Priority management and resource optimization
- Dependency handling and troubleshooting
- Frame failure analysis and recovery
- Batch operations and automation
- Production workflow best practices

**Continue your OpenCue journey**:
- [Creating Multi-Layer Jobs](/docs/tutorials/multi-layer-jobs/) - Complex pipeline workflows
- [DCC Integration Tutorial](/docs/tutorials/dcc-integration/) - Maya, Blender, Nuke integration
- Check out the [Reference](/docs/reference/) documentation for detailed API information

## Troubleshooting Reference

### Quick Diagnostic Commands

```bash
# Job status overview
cueadmin -lj | head -20

# Find stuck jobs
cueadmin -lj | grep PENDING

# Host resource check
cueadmin -lh | grep -v Up

# Recent failures
cueadmin -ll | grep ERROR | tail -10

# Resource usage
cueadmin -lp | awk '{sum+=$8} END {print "Total cores in use:", sum}'
```

### Emergency Procedures

```bash
# Kill all jobs for maintenance
cueadmin -lj | awk '{print $1}' | xargs -I {} cueadmin -kill {}

# Clear all pending jobs
cueadmin -lj | grep PENDING | awk '{print $1}' | xargs -I {} cueadmin -kill {}

# Restart stuck host
cueadmin -safe-reboot hostname
```