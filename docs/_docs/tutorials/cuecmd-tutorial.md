---
title: "Cuecmd Tutorial"
nav_order: 71
parent: Tutorials
layout: default
date: 2025-10-02
description: >
  Step-by-step tutorial for using cuecmd to execute batch commands on the
  OpenCue render farm, from basic usage to advanced workflows.
---

# Cuecmd Tutorial

This tutorial walks you through using cuecmd to execute batch shell commands on the OpenCue render farm, from basic operations to advanced workflows.

**Time required:** Approximately 45 minutes

## Prerequisites

- OpenCue sandbox environment running
- Python 3.7 or later installed
- OpenCue client tools installed
- Basic knowledge of shell commands

## Part 1: Getting Started with Cuecmd

### What You'll Learn

- Create and submit simple command files
- Monitor job execution
- Review results and logs

### Step 1: Verify Installation

First, verify cuecmd is installed and accessible:

```bash
cuecmd --help
```

You should see usage information. If not, install cuecmd:

```bash
# From the OpenCue repository
cd OpenCue/cuecmd
pip install .
```

### Step 2: Create Your First Command File

Create a simple command file with test commands:

```bash
cat > hello_cuecmd.txt << 'EOF'
echo "Hello from command 1"
sleep 2
echo "Hello from command 2"
sleep 2
echo "Hello from command 3"
sleep 2
echo "Hello from command 4"
sleep 2
echo "Hello from command 5"
EOF
```

This file contains 5 commands that print messages and sleep briefly.

### Step 3: Submit to OpenCue

Submit the commands to OpenCue:

```bash
cuecmd hello_cuecmd.txt
```

You'll see output like:

```
Found 5 commands in /path/to/hello_cuecmd.txt
Frame range with chunking of 1: 1-5
Copied commands to: /tmp/cuecmd_abc123/hello_cuecmd.cmds
Successfully launched job: default_default_user_hello_cuecmd
```

**What happened:**
- Cuecmd read your 5 commands
- Created 5 frames (one per command, since chunk=1 by default)
- Copied the command file to a temporary location
- Submitted a job to OpenCue

### Step 4: Monitor the Job

List your jobs:

```bash
cueadmin -lj | grep $USER
```

You should see your job listed. Use cueman to get detailed information:

```bash
# Replace <job_name> with the actual job name from the submission output
cueman -info default_default_user_hello_cuecmd
```

List frames:

```bash
cueman -lf default_default_user_hello_cuecmd
```

You'll see the frame status (WAITING, RUNNING, SUCCEEDED).

### Step 5: Review Logs

Once frames complete, review the logs:

```bash
# Frame logs are typically in /var/tmp/cue/<job>/<frame>/
# Find the log directory from frame listing
cueman -lf default_default_user_hello_cuecmd

# View a frame log (adjust path as needed)
less /var/tmp/cue/<job>/<frame>/rqlog
```

You should see the output from your echo commands.

## Part 2: Working with Chunking

### What You'll Learn

- Understand chunking concepts
- Optimize frame count with chunking
- Balance overhead vs. parallelism

### Step 1: Create a Larger Command File

Generate 100 simple commands:

```bash
for i in {1..100}; do
  echo "echo 'Processing item $i'"
done > process_100.txt
```

### Step 2: Submit Without Chunking

First, submit without chunking (default):

```bash
cuecmd process_100.txt --pretend
```

**Pretend mode output:**

```
=== Pretend Mode ===
Job name: default_default_user_process_100
Frame range: 1-100
Chunk size: 1
Cores per frame: 1.0
Memory per frame: 1.0GB
```

This creates 100 frames. For fast commands, that's too many frames with too much overhead.

### Step 3: Submit With Chunking

Now chunk 10 commands per frame:

```bash
cuecmd process_100.txt --chunk 10 --pretend
```

**Pretend mode output:**

```
=== Pretend Mode ===
Job name: default_default_user_process_100
Frame range: 1-10
Chunk size: 10
Cores per frame: 1.0
Memory per frame: 1.0GB
```

Much better! Only 10 frames, each processing 10 commands.

### Step 4: Submit the Chunked Job

Remove `--pretend` to actually submit:

```bash
cuecmd process_100.txt --chunk 10
```

Monitor the job:

```bash
cueman -lf default_default_user_process_100
```

Notice how quickly frames complete since each processes 10 simple commands.

### Step 5: Understanding Chunk Size Trade-offs

Create a reference table for chunk sizing:

| Commands | Chunk Size | Frames | Use Case |
|----------|------------|--------|----------|
| 100 | 1 | 100 | Long-running commands (>1 min each) |
| 100 | 10 | 10 | Medium commands (10s-1min) |
| 100 | 50 | 2 | Fast commands (<10s) |
| 1000 | 100 | 10 | Very fast commands (<1s) |

**Rule of thumb:** Aim for frames that run at least 1-2 minutes to minimize overhead.

## Part 3: Resource Management

### What You'll Learn

- Allocate CPU cores
- Allocate memory
- Match resources to workload

### Step 1: CPU-Intensive Commands

Create commands that benefit from multiple cores:

```bash
cat > cpu_intensive.txt << 'EOF'
python3 -c "import time; [x**2 for x in range(10000000)]; time.sleep(5)"
python3 -c "import time; [x**2 for x in range(10000000)]; time.sleep(5)"
python3 -c "import time; [x**2 for x in range(10000000)]; time.sleep(5)"
python3 -c "import time; [x**2 for x in range(10000000)]; time.sleep(5)"
EOF
```

Submit with multiple cores:

```bash
cuecmd cpu_intensive.txt --cores 4 --pretend
```

**Output:**

```
=== Pretend Mode ===
Job name: default_default_user_cpu_intensive
Frame range: 1-4
Chunk size: 1
Cores per frame: 4.0
Memory per frame: 1.0GB
```

Each frame gets 4 CPU cores.

### Step 2: Memory-Intensive Commands

Create a command that uses significant memory:

```bash
cat > memory_test.txt << 'EOF'
python3 -c "import sys; data = 'x' * (500 * 1024 * 1024); print(f'Allocated {sys.getsizeof(data) / 1024 / 1024:.1f} MB')"
EOF
```

Submit with more memory:

```bash
cuecmd memory_test.txt --memory 2 --pretend
```

**Output:**

```
=== Pretend Mode ===
Job name: default_default_user_memory_test
Frame range: 1-1
Chunk size: 1
Cores per frame: 1.0
Memory per frame: 2.0GB
```

Frame gets 2GB of RAM.

### Step 3: Combined Resource Allocation

For real workloads, combine resources appropriately:

```bash
# Video encoding: CPU-intensive, moderate memory
cuecmd encode_videos.txt --chunk 2 --cores 8 --memory 4

# Data processing: Moderate CPU, high memory
cuecmd process_data.txt --chunk 5 --cores 2 --memory 16

# File operations: Low CPU, low memory, high concurrency
cuecmd copy_files.txt --chunk 50 --cores 1 --memory 1
```

## Part 4: Real-World Workflow - Image Processing

### What You'll Learn

- Generate command files from file lists
- Process files in batch
- Handle output paths

### Step 1: Create Sample Images

Create a directory with test images:

```bash
mkdir -p ~/cuecmd_tutorial/input ~/cuecmd_tutorial/output

# Create dummy image files
for i in {1..20}; do
  touch ~/cuecmd_tutorial/input/image_$(printf "%03d" $i).jpg
done
```

### Step 2: Generate Conversion Commands

Create commands to "process" these images:

```bash
cd ~/cuecmd_tutorial

# Generate conversion commands
for img in input/*.jpg; do
  basename=$(basename "$img" .jpg)
  echo "convert '$img' -resize 800x600 output/${basename}_thumb.jpg"
done > resize_commands.txt

# View the commands
head -3 resize_commands.txt
```

Output:

```
convert 'input/image_001.jpg' -resize 800x600 output/image_001_thumb.jpg
convert 'input/image_002.jpg' -resize 800x600 output/image_002_thumb.jpg
convert 'input/image_003.jpg' -resize 800x600 output/image_003_thumb.jpg
```

### Step 3: Submit the Job

Submit with appropriate chunking:

```bash
cuecmd resize_commands.txt --chunk 5 --cores 2 --memory 2
```

This creates 4 frames (20 images / 5 per frame), each with 2 cores and 2GB RAM.

### Step 4: Monitor Progress

Watch the job:

```bash
# Get job name from submission output, or list jobs
cueadmin -lj | grep $USER

# Monitor frames
watch -n 5 'cueman -lf <job_name> | head -20'
```

### Step 5: Verify Results

Once complete, verify output files:

```bash
ls -l output/
```

You should see 20 thumbnail images.

## Part 5: Advanced Workflows

### What You'll Learn

- Generate dynamic commands
- Handle conditional execution
- Implement error handling

### Step 1: Dynamic Command Generation from Database

Simulate generating commands from data:

```bash
# Create mock data file
cat > data_ids.txt << EOF
ID001
ID002
ID003
ID004
ID005
EOF

# Generate processing commands
while read id; do
  echo "python3 process_data.py --id $id --output results/${id}.csv"
done < data_ids.txt > process_ids.txt
```

### Step 2: Conditional Command Execution

Skip already processed files:

```bash
mkdir -p results

# Create command file that checks for existing results
cat > conditional_process.txt << 'EOF'
test -f results/ID001.csv || python3 process_data.py --id ID001 --output results/ID001.csv
test -f results/ID002.csv || python3 process_data.py --id ID002 --output results/ID002.csv
test -f results/ID003.csv || python3 process_data.py --id ID003 --output results/ID003.csv
EOF
```

This only processes files that don't already exist.

### Step 3: Error Handling in Commands

Add retry logic to commands:

```bash
cat > retry_commands.txt << 'EOF'
for i in {1..3}; do python3 flaky_process.py && break || sleep 5; done
for i in {1..3}; do python3 flaky_process.py && break || sleep 5; done
EOF
```

Each command retries up to 3 times with 5-second delays.

### Step 4: Chained Commands

Create commands with dependencies within a chunk:

```bash
cat > chained_commands.txt << 'EOF'
python3 step1_extract.py input.dat && python3 step2_transform.py temp.dat && python3 step3_load.py output.dat
EOF
```

Commands in the same chunk run sequentially, so dependencies work.

## Part 6: Job Control and Testing

### What You'll Learn

- Use pretend mode effectively
- Launch paused jobs
- Set job metadata

### Step 1: Test with Pretend Mode

Always test complex jobs first:

```bash
cuecmd large_job.txt \
  --chunk 20 \
  --cores 4 \
  --memory 8 \
  --show my_project \
  --shot seq010 \
  --pretend
```

Review the output carefully:

```
=== Pretend Mode ===
Job name: my_project_seq010_user_large_job
Frame range: 1-50
Chunk size: 20
Cores per frame: 4.0
Memory per frame: 8.0GB
Command file: /tmp/cuecmd_xyz/large_job.cmds
Would launch the job with the above settings.
```

Verify:
- Frame range is correct
- Resources match your needs
- Job name follows your conventions

### Step 2: Launch Paused for Review

For critical jobs, launch paused:

```bash
cuecmd large_job.txt \
  --chunk 20 \
  --cores 4 \
  --memory 8 \
  --show my_project \
  --shot seq010 \
  --pause
```

The job is created but not running. Review it:

```bash
cueman -info my_project_seq010_user_large_job
```

Unpause when ready:

```bash
cueadmin -unpause my_project_seq010_user_large_job
```

### Step 3: Custom Job Names

Use meaningful job names:

```bash
cuecmd commands.txt \
  --job-name "batch_processing_v2_2025_10_02" \
  --show production \
  --shot general
```

This makes jobs easier to identify and manage.

### Step 4: Environment Variables

Set defaults with environment variables:

```bash
# Set in your shell profile
export SHOW="my_project"
export SHOT="general"
export OPENCUE_HOSTS="cuebot-server:8443"

# Now just run
cuecmd commands.txt --chunk 10
```

Job uses your environment defaults.

## Part 7: Troubleshooting and Best Practices

### What You'll Learn

- Debug failed commands
- Optimize performance
- Follow best practices

### Step 1: Debugging Failed Commands

Create a command that will fail:

```bash
cat > failing_commands.txt << 'EOF'
echo "This works"
false
echo "This won't run"
EOF

cuecmd failing_commands.txt
```

The frame will fail. Debug it:

```bash
# Find the frame that failed
cueman -lf <job_name> -state DEAD

# View the frame log
less /var/tmp/cue/<job>/<frame>/rqlog
```

The log shows which command failed and why.

### Step 2: Test Locally First

Always test commands locally before submitting:

```bash
# Extract first command from file
sed -n '1p' commands.txt

# Run it locally
bash -c "$(sed -n '1p' commands.txt)"
```

Verify it works before submitting to the farm.

### Step 3: Performance Optimization

Monitor actual resource usage:

```bash
# After job completes, check actual memory usage
cueman -lf <job_name> -memory gt2

# Check frame durations
cueman -lf <job_name> -duration gt1
```

Adjust resources for next run based on actual usage.

### Step 4: Best Practices Checklist

Before submitting large jobs:

- [ ] Test commands locally
- [ ] Use pretend mode to verify configuration
- [ ] Start with a small test (first 10 commands)
- [ ] Choose appropriate chunk size
- [ ] Allocate resources based on testing
- [ ] Use absolute paths in commands
- [ ] Make commands idempotent (safe to rerun)
- [ ] Add error handling to commands
- [ ] Set meaningful job names
- [ ] Document your command generation process

## Summary

You've learned how to:

- Create and submit command files
- Use chunking to optimize frame count
- Allocate CPU cores and memory
- Build real-world workflows
- Generate dynamic command files
- Use pretend mode and paused launch
- Debug failed commands
- Follow best practices
