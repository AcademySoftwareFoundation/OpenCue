---
title: "Cuecmd - Command Execution Tool"
nav_order: 60
parent: "Command Line Tools"
grand_parent: "Reference"
layout: default
date: 2025-10-02
description: >
  Cuecmd is a command-line tool for OpenCue that executes a list of shell
  commands as frames on the render farm, enabling batch processing and parallelization.
---

# Cuecmd - Command Execution Tool

Cuecmd is a command-line tool that executes arbitrary shell commands on the OpenCue render farm. It reads a text file containing commands and distributes them across multiple frames for parallel execution.

## Overview

Cuecmd provides a simple way to parallelize any batch of shell commands using the OpenCue infrastructure. Commands can be chunked together to optimize resource usage and execution time.

### Key Features

- **Command batching**: Execute any list of shell commands on the render farm
- **Chunking**: Group multiple commands per frame for efficient resource usage
- **Resource control**: Specify cores and memory requirements per frame
- **Job management**: Launch jobs paused or test with pretend mode
- **Flexible configuration**: Override show, shot, and user from command line
- **Simple input format**: Plain text file with one command per line

## Installation

### Prerequisites

- OpenCue server running and accessible
- Python 3.7 or higher
- OpenCue Python packages installed

### Install from PyPI

```bash
pip install opencue-cuecmd
```

### Install from Source

```bash
cd OpenCue/cuecmd
pip install .
```

### Configuration

Set up your environment variables:
```bash
export OPENCUE_HOSTS="your-cuebot-server:8443"
export OPENCUE_FACILITY="your-facility-code"
```

## Basic Usage

```bash
cuecmd [options] <command_file>
```

### Quick Example

```bash
# Create a command file
cat > commands.txt << EOF
echo "Processing file 1"
echo "Processing file 2"
echo "Processing file 3"
EOF

# Submit to OpenCue
cuecmd commands.txt
```

## Command-Line Options

### Required Arguments

| Argument | Description |
|----------|-------------|
| `command_file` | A text file with commands to run (one per line) |

### Execution Options

| Option | Description | Default |
|--------|-------------|---------|
| `-c, --chunk <N>` | Number of commands per frame | 1 |
| `--cores <N>` | Number of cores required per frame | 1.0 |
| `--memory <N>` | Amount of RAM in GB per frame | 1.0 |

### Job Control

| Option | Description |
|--------|-------------|
| `-p, --pause` | Launch the job in paused state |
| `--pretend` | Generate outline without submitting |

### Job Metadata

| Option | Description | Default |
|--------|-------------|---------|
| `--show <name>` | Show name for the job | `$SHOW` or "default" |
| `-s, --shot <name>` | Shot name for the job | `$SHOT` or "default" |
| `--user <name>` | User name for the job | `$USER` or "unknown" |
| `--job-name <name>` | Custom job name | Auto-generated |

## Examples

### Example 1: Basic Command Execution

```bash
# Create command file
cat > render_frames.txt << EOF
blender -b scene.blend -o /tmp/frame_#### -f 1
blender -b scene.blend -o /tmp/frame_#### -f 2
blender -b scene.blend -o /tmp/frame_#### -f 3
EOF

# Submit to OpenCue
cuecmd render_frames.txt
```

### Example 2: Chunked Execution

Process 1000 images, 10 per frame:

```bash
# Generate commands
for i in {1..1000}; do
  echo "convert input_$i.jpg -resize 50% output_$i.jpg"
done > convert_images.txt

# Submit with chunking (creates 100 frames)
cuecmd convert_images.txt --chunk 10
```

### Example 3: Resource-Intensive Jobs

```bash
# Create simulation commands
cat > simulations.txt << EOF
python simulate.py --scene 1
python simulate.py --scene 2
python simulate.py --scene 3
EOF

# Submit with high resource requirements
cuecmd simulations.txt --cores 8 --memory 32
```

### Example 4: Testing Configuration

```bash
# Test without submitting
cuecmd commands.txt --chunk 5 --cores 2 --memory 4 --pretend

# Output shows:
# - Job name
# - Frame range
# - Resource requirements
# - Command file location
```

### Example 5: Custom Job Configuration

```bash
cuecmd commands.txt \
  --show "my_project" \
  --shot "sequence_010" \
  --user "artist" \
  --job-name "batch_processing" \
  --chunk 10 \
  --cores 4 \
  --memory 8 \
  --pause
```

### Example 6: Data Processing Pipeline

```bash
# Create processing pipeline
cat > data_pipeline.txt << EOF
python extract.py data1.csv
python extract.py data2.csv
python extract.py data3.csv
python transform.py data1.json
python transform.py data2.json
python transform.py data3.json
EOF

cuecmd data_pipeline.txt --chunk 2 --cores 2 --memory 4
```

## How It Works

1. **Command File Reading**: Cuecmd reads your text file containing commands
2. **Chunking**: Commands are divided into chunks based on `--chunk` parameter
3. **Frame Range Calculation**: Frame range is calculated as `1-ceil(commands/chunk)`
4. **Outline Creation**: An OpenCue outline is created with a Shell layer
5. **Job Submission**: The job is submitted to OpenCue for execution
6. **Frame Execution**: Each frame executes its assigned chunk of commands

### Technical Details

- Commands are copied to a temporary location for access during execution
- Each frame executes a helper script (`execute_commands.py`) that:
  - Reads the command file
  - Calculates which commands to run based on frame number and chunk size
  - Executes each command in sequence
  - Reports success/failure

## Environment Variables

Cuecmd respects the following environment variables:

| Variable | Description |
|----------|-------------|
| `OPENCUE_HOSTS` | Comma-separated list of OpenCue servers |
| `OPENCUE_FACILITY` | Default facility code |
| `SHOW` | Default show name |
| `SHOT` | Default shot name |
| `USER` | Default user name |

These can be overridden using command-line arguments.

## Command File Format

The command file is a simple text file with:
- One command per line
- Empty lines are ignored
- No special formatting required

Example:
```
echo "Starting batch"
python process.py input1.dat
python process.py input2.dat
echo "Batch complete"
```

## Monitoring Jobs

After submitting with cuecmd, monitor your job using:

```bash
# List all jobs
cueadmin -lj

# Get detailed job info
cueman -info <job_name>

# List frames
cueman -lf <job_name>

# View running processes
cueman -lp <job_name>
```

## Best Practices

### Resource Allocation

- Start with default resources and adjust based on actual usage
- Monitor initial frames to determine optimal core/memory settings
- Use `--pretend` to verify configuration before submitting

### Chunking Strategy

- Small, fast commands: Use larger chunk sizes (10-100)
- Long-running commands: Use smaller chunk sizes (1-5)
- Mixed workloads: Group similar commands together

### Error Handling

- Test commands locally before submitting to the farm
- Verify file paths are accessible from render nodes
- Check dependencies are available on all render nodes
- Review frame logs if commands fail

### Job Organization

- Use meaningful job names for easy identification
- Group related commands in separate files
- Keep command files for reproducibility
- Document command file purpose and parameters

## Troubleshooting

### Command File Not Found

```bash
# Verify file exists
ls -l commands.txt

# Use absolute path
cuecmd $(pwd)/commands.txt
```

### No Commands Found

```bash
# Check file has content
cat commands.txt

# Verify not all blank lines
grep -v '^[[:space:]]*$' commands.txt
```

### Job Fails to Launch

```bash
# Check OpenCue connection
echo $OPENCUE_HOSTS
cueadmin -lj

# Verify Python packages
python -c "import outline"
```

### Commands Fail During Execution

- Verify command syntax is correct
- Check file paths are accessible from render nodes
- Ensure sufficient resources allocated
- Review frame logs for detailed errors

## Comparison with Other Tools

| Tool | Use Case                         | Input Format |
|------|----------------------------------|--------------|
| **cuecmd** | Execute arbitrary shell commands | Text file with commands |
| **pycuerun** | Submit Python-based jobs         | Python outline scripts |
| **cuesubmit** | Submit jobs using an UI          | GUI/CLI for standard jobs |
