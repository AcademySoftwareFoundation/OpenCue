---
title: "Command Execution on the Render Farm"
nav_order: 14
parent: "Concepts"
layout: default
date: 2025-10-02
description: >
  Understanding how arbitrary shell commands are executed on the OpenCue
  render farm using cuecmd for batch processing and parallelization.
---

# Command Execution on the Render Farm

Learn how OpenCue enables execution of arbitrary shell commands across the render farm for batch processing and parallelization.

## Overview

OpenCue supports executing arbitrary shell commands on the render farm through the **cuecmd** tool. This approach transforms any batch of shell commands into parallelized render farm jobs, enabling efficient processing of tasks that don't require specialized render applications.

## Core Concepts

### Command Files

A **command file** is a simple text file containing shell commands (one per line) that you want to execute on the render farm:

```
convert image_001.jpg -resize 50% thumb_001.jpg
convert image_002.jpg -resize 50% thumb_002.jpg
convert image_003.jpg -resize 50% thumb_003.jpg
```

Benefits:
- **Simple format**: Plain text, easy to generate
- **Flexible**: Any valid shell command
- **Version controlled**: Can be tracked in git
- **Reusable**: Same file for multiple runs

### Chunking

**Chunking** groups multiple commands to execute on a single frame, optimizing resource usage:

```
Without chunking (chunk=1):
  10 commands = 10 frames
  Each frame executes 1 command

With chunking (chunk=5):
  10 commands = 2 frames
  Each frame executes 5 commands
```

**When to use chunking:**
- Commands execute quickly (seconds)
- Minimize frame startup overhead
- Reduce scheduling complexity

**When to avoid chunking:**
- Commands take significant time (minutes/hours)
- Need individual command failure isolation
- Want fine-grained progress tracking

### Frame Distribution

Commands are distributed across frames using a simple calculation:

```
Frame 1: Commands 1 to chunk_size
Frame 2: Commands (chunk_size + 1) to (2 × chunk_size)
Frame N: Remaining commands
```

Example with 23 commands and chunk size 5:
- Frame 1: Commands 1-5
- Frame 2: Commands 6-10
- Frame 3: Commands 11-15
- Frame 4: Commands 16-20
- Frame 5: Commands 21-23 (only 3 commands)

### Resource Allocation

Each frame can specify:

**Cores**: Number of CPU cores required
```bash
cuecmd commands.txt --cores 4
```

**Memory**: RAM in gigabytes
```bash
cuecmd commands.txt --memory 8
```

Resources are allocated per-frame, so all commands in a chunk share the same resources.

## Execution Flow

1. **Preparation**
   - Read command file
   - Count commands
   - Calculate frame range based on chunk size
   - Copy command file to accessible location

2. **Job Creation**
   - Generate OpenCue outline
   - Create Shell layer with frame range
   - Configure resources per frame
   - Set job metadata (show, shot, user)

3. **Submission**
   - Submit job to OpenCue
   - Job enters queue
   - Frames distributed to available hosts

4. **Execution**
   - Frame starts on render node
   - Helper script (`execute_commands.py`) runs
   - Reads command file
   - Calculates which commands to execute
   - Runs commands sequentially
   - Reports success/failure

5. **Completion**
   - All frames complete
   - Job marked as finished
   - Results available in logs

## Use Cases

### Data Processing

Process large datasets in parallel:

```bash
# Generate commands for 1000 files
for i in {1..1000}; do
  echo "python process.py data_${i}.csv"
done > process_data.txt

# Execute with 10 files per frame
cuecmd process_data.txt --chunk 10
```

### Batch Conversions

Convert files in various formats:

```bash
# Image format conversion
for img in *.png; do
  echo "convert $img -format jpg ${img%.png}.jpg"
done > convert.txt

cuecmd convert.txt --chunk 20
```

### Simulation Workflows

Run parameter sweeps:

```bash
# Vary simulation parameters
for temp in {100..500..10}; do
  echo "simulate --temperature $temp --output sim_${temp}.dat"
done > simulations.txt

cuecmd simulations.txt --cores 8 --memory 16
```

### Testing and Validation

Execute test suites:

```bash
# Run tests across environments
echo "pytest tests/unit/" > tests.txt
echo "pytest tests/integration/" >> tests.txt
echo "pytest tests/e2e/" >> tests.txt

cuecmd tests.txt
```

### Archive Operations

Batch file operations:

```bash
# Compress old files
find /archive -name "*.log" -mtime +90 | while read f; do
  echo "gzip $f"
done > compress.txt

cuecmd compress.txt --chunk 50
```

## Comparison with Other Approaches

### vs. Traditional Job Submission

**Traditional (PyOutline)**:
```python
# Write Python outline
outline = Outline("job")
layer = Shell("process", command="python process.py", range="1-100")
outline.add_layer(layer)
launch(outline)
```

**Cuecmd**:
```bash
# Simple command file
for i in {1..100}; do
  echo "python process.py --frame $i"
done > commands.txt

cuecmd commands.txt
```

**Advantages of cuecmd**:
- No Python coding required
- Faster for ad-hoc tasks
- Easy to generate programmatically
- Simple to modify and rerun

**Advantages of PyOutline**:
- More control over layer structure
- Complex dependencies
- Custom frame ranges
- Advanced features (preprocess, postprocess)

### vs. Local Execution

**Local sequential**:
```bash
# Runs on single machine
bash commands.txt
Time: N * average_command_time
```

**Cuecmd parallel**:
```bash
# Distributes across farm
cuecmd commands.txt --chunk 10
Time: (N / num_hosts / chunk_size) * average_command_time
```

**Speedup example**:
- 1000 commands @ 10 seconds each
- Local: 10,000 seconds (2.8 hours)
- Farm (100 hosts, chunk=10): ~100 seconds (1.7 minutes)

## Best Practices

### Command File Organization

**Good practices**:
- One command per line
- Full paths or relative to known location
- Commands are independent
- Can run in any order

**Avoid**:
- Commands with dependencies between them
- Commands that modify shared state
- Commands requiring interactive input

### Resource Planning

**Estimate requirements**:
```bash
# Test locally to determine resources
time command_example
# Note: CPU cores used, peak memory

# Set appropriate resources
cuecmd commands.txt --cores 2 --memory 4
```

**Monitor and adjust**:
```bash
# Check actual usage
cueman -lf job_name -memory gt4
cueman -lf job_name -duration gt1

# Adjust for future runs
```

### Error Handling

Commands should:
- Exit with non-zero on failure
- Write errors to stderr
- Clean up temporary files
- Be idempotent (safe to rerun)

### Testing Workflow

1. **Test locally**
   ```bash
   bash commands.txt  # Run subset locally
   ```

2. **Pretend mode**
   ```bash
   cuecmd commands.txt --pretend
   ```

3. **Small test run**
   ```bash
   head -10 commands.txt > test.txt
   cuecmd test.txt
   ```

4. **Full production run**
   ```bash
   cuecmd commands.txt --chunk 20 --cores 4
   ```

## Advanced Topics

### Dynamic Command Generation

Generate commands based on runtime data:

```bash
# From database query
mysql -e "SELECT file FROM processing_queue" | \
  tail -n +2 | \
  awk '{print "process " $1}' > commands.txt

cuecmd commands.txt
```

### Conditional Execution

Skip already processed files:

```bash
for file in input_*.dat; do
  output="${file%.dat}.result"
  if [ ! -f "$output" ]; then
    echo "process $file > $output"
  fi
done > commands.txt
```

### Dependency Management

For simple dependencies, use chunking:

```bash
# Commands within a chunk run sequentially
echo "step1.sh && step2.sh && step3.sh" > commands.txt
cuecmd commands.txt
```

For complex dependencies, use PyOutline layers instead.

## Troubleshooting

### Commands Not Executing

**Check**:
- Command file format (one per line)
- Paths are accessible from render nodes
- Required software installed on nodes
- Environment variables set correctly

### Performance Issues

**Optimize**:
- Adjust chunk size (too small = overhead, too large = poor load balancing)
- Match resources to actual usage
- Use faster storage for I/O intensive commands
- Distribute across more hosts

### Resource Exhaustion

**Solutions**:
- Increase memory allocation
- Reduce commands per chunk
- Add swap space on nodes
- Limit concurrent frames

## Summary

Command execution on OpenCue via cuecmd provides:
- **Simplicity**: Plain text command files
- **Scalability**: Parallel execution across farm
- **Flexibility**: Any shell command supported
- **Control**: Resource and chunking options
- **Efficiency**: Optimal use of render resources

This approach democratizes render farm access, making it useful for any batch processing task, not just rendering.
