# OpenCue Cuecmd

Cuecmd is a command-line tool for OpenCue that executes a list of commands as frames on the render farm. It enables batch processing by chunking commands and submitting them as OpenCue jobs.

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Usage](#usage)
6. [Options](#options)
7. [Examples](#examples)
8. [Environment Variables](#environment-variables)
9. [How It Works](#how-it-works)
10. [Running Tests](#running-tests)
11. [Docker Support](#docker-support)
12. [Contributing](#contributing)

## Overview

`cuecmd` is a tool for executing arbitrary shell commands on the OpenCue render farm. It takes a text file containing a list of commands (one per line) and distributes them across multiple frames for parallel execution.

### About Cuecmd

The name "cuecmd" combines:
- **"Cue"** - From OpenCue, the render farm management system
- **"cmd"** - Short for command, representing its purpose of executing commands

The `cuecmd` provides a simple way to parallelize any batch of shell commands using the OpenCue infrastructure.

## Features

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

### Install Methods

Install as part of the OpenCue Python packages:

```bash
pip install opencue-cuecmd
```

Or install from source:

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

## Quick Start

1. **Create a command file:**
   ```bash
   cat > commands.txt << EOF
   echo "Processing file 1"
   echo "Processing file 2"
   echo "Processing file 3"
   EOF
   ```

2. **Submit to OpenCue:**
   ```bash
   cuecmd commands.txt
   ```

3. **Monitor the job:**
   ```bash
   cueadmin -lj  # List jobs
   cueman -lf <job_name>  # List frames
   ```

## Usage

```bash
cuecmd [options] <command_file>
```

### Basic Usage

```bash
# Submit a simple command list
cuecmd commands.txt

# Chunk 5 commands per frame
cuecmd commands.txt --chunk 5

# Specify resources
cuecmd commands.txt --cores 4 --memory 8

# Launch paused for review
cuecmd commands.txt --pause

# Test without submitting
cuecmd commands.txt --pretend
```

## Options

### Required Arguments
- `command_file` - A text file with a list of commands to run (one per line)

### Optional Arguments

#### Execution Options
- `-c, --chunk <N>` - Number of commands to chunk per frame (Default: 1)
- `--cores <N>` - Number of cores required per frame (Default: 1.0)
- `--memory <N>` - Amount of RAM in GB required per frame (Default: 1.0)

#### Job Control
- `-p, --pause` - Launch the job in the paused state
- `--pretend` - Generate the outline and print info without submitting

#### Job Metadata
- `--show <name>` - Show name for the job (Default: from $SHOW or "default")
- `-s, --shot <name>` - Shot name for the job (Default: from $SHOT or "default")
- `--user <name>` - User name for the job (Default: from $USER or "unknown")
- `--job-name <name>` - Custom job name (Default: auto-generated)

## Examples

### Example 1: Simple Command Execution
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
```bash
# Process 1000 images, 10 per frame
for i in {1..1000}; do
  echo "convert input_$i.jpg -resize 50% output_$i.jpg"
done > convert_images.txt

cuecmd convert_images.txt --chunk 10
# This creates 100 frames, each processing 10 images
```

### Example 3: Resource-Intensive Jobs
```bash
# Heavy computation requiring more resources
cat > simulations.txt << EOF
python simulate.py --scene 1
python simulate.py --scene 2
python simulate.py --scene 3
EOF

cuecmd simulations.txt --cores 8 --memory 32
```

### Example 4: Testing Before Launch
```bash
# Test the job configuration without submitting
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
# Generate processing commands
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

## Environment Variables

Cuecmd respects the following environment variables:

- `OPENCUE_HOSTS` - Comma-separated list of OpenCue servers
- `OPENCUE_FACILITY` - Default facility code
- `SHOW` - Default show name
- `SHOT` - Default shot name
- `USER` - Default user name

These can be overridden using command-line arguments.

## How It Works

1. **Command File Reading**: Cuecmd reads your text file containing commands
2. **Chunking**: Commands are divided into chunks based on the `--chunk` parameter
3. **Frame Range Calculation**: A frame range is calculated (1 to ceil(commands/chunk))
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

## Running Tests

The `cuecmd` includes a comprehensive test suite.

### Quick Start

```bash
# Install with test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=cuecmd --cov-report=term-missing
```

### Test Types

- **Unit tests** - Test individual functions (`tests/test_main.py`, `tests/test_execute_commands.py`)
- **Integration tests** - Test complete workflows (`tests/integration_tests.py`, `tests/test_integration_workflows.py`)

### Running Tests

```bash
# Basic test run
pytest tests/

# Verbose output
pytest -v

# Run specific test file
pytest tests/test_main.py

# Run with coverage and HTML report
pytest --cov=cuecmd --cov-report=html --cov-report=term-missing
```

### CI/CD Integration

Cuecmd is integrated into OpenCue's CI/CD pipeline:

```bash
# In OpenCue root directory
./ci/run_python_tests.sh     # Includes cuecmd tests
./ci/run_python_lint.sh      # Includes cuecmd linting
```

## Docker Support

### Building the Docker Image

From the OpenCue root directory:
```bash
docker build -f cuecmd/Dockerfile -t cuecmd .
```

### Running the Docker Container

**Show help:**
```bash
docker run --rm cuecmd cuecmd --help
```

**Test with commands:**
```bash
# Create test commands
echo "echo 'test 1'" > /tmp/commands.txt
echo "echo 'test 2'" >> /tmp/commands.txt

# Run in pretend mode
docker run --rm -v /tmp:/data cuecmd cuecmd /data/commands.txt --pretend
```

## Contributing

### Development Setup

```bash
# Clone and setup
git clone https://github.com/<username>/OpenCue.git
cd OpenCue/cuecmd

# Install with development dependencies
pip install -e ".[dev]"
```

### Testing and Quality

```bash
# Run tests
pytest --cov=cuecmd --cov-report=term-missing

# Code formatting and linting
black cuecmd tests
isort cuecmd tests
pylint cuecmd tests
```

### Guidelines

- Add tests for new features
- Update documentation for API changes
- Ensure all tests pass before submitting PRs

## Troubleshooting

### Common Issues

**Command file not found:**
```bash
# Make sure file exists and path is correct
ls -l commands.txt
cuecmd $(pwd)/commands.txt  # Use absolute path
```

**No commands found:**
```bash
# Check file has content and is not all blank lines
cat commands.txt
```

**Job fails to launch:**
```bash
# Check OpenCue connection
echo $OPENCUE_HOSTS
cueadmin -lj  # Test connection
```

**Commands fail during execution:**
- Check command syntax is correct
- Verify commands have access to required files/paths
- Ensure sufficient resources (cores/memory) are allocated
