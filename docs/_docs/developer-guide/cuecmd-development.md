---
title: "Cuecmd Development Guide"
nav_order: 81
parent: "Developer Guide"
layout: default
date: 2025-10-02
description: >
  Technical documentation for developers contributing to cuecmd, including
  architecture, testing, and extension guidelines.
---

# Cuecmd Development Guide

This guide provides technical documentation for developers contributing to cuecmd.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Development Setup](#development-setup)
4. [Testing](#testing)
5. [Troubleshooting](#troubleshooting)

## Overview

Cuecmd is a command-line tool that enables batch execution of shell commands on the OpenCue render farm. It bridges the gap between simple shell scripts and complex render job submissions.

### Design Goals

- **Simplicity**: Minimal barrier to entry (plain text command files)
- **Flexibility**: Support any shell command
- **Integration**: Seamless integration with OpenCue infrastructure
- **Performance**: Efficient resource utilization through chunking
- **Reliability**: Robust error handling and logging

### Key Technologies

- **Python 3.7+**: Modern Python with type hints support
- **PyOutline**: OpenCue's job specification library
- **PyCue**: OpenCue's Python API client
- **Argparse**: Command-line argument parsing
- **Pytest**: Testing framework
- **Hatchling**: Modern Python build backend

## Architecture

### High-Level Architecture

```
┌─────────────┐
│   cuecmd    │  Command-line interface
│  (main.py)  │
└──────┬──────┘
       │
       ├─ Parse arguments
       ├─ Count commands
       ├─ Calculate frame range
       ├─ Copy command file
       └─ Create outline
              │
              ├─ Generate Shell layer
              └─ Submit to OpenCue
                     │
                     └─ Frames execute on render nodes
                            │
                            └─ execute_commands.py runs per frame
```

### Component Breakdown

#### 1. Main Entry Point (`__main__.py`)

Minimal entry point that imports and calls the main function:

**Purpose**: Provides the `cuecmd` command-line executable.

#### 2. Core Logic (`main.py`)

Contains the main application logic:

**Key Functions:**

- `parse_arguments()`: CLI argument parsing
- `count_commands()`: Count valid commands in file
- `get_frame_range()`: Calculate frame range from command count and chunk size
- `copy_to_temp()`: Copy command file to accessible location
- `create_outline()`: Generate OpenCue outline
- `main()`: Main execution flow

#### 3. Frame Executor (`execute_commands.py`)

Standalone script executed on each frame:

**Responsibilities:**
- Read command file
- Calculate which commands to execute based on frame number and chunk size
- Execute commands sequentially
- Report success/failure via exit code

**Example:**
- 100 commands, chunk_size=10
- Frame 1: Commands 1-10 (indices 0-9)
- Frame 2: Commands 11-20 (indices 10-19)
- Frame 10: Commands 91-100 (indices 90-99)

### Data Flow

```
Command File             Temporary Copy             Outline                 Frames
(user input)             (accessible to RQD)        (job spec)              (execution)

commands.txt    ─────>   /tmp/cuecmd_*/      ─────>  Shell Layer    ─────>  Frame 1: Cmds 1-10
  cmd 1                  commands.cmds               Range: 1-10            Frame 2: Cmds 11-20
  cmd 2                                              Chunk: 10              ...
  ...                                                Cores: 4               Frame 10: Cmds 91-100
  cmd 100                                            Memory: 8GB
```

## Development Setup

### Prerequisites

- Python 3.7 or higher
- OpenCue repository cloned
- Virtual environment recommended

### Setup Steps

```bash
# 1. Clone repository
git clone https://github.com/<username>/OpenCue.git
cd OpenCue

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install ./proto
pip install ./pycue
pip install ./pyoutline

# 4. Install cuecmd in editable mode with dev dependencies
pip install -e ./cuecmd[dev]
```

## Testing

### Test Organization

Cuecmd has three types of tests:

#### 1. Unit Tests

**Location**: `tests/test_main.py`, `tests/test_execute_commands.py`

**Purpose**: Test individual functions in isolation

#### 2. Integration Workflow Tests

**Location**: `tests/test_integration_workflows.py`

**Purpose**: Test complete workflows end-to-end

#### 3. Granular Integration Tests

**Location**: `tests/integration_tests.py`

**Purpose**: Test specific workflow scenarios organized by category

**Categories**:
- Command file processing
- Chunking workflows
- Outline creation
- Resource allocation
- Job metadata
- Error handling
- Pretend mode
- Pause mode
- Command execution

### Running Tests

**All tests:**

```bash
pytest
```

**With coverage:**

```bash
pytest --cov=cuecmd --cov-report=term-missing --cov-report=html
```

**Specific test file:**

```bash
pytest tests/test_main.py
```

**Specific test class:**

```bash
pytest tests/test_main.py::TestParseArguments
```

**Specific test:**

```bash
pytest tests/test_main.py::TestParseArguments::test_default_values
```

**Verbose output:**

```bash
pytest -v
```

**Stop on first failure:**

```bash
pytest -x
```

## Troubleshooting

### Common Development Issues

**Issue: Tests fail with import errors**

```
ModuleNotFoundError: No module named 'cuecmd'
```

**Solution**: Install cuecmd in editable mode:

```bash
pip install -e ./cuecmd
```

**Issue: Pylint fails with unknown module**

```
E0401: Unable to import 'outline'
```

**Solution**: Install dependencies:

```bash
pip install ./pycue ./pyoutline
```

**Issue: execute_commands.py not found during tests**

```
FileNotFoundError: execute_commands.py
```

**Solution**: Ensure tests run from correct directory or use absolute paths:

```python
script_dir = os.path.dirname(os.path.abspath(__file__))
execute_script = os.path.join(script_dir, "execute_commands.py")
```
