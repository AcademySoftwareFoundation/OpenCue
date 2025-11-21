#!/bin/bash

# Check if memory argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <memory_in_gb>"
    echo "Example: $0 2.5  # Allocates approximately 2.5 GB"
    exit 1
fi

MEMORY_GB=$1

# Validate that the argument is a number
if ! [[ "$MEMORY_GB" =~ ^[0-9]+\.?[0-9]*$ ]]; then
    echo "Error: Memory argument must be a positive number"
    exit 1
fi

# Calculate number of elements needed
# Based on empirical testing, each bash array element consumes approximately 200 bytes
# This accounts for the value storage plus bash's internal overhead
# Convert GB to bytes: GB * 1024^3 / 200
ELEMENTS=$(awk "BEGIN {printf \"%.0f\", $MEMORY_GB * 1024 * 1024 * 1024 / 100}")

echo "Allocating approximately ${MEMORY_GB} GB of memory (${ELEMENTS} array elements)..."

# Function to allocate memory
allocate_memory() {
    local elements=$1
    local array

    echo "Process $$ starting memory allocation..."

    # Fill array with data (allocate 3 elements per iteration for 3x speed)
    for ((i=0; i<elements; i+=3)); do
        array[$i]=$i
        array[$((i+1))]=$((i+1))
        array[$((i+2))]=$((i+2))

        # Print progress every 10% for large allocations
        if [ $((i % (elements / 10))) -eq 0 ] && [ $i -gt 0 ]; then
            echo "Process $$: allocated $((i * 100 / elements))%"
        fi
    done

    echo "Process $$ allocated ~${MEMORY_GB} GB, sleeping..."
    # Sleep for 310 seconds to ensure memory is held until parent process completes
    sleep 310
}

# Main process allocates memory
echo "Parent process $$ starting..."

# Fork child process with memory allocation
echo "Forking child process..."
allocate_memory "$ELEMENTS" &
child_pid=$!
echo "Child process has PID: $child_pid"

echo "All processes running. Parent will wait before exiting."
sleep 300

# Clean up child processes
kill $child_pid 2>/dev/null
wait

echo "Script completed"
