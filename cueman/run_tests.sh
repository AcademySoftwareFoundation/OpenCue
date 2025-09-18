#!/bin/bash
# Script to run tests with various options

set -e

# Default values
COVERAGE=false
HTML=false
VERBOSE=false
TESTS=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
        *)
            TESTS="$TESTS $1"
            shift
            ;;
    esac
done

# Build the pytest command
CMD="python -m pytest"

if [ "$VERBOSE" = true ]; then
    CMD="$CMD -vv"
fi

if [ "$COVERAGE" = true ]; then
    CMD="$CMD --cov=cueman --cov-report=term-missing"

    if [ "$HTML" = true ]; then
        CMD="$CMD --cov-report=html"
    fi

    CMD="$CMD --cov-report=xml"
fi

# Add test paths if specified, otherwise run all tests
if [ -n "$TESTS" ]; then
    CMD="$CMD $TESTS"
else
    CMD="$CMD tests/"
fi

echo "Running: $CMD"
echo "----------------------------------------"
$CMD
