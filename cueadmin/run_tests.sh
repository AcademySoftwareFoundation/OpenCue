#!/bin/bash
#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# Script to run cueadmin tests with various options

set -e

# Default values
COVERAGE=false
HTML=false
VERBOSE=false
TESTS=""
QUICK=false

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to display help
show_help() {
    echo "Usage: ./run_tests.sh [OPTIONS] [TEST_PATHS]"
    echo ""
    echo "Run cueadmin tests with various options."
    echo ""
    echo "Options:"
    echo "  -c, --coverage    Enable coverage reporting"
    echo "  -h, --html        Generate HTML coverage report (implies --coverage)"
    echo "  -v, --verbose     Run tests in verbose mode"
    echo "  -q, --quick       Run tests quickly (no coverage, parallel execution)"
    echo "  --help            Show this help message and exit"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh                           # Run all tests"
    echo "  ./run_tests.sh --coverage                # Run with coverage"
    echo "  ./run_tests.sh --html                    # Run with HTML coverage report"
    echo "  ./run_tests.sh tests/test_output.py      # Run specific test file"
    echo "  ./run_tests.sh -v tests/                 # Run all tests verbosely"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_help
            ;;
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --html|-h)
            HTML=true
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --quick|-q)
            QUICK=true
            COVERAGE=false
            shift
            ;;
        *)
            TESTS="$TESTS $1"
            shift
            ;;
    esac
done

# Check if pytest is installed
if ! python -m pytest --version &> /dev/null; then
    print_error "pytest is not installed. Please install it with: pip install pytest"
    exit 1
fi

# Check if pytest-cov is installed when coverage is requested
if [ "$COVERAGE" = true ]; then
    if ! python -c "import pytest_cov" &> /dev/null; then
        print_warning "pytest-cov is not installed. Installing it now..."
        pip install pytest-cov
    fi
fi

# Build the pytest command
CMD="python -m pytest"

# Add verbose flag if requested
if [ "$VERBOSE" = true ]; then
    CMD="$CMD -vv"
else
    CMD="$CMD -v"
fi

# Add quick mode flags
if [ "$QUICK" = true ]; then
    CMD="$CMD -n auto --dist loadgroup"
    # Check if pytest-xdist is installed for parallel execution
    if ! python -c "import xdist" &> /dev/null; then
        print_warning "pytest-xdist not installed, falling back to sequential execution"
        CMD="python -m pytest -v"
    fi
fi

# Add coverage flags if requested
if [ "$COVERAGE" = true ]; then
    CMD="$CMD --cov=cueadmin --cov-report=term-missing"

    if [ "$HTML" = true ]; then
        CMD="$CMD --cov-report=html"
        print_status "HTML coverage report will be generated in htmlcov/"
    fi

    CMD="$CMD --cov-report=xml"
fi

# Add test paths if specified, otherwise run all tests
if [ -n "$TESTS" ]; then
    CMD="$CMD $TESTS"
else
    CMD="$CMD tests/"
fi

# Display test environment info
print_status "Python version: $(python --version 2>&1)"
print_status "pytest version: $(python -m pytest --version 2>&1 | head -1)"
print_status "Test directory: $(pwd)"

# Run the tests
echo ""
print_status "Running: $CMD"
echo "=========================================="
$CMD
TEST_EXIT_CODE=$?

# Print summary
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_status "All tests passed successfully!"

    if [ "$COVERAGE" = true ]; then
        echo ""
        print_status "Coverage reports generated:"
        [ -f coverage.xml ] && echo "  - XML: coverage.xml"
        [ -d htmlcov ] && echo "  - HTML: htmlcov/index.html"
    fi
else
    print_error "Some tests failed. Exit code: $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE
