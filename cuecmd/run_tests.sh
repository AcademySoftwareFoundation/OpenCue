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

# Script for running cuecmd tests

set -e

# Parse command line arguments
COVERAGE=false
HTML=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --html)
            HTML=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--coverage] [--html]"
            exit 1
            ;;
    esac
done

# Install test dependencies if needed
pip install -e ".[test]" > /dev/null 2>&1 || true

# Run tests
if [ "$COVERAGE" = true ]; then
    if [ "$HTML" = true ]; then
        echo "Running tests with coverage (HTML report)..."
        pytest --cov=cuecmd --cov-report=html --cov-report=term-missing tests/
        echo "HTML coverage report generated in htmlcov/"
    else
        echo "Running tests with coverage..."
        pytest --cov=cuecmd --cov-report=term-missing tests/
    fi
else
    echo "Running tests..."
    pytest tests/
fi

echo "Tests completed successfully!"
