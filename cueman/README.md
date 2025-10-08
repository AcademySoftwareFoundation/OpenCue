# OpenCue Cueman

Cueman is a command-line job management tool for OpenCue that provides efficient job control operations. It offers a streamlined interface for managing jobs, frames, and processes with advanced filtering and batch operation capabilities.

**For detailed tutorials and real-world examples, see [cueman_tutorial.md](cueman_tutorial.md)**

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Getting Help](#getting-help)
6. [Basic Usage](#basic-usage)
7. [Job Operations](#job-operations)
8. [Frame Operations](#frame-operations)
9. [Frame Manipulation](#frame-manipulation)
10. [Filtering Options](#filtering-options)
11. [Process Listing](#process-listing)
12. [Common Options](#common-options)
13. [Examples](#some-examples-on-how-to-use-cueman)
14. [Environment Variables](#environment-variables)
15. [Important Notes](#important-notes)
16. [Troubleshooting](#troubleshooting)
17. [Documentation](#documentation)
18. [Running Tests](#running-tests)
19. [Docker Support](#docker-support)
20. [Contributing](#contributing)

## Overview

The `cueman` command-line tool is designed to enhance the OpenCue experience by providing a user-friendly interface for managing jobs and frames. It builds upon the existing OpenCue Python API and `cueadmin` commands, offering additional features and improved usability.

### About the Name

The name "cueman" is a play on words that combines two concepts:
 
1. **"Cue"** - From OpenCue, the render farm management system it's built for
2. **"man"** - From the Unix/Linux tradition of command-line tools (like man pages, or tools ending in "man")

So "cueman" literally means "Cue manager" or "the man for Cue" - it's the command-line tool that manages OpenCue jobs.

### What Cueman Provides

Cueman extends the functionality of cueadmin and the OpenCue Python API, enabling users to efficiently manage jobs, frames, and processes through a command-line interface. Key capabilities include:

- **Job Control**: Pause/Resume/Terminate jobs with batch operations
- **Frame Management**: Retry/Kill/Eat frames with advanced filtering
- **Smart Filtering**: Filter operations by state, memory, duration, and layers  
- **Frame Manipulation**: Stagger and reorder frames for optimal scheduling
- **Process Monitoring**: View and filter running processes
- **Batch Operations**: Job control with wildcard support and comma-separated lists
- **User Experience**: Integrated help, verbose logging, and user-friendly error messages

Cueman includes a full test suite, CI/CD integration, and comprehensive documentation with real-world examples.

### Integration

Cueman is fully integrated into the OpenCue ecosystem:
- **Build Pipeline**: Included in GitHub Actions workflows
- **Packaging**: Distributed via pyproject.toml as `opencue-cueman`
- **Environment**: Available in sandbox environments
- **Quality**: Full Dockerfile and linting support included

Cueman is available as a standard OpenCue CLI package and can be installed with `pip install opencue-cueman`.

## Features

- **Job Management**
  - Pause/Resume jobs
  - Terminate jobs with proper reason tracking
  - Set retry limits on jobs
  - Enable/Disable auto-eat functionality

- **Frame Operations**
  - List frames with filtering options (state, range, layer, memory, duration)
  - Kill running frames
  - Retry failed frames
  - Eat frames (mark as succeeded without running)
  - Mark frames as done (resolve dependencies)
  - Stagger frame execution
  - Reorder frame execution (FIRST, LAST, REVERSE)

- **Process Management**
  - List running processes with memory and duration filters
  - Filter by job, layer, or frame criteria

- **Layer Operations**
  - List layers in a job
  - Apply frame operations to specific layers

## Installation

### Prerequisites
- OpenCue server running and accessible
- Python 3.7 or higher
- OpenCue Python packages installed

### Install Methods

Cueman is installed as part of the OpenCue Python packages:

```bash
pip install opencue-cueman
```

Or install from source:

```bash
cd OpenCue/cueman
pip install .
```

### Configuration
Set up your environment variables:
```bash
export OPENCUE_HOSTS="your-cuebot-server:8443"
export OPENCUE_FACILITY="your-facility-code"
```

## Quick Start

1. **Verify Installation:**
   ```bash
   cueman -h  # Should show help message
   ```

2. **List jobs to get job names:**
   ```bash
   cueadmin -lj  # Lists all jobs
   ```

3. **Basic operations:**
   ```bash
   # Get job information
   cueman -info your_job_name
   
   # List frames
   cueman -lf your_job_name
   
   # List only running frames
   cueman -lf your_job_name -state RUNNING
   ```

## Getting Help

```bash
# Display help message
cueman -h
cueman --help

# Running cueman without arguments also shows help
cueman
```

## Basic Usage

```bash
# List frames for a job
cueman -lf job_name

# List running processes
cueman -lp job_name

# List layers
cueman -ll job_name

# Get job info
cueman -info job_name
```

## Job Operations

```bash
# Pause jobs
cueman -pause job1,job2,job3

# Resume jobs
cueman -resume job1,job2

# Terminate jobs
cueman -term job1,job2

# Set maximum retries
cueman -retries job_name 5

# Enable auto-eat (automatically eat dead frames)
cueman -autoeaton job1,job2

# Disable auto-eat
cueman -autoeatoff job1,job2
```

## Frame Operations

```bash
# Kill running frames (by default only kills RUNNING frames)
cueman -kill job_name

# Kill frames with specific states
cueman -kill job_name -state RUNNING WAITING

# Retry frames
cueman -retry job_name

# Eat frames (mark as succeeded)
cueman -eat job_name

# Mark frames as done (resolve dependencies)
cueman -done job_name

# With filters
cueman -kill job_name -layer render_layer -range 1-100
cueman -retry job_name -state DEAD
```

## Frame Manipulation

```bash
# Stagger frames by increment (must be positive integer)
cueman -stagger job_name 1-100 5

# Reorder frames (position must be FIRST, LAST, or REVERSE)
cueman -reorder job_name 1-100 FIRST
cueman -reorder job_name 50-100 LAST
cueman -reorder job_name 1-100 REVERSE
```

## Filtering Options

### State Filter
```bash
cueman -lf job_name -state RUNNING WAITING
```

### Range Filter
```bash
cueman -lf job_name -range 1-100
cueman -lf job_name -range 1,3,5,7-10
```

### Layer Filter
```bash
cueman -lf job_name -layer render_layer comp_layer
```

### Memory Filter
```bash
# Frames using 2-4 GB (both values must be non-negative, min < max)
cueman -lf job_name -memory 2-4

# Frames using less than 2 GB
cueman -lf job_name -memory lt2

# Frames using more than 4 GB
cueman -lf job_name -memory gt4
```

**Input Validation:** Values must be non-negative numbers. Range format requires `min < max` (e.g., `2-8`, `0-5`). Invalid formats like `8-2` (reversed), `2--5` (double dash), or `2-3-5` (multiple dashes) are rejected.

### Duration Filter
```bash
# Frames running 1-2 hours (both values must be non-negative, min < max)
cueman -lf job_name -duration 1-2

# Frames running more than 3.5 hours
cueman -lf job_name -duration gt3.5

# Frames running less than 0.5 hours
cueman -lf job_name -duration lt0.5
```

**Input Validation:** Values must be non-negative numbers. Range format requires `min < max` (e.g., `1-3`, `0-5`). Invalid formats like `5-2` (reversed), `2--5` (double dash), `2-3-5` (multiple dashes), or `-5` (negative) are rejected.

### Pagination
```bash
# View second page of results (default 1000 per page)
cueman -lf job_name -page 2

# Change page size
cueman -lf job_name -limit 500
```

## Process Listing

```bash
# List all processes for a job
cueman -lp job_name

# Filter by duration and memory
cueman -lp job_name -duration 2-4 -memory 4-8
```

## Common Options

- `-h, --help`: Show help message and exit
- `-v, --verbose`: Enable verbose logging
- `-server HOSTNAME`: Specify OpenCue server address(es)
- `-facility CODE`: Specify facility code
- `-force`: Skip confirmation prompts for destructive operations

## Some Examples on How to Use Cueman

### Handling Stuck Frames
```bash
# Find frames running more than 12 hours
cueman -lf job_name -duration gt12

# Kill and retry them
cueman -kill job_name -duration gt12
cueman -retry job_name -state DEAD
```

### Batch Job Management
```bash
# Pause multiple jobs
cueman -pause "show_shot_*,show_comp_*"

# Terminate all test jobs
cueman -term "test_*" -force
```

### Complex Frame Selection
```bash
# Retry specific frames on specific layers
cueman -retry job_name -layer render -range 1-50,100-150

# Kill high memory frames
cueman -kill job_name -memory gt16
```

## Environment Variables

- `OPENCUE_CONFIG_FILE`: Path to OpenCue configuration file
- `OPENCUE_HOSTS`: Comma-separated list of OpenCue servers
- `OPENCUE_FACILITY`: Default facility

## Important Notes

**Safety Guidelines:**
- Frame operations apply to ALL matching frames - always use filters carefully
- The `-force` flag skips confirmation prompts - use with extreme caution
- Preview operations with `-lf` before running destructive commands like `-kill`

**Usage Notes:**
- Memory values are specified in GB (e.g., `gt16` = greater than 16GB)
- Duration values are specified in hours (e.g., `gt12` = greater than 12 hours)
- Memory and duration ranges must use non-negative values with min < max (e.g., `2-5` not `5-2`)
- Input validation ensures only valid ranges are accepted (rejects negative, reversed, and malformed inputs)
- Job names support wildcards and comma-separated lists
- Use `cueman -h` anytime to see all available commands and options
- Error messages are user-friendly and clearly indicate when jobs don't exist or inputs are invalid

**Best Practices:**
- Always verify job state with `-info` before major operations
- Use specific filters to target exact frames you want to affect
- Combine multiple filters for precise control
- Test commands on small jobs before applying to large productions

## Troubleshooting

### Getting Help
If you're unsure about command syntax or available options:
```bash
cueman -h                    # Show all commands and options
cueman --help                # Same as -h
cueman                       # Running without args also shows help
```

### Common Issues
- **No command specified**: Cueman requires at least one command flag (e.g., `-lf`, `-info`, `-pause`)
- **Job does not exist**: Cueman will clearly indicate when a specified job name doesn't exist
- **Connection errors**: Use `-server hostname` to specify your OpenCue server
- **Permission errors**: Some operations require appropriate OpenCue permissions

### Error Examples
When a job doesn't exist or inputs are invalid, you'll see clear error messages:

**Job not found:**
```bash
$ cueman -lf nonexistent_job
Error: Job 'nonexistent_job' does not exist.

$ cueman -info missing_job
Error: Job 'missing_job' does not exist.
```

**Invalid duration values:**
```bash
$ cueman -lp job_name -duration 5-2
Invalid duration range '5-2'. Minimum value must be less than maximum value.

$ cueman -lp job_name -duration 2--5
Invalid duration format '2--5'. Expected format: x-y where x and y are non-negative numbers.

$ cueman -lp job_name -duration -5
Invalid duration format '-5'. Value cannot be negative.
```

**Invalid memory values:**
```bash
$ cueman -lp job_name -memory 8-2
Invalid memory range '8-2'. Minimum value must be less than maximum value.

$ cueman -lp job_name -memory 2-3-5
Invalid memory format '2-3-5'. Expected format: x-y where x and y are non-negative numbers.
```

### Verbose Output
For debugging connection or operation issues:
```bash
cueman -v -info job_name     # Enable verbose logging
```

## Documentation

- **[README.md](README.md)** - This file, quick reference and overview
- **[cueman_tutorial.md](cueman_tutorial.md)** - Comprehensive tutorial with real-world scenarios
- **Built-in help** - Use `cueman -h` for command-line help

## Running Tests

Cueman includes a comprehensive test suite with tests covering unit tests and integration workflows.

### Quick Start

```bash
# Install with test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=cueman --cov-report=term-missing
```

### Test Infrastructure

**Test Dependencies:**
- `pytest` - Modern test framework
- `pytest` - Coverage reporting
- `pytest-mock` - Enhanced mocking
- `mock` - Core mocking library
- `pyfakefs` - Filesystem mocking

**Test Types:**
- **Unit tests** - Function-level testing (`tests/test_main.py`)
- **Integration tests** - Workflow testing (`tests/test_integration_workflows.py`)
- **Test suite** - Combined test runner (`tests/test_suite.py`)

### Running Tests

```bash
# Basic test run
pytest tests/

# Verbose output
pytest -v

# Run specific test file
pytest tests/test_integration_workflows.py

# Run with coverage and HTML report
pytest --cov=cueman --cov-report=html --cov-report=term-missing

# Use the convenience script
./run_tests.sh --coverage --html
```

### Coverage Reporting

```bash
# Terminal coverage report
pytest --cov=cueman --cov-report=term-missing

# HTML coverage report (generates htmlcov/ directory)
pytest --cov=cueman --cov-report=html

# XML coverage for CI/CD
pytest --cov=cueman --cov-report=xml
```

### Development Testing

**For contributors:**

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests with linting
pytest && pylint cueman tests

# Run tests across Python versions (requires tox)
tox

# Format code
black cueman tests
isort cueman tests
```

**CI/CD Integration:**

```bash
# In OpenCue root directory
./ci/run_python_tests.sh     # Includes cueman tests
./ci/run_python_lint.sh      # Includes cueman linting

# Run cueman tests specifically
cd cueman && python -m pytest tests/
```

### Test Configuration

Tests are configured via `pyproject.toml`:
- **pytest.ini_options** - Test discovery and execution
- **coverage settings** - Coverage reporting configuration
- **markers** - Test categorization (unit, integration, slow)

### Continuous Integration

The test suite is integrated into:
- **GitHub Actions** - Automated testing on PRs
- **Docker builds** - Container-based testing
- **Lint pipeline** - Code quality checks

## Docker Support

### Building the Docker Image

From the OpenCue root directory:
```bash
docker build -f cueman/Dockerfile -t cueman .
```

### Running the Docker Container

**Basic run (shows usage information):**
```bash
docker run --rm cueman
```

**Interactive shell access:**
```bash
docker run --rm -it cueman /bin/bash
```

**View documentation:**
```bash
docker run --rm cueman ls -la /opt/opencue/docs/
docker run --rm cueman cat /opt/opencue/docs/README.md
```

**Run with volume mount (to access local files):**
```bash
docker run --rm -v $(pwd):/workspace cueman
```

### Example Output

When you run `docker run --rm cueman`, you'll see:
```
OpenCue Cueman - CLI Job Management Tool
Install with: pip install opencue-cueman
Documentation available in /opt/opencue/docs/
Source code available in /opt/opencue/cueman/
```

## Contributing

### Development Setup

```bash
# Clone and setup
git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
cd OpenCue/cueman

# Install with development dependencies
pip install -e ".[dev]"
```

### Testing and Quality

```bash
# Run comprehensive test suite (tests)
pytest --cov=cueman --cov-report=term-missing

# Code formatting and linting
black cueman tests && isort cueman tests
pylint cueman tests

# Multi-environment testing
tox
```