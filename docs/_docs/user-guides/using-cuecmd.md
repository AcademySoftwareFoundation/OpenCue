---
title: "Cuecmd User Guide"
nav_order: 34
parent: "User Guides"
layout: default
date: 2025-10-02
description: >
  User guide for executing batch shell commands on the OpenCue render farm
  using cuecmd, including common workflows and best practices.
---

# Using Cuecmd for Batch Commands

This guide covers common workflows and best practices for using cuecmd to execute batch shell commands on the OpenCue render farm.

## Table of Contents

1. [Introduction](#introduction)
2. [Basic Workflow](#basic-workflow)
3. [Command File Formats](#command-file-formats)
4. [Resource Management](#resource-management)
5. [Job Control](#job-control)
6. [Common Workflows](#common-workflows)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Introduction

Cuecmd enables you to execute arbitrary shell commands on the render farm by:
- Reading commands from a text file
- Distributing them across multiple frames
- Running them in parallel on available hosts
- Tracking execution and results

**When to use cuecmd:**
- Batch file processing
- Data transformations
- Archive operations
- Testing and validation
- Parameter sweeps
- Any parallelizable shell commands

**When to use other tools:**
- Complex render jobs -> Use CueSubmit or PyOutline
- Interactive tasks -> Run locally
- Real-time processing -> Use streaming tools

## Basic Workflow

### Step 1: Create Command File

Create a text file with commands (one per line):

```bash
cat > process_files.txt << 'EOF'
python process.py input1.dat
python process.py input2.dat
python process.py input3.dat
EOF
```

### Step 2: Submit to OpenCue

```bash
cuecmd process_files.txt
```

### Step 3: Monitor Execution

```bash
# List your jobs
cueadmin -lj | grep $USER

# Get detailed info
cueman -info <job_name>

# Watch frame progress
cueman -lf <job_name>
```

### Step 4: Review Results

```bash
# Check for failures
cueman -lf <job_name> -state DEAD

# View frame logs
# Logs are in: /var/tmp/cue/<job>/<frame>/
```

## Command File Formats

### Simple Commands

```bash
# One command per line
echo "Hello World"
ls -la /tmp
date
hostname
```

### Commands with Arguments

```bash
# Use quotes for arguments with spaces
convert "input file.jpg" -resize 50% "output file.jpg"

# Escape special characters
echo "Path: \$HOME/data"
```

### Environment Variables

```bash
# Reference environment variables
python process.py --output $OUTPUT_DIR/result.txt

# Set variables inline
OUTPUT=/tmp/result.dat python process.py
```

### Conditional Logic

```bash
# Shell logic within commands
test -f input.txt && python process.py input.txt

# Chain commands
mkdir -p output && python process.py > output/result.txt
```

### Generated Command Files

#### From File Lists

```bash
# Process all files in directory
find /data -name "*.dat" | while read f; do
  echo "python process.py '$f'"
done > commands.txt
```

#### From Database

```bash
# Export from database
mysql -e "SELECT cmd FROM job_queue WHERE status='pending'" | \
  tail -n +2 > commands.txt
```

#### From Scripts

```python
# Python script to generate commands
with open('commands.txt', 'w') as f:
    for i in range(1, 1001):
        f.write(f"process --id {i} --output /tmp/result_{i}.txt\n")
```

## Resource Management

### Cores Allocation

```bash
# Single core (default)
cuecmd commands.txt

# Multiple cores for parallel processing within command
cuecmd commands.txt --cores 4

# Fractional cores for light tasks
cuecmd commands.txt --cores 0.5
```

**Cores are per-frame**, so all commands in a chunk share the cores.

### Memory Allocation

```bash
# 1GB memory (default)
cuecmd commands.txt

# High memory tasks
cuecmd commands.txt --memory 16

# Memory-intensive processing
cuecmd commands.txt --memory 32
```

**Memory is specified in GB** and allocated per-frame.

### Chunking Strategy

Chunk size determines commands per frame:

```bash
# No chunking: 100 commands = 100 frames
cuecmd commands.txt

# Chunk 10: 100 commands = 10 frames
cuecmd commands.txt --chunk 10

# Chunk 50: 100 commands = 2 frames
cuecmd commands.txt --chunk 50
```

**Choosing chunk size:**

| Scenario | Chunk Size | Reasoning |
|----------|-----------|-----------|
| Fast commands (<1s) | 50-100 | Reduce frame overhead |
| Medium commands (1s-1m) | 10-20 | Balance overhead and parallelism |
| Slow commands (>1m) | 1-5 | Fine-grained progress tracking |
| Variable duration | 1 | Avoid blocking on long commands |

### Combined Resource Example

```bash
# CPU-intensive tasks
cuecmd encode_videos.txt --chunk 5 --cores 8 --memory 4

# Memory-intensive tasks
cuecmd process_large_files.txt --chunk 2 --cores 2 --memory 32

# I/O-intensive tasks
cuecmd copy_files.txt --chunk 20 --cores 1 --memory 1
```

## Job Control

### Job Metadata

Set show, shot, and user information:

```bash
# Use environment variables
export SHOW="my_project"
export SHOT="seq010_shot020"
cuecmd commands.txt

# Override with arguments
cuecmd commands.txt --show prod --shot sh100 --user artist

# Custom job name
cuecmd commands.txt --job-name "batch_processing_v1"
```

### Launch Modes

#### Normal Launch

```bash
cuecmd commands.txt
```

Job starts immediately and runs.

#### Paused Launch

```bash
cuecmd commands.txt --pause
```

Job is created but paused. Unpause when ready:

```bash
cueadmin -unpause <job_name>
```

**Use cases:**
- Review job configuration first
- Wait for specific time window
- Coordinate with other jobs

#### Pretend Mode

```bash
cuecmd commands.txt --pretend
```

Shows what would be submitted without actually submitting:

```
=== Pretend Mode ===
Job name: my_project_sh100_user_commands
Frame range: 1-20
Chunk size: 5
Cores per frame: 1.0
Memory per frame: 1.0GB
```

**Use cases:**
- Verify frame range calculation
- Check resource allocation
- Debug job configuration

## Common Workflows

### Image Processing

```bash
# Resize images in batch
find /images -name "*.jpg" | while read img; do
  out="/thumbs/$(basename $img)"
  echo "convert '$img' -resize 800x600 '$out'"
done > resize.txt

cuecmd resize.txt --chunk 20 --cores 2 --memory 2
```

### Data Extraction

```bash
# Extract data from logs
for log in /logs/*.log; do
  echo "python extract.py '$log' > '/results/$(basename $log .log).csv'"
done > extract.txt

cuecmd extract.txt --chunk 10
```

### Archive Compression

```bash
# Compress old files
find /archive -mtime +90 -type f | while read f; do
  echo "gzip '$f'"
done > compress.txt

cuecmd compress.txt --chunk 100 --cores 1 --memory 1
```

### Video Encoding

```bash
# Transcode videos
for video in /raw/*.mov; do
  out="/encoded/$(basename $video .mov).mp4"
  echo "ffmpeg -i '$video' -c:v libx264 '$out'"
done > encode.txt

cuecmd encode.txt --chunk 2 --cores 8 --memory 8
```

### Scientific Computing

```bash
# Parameter sweep for simulations
for temp in {100..500..10}; do
  for pressure in {1..10}; do
    echo "simulate --temp $temp --pressure $pressure --output sim_${temp}_${pressure}.dat"
  done
done > simulations.txt

cuecmd simulations.txt --chunk 5 --cores 16 --memory 32
```

### Testing Suite

```bash
# Run test suites in parallel
cat > tests.txt << 'EOF'
pytest tests/unit --junitxml=results/unit.xml
pytest tests/integration --junitxml=results/integration.xml
pytest tests/e2e --junitxml=results/e2e.xml
pytest tests/performance --junitxml=results/performance.xml
EOF

cuecmd tests.txt --cores 4 --memory 8
```

## Best Practices

### Command Design

**✅ Do:**
- Use absolute paths or well-known relative paths
- Make commands idempotent (safe to rerun)
- Include error handling in commands
- Test commands locally first
- Output to unique file names

**❌ Don't:**
- Rely on current working directory
- Use interactive commands (requiring input)
- Create dependencies between commands
- Assume specific execution order
- Overwrite shared files

### Performance Optimization

**Minimize Overhead:**
```bash
# Bad: Too many small frames
cuecmd 10000_commands.txt  # 10000 frames

# Good: Appropriate chunking
cuecmd 10000_commands.txt --chunk 100  # 100 frames
```

**Match Resources to Needs:**
```bash
# Overallocated (wastes resources)
cuecmd simple_commands.txt --cores 16 --memory 64

# Right-sized
cuecmd simple_commands.txt --cores 1 --memory 1
```

**I/O Optimization:**
```bash
# Read from fast storage
# Write to fast storage initially
# Move to archive storage after completion
```

### Error Management

**Command-level error handling:**
```bash
# Exit on error
command || exit 1

# Retry logic
for i in {1..3}; do command && break || sleep 5; done

# Fallback
command || fallback_command
```

**Job-level monitoring:**
```bash
# After job completion, check for failures
cueman -lf job_name -state DEAD

# Review logs
less /var/tmp/cue/job_name/frame_001/rqlog
```

### Resource Monitoring

**Check actual usage:**
```bash
# High memory frames
cueman -lf job_name -memory gt8

# Long-running frames
cueman -lf job_name -duration gt2

# Adjust for next run based on results
```

## Troubleshooting

### Jobs Don't Start

**Check queue:**
```bash
cueadmin -lj
# Look for job in list
```

**Verify connection:**
```bash
echo $OPENCUE_HOSTS
cueadmin -ls  # Should list shows
```

### Commands Fail

**Review frame logs:**
```bash
# Find log location
cueman -lf job_name

# View logs
less /var/tmp/cue/<job>/<frame>/rqlog
```

**Test locally:**
```bash
# Extract command from file
sed -n '1p' commands.txt

# Run locally to debug
bash -c "$(sed -n '1p' commands.txt)"
```

### Performance Issues

**Too many frames:**
```bash
# Increase chunk size
cuecmd commands.txt --chunk 20
```

**Insufficient resources:**
```bash
# Allocate more
cuecmd commands.txt --cores 4 --memory 8
```

**Uneven load:**
```bash
# Sort commands by expected duration
# Put similar commands together
```

### File Access Issues

**Path problems:**
```bash
# Use absolute paths
echo "/full/path/to/command input.txt"

# Or set working directory in command
echo "cd /working/dir && command input.txt"
```

**Permissions:**
```bash
# Ensure files readable by render user
chmod 644 input_files/*
chmod 755 scripts/*
```

## Summary

Cuecmd provides a simple, powerful way to parallelize shell commands:

- **Create** text file with commands
- **Configure** resources and chunking
- **Submit** to OpenCue
- **Monitor** execution
- **Review** results

This approach works for any batch processing task, from simple file operations to complex scientific computing.
