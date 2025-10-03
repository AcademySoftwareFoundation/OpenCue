# CueAdmin

CueAdmin is a command-line administration tool for OpenCue that provides full control over jobs, layers, frames, and hosts. It allows administrators to perform advanced management tasks such as setting priorities, killing jobs, or managing resource allocation. It's written in Python and provides a thin layer over the OpenCue Python API.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Running Tests](#running-tests)
- [Contributing](#contributing)

## Installation

Install CueAdmin with:

```bash
pip install opencue-cueadmin
```

For development:

```bash
# Clone repository and install with test dependencies
git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
cd OpenCue/cueadmin
pip install -e ".[dev]"
```

## Usage

Basic CueAdmin commands:

```bash
# List jobs
cueadmin -lj

# List job details
cueadmin -lji

# List hosts
cueadmin -lh

# Job management
cueadmin -pause JOB_NAME                    # Pause a job
cueadmin -unpause JOB_NAME                  # Resume a job
cueadmin -kill JOB_NAME                     # Kill a job (with confirmation)
cueadmin -retry JOB_NAME                    # Retry dead frames
cueadmin -priority JOB_NAME 100             # Set job priority
cueadmin -set-min-cores JOB_NAME 4.0        # Set minimum cores
cueadmin -set-max-cores JOB_NAME 16.0       # Set maximum cores
cueadmin -drop-depends JOB_NAME             # Drop job dependencies
```

For full documentation, see the [OpenCue Documentation](https://opencue.io/docs/).

## Running Tests

CueAdmin includes a comprehensive test suite with tests covering job management, allocation management, host operations, output formatting, and core functionality.

### Quick Start

```bash
# Install with test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=cueadmin --cov-report=term-missing
```

### Test Infrastructure

**Test Dependencies:**
- `pytest>=8.0.0` - Modern test framework
- `pytest-cov>=4.0.0` - Coverage reporting
- `pytest-mock>=3.10.0` - Enhanced mocking
- `mock>=4.0.0` - Core mocking library
- `pyfakefs>=5.2.3` - Filesystem mocking

**Test Types:**
- **Unit tests** - Function-level testing (`tests/test_*.py`)
- **Integration tests** - Command workflow testing (`tests/integration_tests.py`)
- **Job commands tests** - Job management operations (`tests/test_job_commands.py`)
- **Allocation tests** - Allocation management functionality (`tests/test_allocation_commands.py`)
- **Host commands tests** - Host operations (`tests/test_host_command.py`)
- **Subscription tests** - Subscription management (`tests/test_subscription_commands.py`)

### Running Tests

```bash
# Basic test run
pytest tests/

# Verbose output
pytest -v

# Run specific test file
pytest tests/test_allocation_commands.py

# Run with coverage and HTML report
pytest --cov=cueadmin --cov-report=html --cov-report=term-missing

# Use the convenience script
./run_tests.sh --coverage --html
```

### Coverage Reporting

```bash
# Terminal coverage report
pytest --cov=cueadmin --cov-report=term-missing

# HTML coverage report (generates htmlcov/ directory)
pytest --cov=cueadmin --cov-report=html

# XML coverage for CI/CD
pytest --cov=cueadmin --cov-report=xml
```

### Development Testing

**For contributors:**

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests with linting
pytest && pylint cueadmin tests

# Run tests across Python versions (requires tox)
tox

# Format code
black cueadmin tests
isort cueadmin tests
```

**CI/CD Integration:**

```bash
# In OpenCue root directory
./ci/run_python_tests.sh     # Includes cueadmin tests
./ci/run_python_lint.sh      # Includes cueadmin linting

# Run cueadmin tests specifically
cd cueadmin && python -m pytest tests/
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

## Contributing

We welcome contributions to CueAdmin! The project includes comprehensive development infrastructure:

### Development Setup

```bash
# Clone and setup
git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
cd OpenCue/cueadmin

# Install with development dependencies
pip install -e ".[dev]"
```

### Testing and Quality

```bash
# Run comprehensive test suite
pytest --cov=cueadmin --cov-report=term-missing

# Code formatting and linting
black cueadmin tests && isort cueadmin tests
pylint cueadmin tests

# Multi-environment testing
tox
```

### Project Quality

- **Comprehensive test coverage** with unit and integration tests
- **Modern testing infrastructure** using pytest, coverage, and CI/CD
- **Code quality tools** including pylint, black, and isort
- **Multi-Python version support** via tox
- **Docker support** for containerized development

For detailed contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

### Get Involved

- **Report Issues**: [GitHub Issues](https://github.com/AcademySoftwareFoundation/OpenCue/issues)
- **Contribute Code**: Submit pull requests with tests and documentation
- **Improve Documentation**: Help enhance tutorials and reference docs
- **Share Use Cases**: Contribute real-world examples and workflows
