---
title: "Cuecmd Quick Start"
nav_order: 6
parent: Quick Starts
layout: default
date: 2025-10-02
description: >
  Get started with cuecmd to execute batch commands on the OpenCue render farm
---

# Quick start with cuecmd

Learn how to use cuecmd to execute batch shell commands on the OpenCue render farm.

## What is cuecmd?

Cuecmd is a command-line tool that executes arbitrary shell commands from a text file as frames on the OpenCue render farm. It enables easy parallelization of batch operations without writing complex job scripts.

## Before you begin

Ensure you have:
- OpenCue sandbox environment running
- Python 3.7 or later installed
- OpenCue client tools installed

## Step 1: Install cuecmd

If you've already installed OpenCue client tools, cuecmd should be available:

```bash
# Verify installation
cuecmd --help
```

If not installed, install it with:

```bash
pip install opencue-cuecmd
```

Or from the OpenCue repository:

```bash
cd OpenCue/cuecmd
pip install .
```

## Step 2: Create a command file

Create a simple text file with commands (one per line):

```bash
cat > my_commands.txt << 'EOF'
echo "Processing item 1"
echo "Processing item 2"
echo "Processing item 3"
echo "Processing item 4"
echo "Processing item 5"
EOF
```

## Step 3: Submit to OpenCue

Submit the commands to OpenCue:

```bash
cuecmd my_commands.txt
```

You'll see output similar to:

```
Found 5 commands in /path/to/my_commands.txt
Frame range with chunking of 1: 1-5
Copied commands to: /tmp/cuecmd_abc123/my_commands.cmds
Successfully launched job: default_default_user_my_commands
```

## Step 4: Monitor the job

Use cueadmin or cueman to monitor your job:

```bash
# List all jobs
cueadmin -lj

# Get job details with cueman
cueman -info <job_name>

# List frames
cueman -lf <job_name>
```

## Step 5: Try advanced features

### Chunk multiple commands per frame

Group commands together to reduce frame overhead:

```bash
# 5 commands per frame (5 commands = 1 frame)
cuecmd my_commands.txt --chunk 5
```

### Specify resource requirements

```bash
# Request 4 cores and 8GB memory per frame
cuecmd my_commands.txt --cores 4 --memory 8
```

### Test before submitting

Use pretend mode to see what would be submitted:

```bash
cuecmd my_commands.txt --chunk 5 --pretend
```

Output:
```
=== Pretend Mode ===
Job name: default_default_user_my_commands
Frame range: 1-1
Chunk size: 5
Cores per frame: 1.0
Memory per frame: 1.0GB
Would launch the job with the above settings.
```

### Launch paused for review

```bash
# Launch job in paused state
cuecmd my_commands.txt --pause

# Unpause when ready
cueadmin -unpause <job_name>
```

## Example

Convert a batch of images:

```bash
# Generate conversion commands
for i in {1..100}; do
  echo "convert input_${i}.jpg -resize 50% output_${i}.jpg"
done > convert_images.txt

# Submit with 10 commands per frame (100 commands = 10 frames)
cuecmd convert_images.txt --chunk 10 --cores 2 --memory 2
```

## Troubleshooting

### Command file not found
```bash
# Use absolute path
cuecmd $(pwd)/my_commands.txt
```

### Job doesn't appear
```bash
# Check OpenCue connection
echo $OPENCUE_HOSTS
cueadmin -lj
```

### Commands fail
- Verify commands work locally first
- Check paths are accessible from render nodes
- Review frame logs for detailed errors

## Summary

You've learned how to:
- Install and verify cuecmd
- Create command files
- Submit jobs to OpenCue
- Monitor job execution
- Use chunking and resource controls
- Test with pretend mode

Cuecmd makes it easy to parallelize any batch of shell commands on the render farm!
