#!/bin/bash

# Function to allocate memory (approximately 5MB)
allocate_memory() {
    # Create an array and fill it with data (each element is 8 bytes)
    local array
    local array2
    # 5MB ≈ 5,000,000 bytes ÷ 8 bytes per element ≈ 625,000 elements
    for ((i=0; i<625000; i++)); do
        array[$i]=$i
    done
    sleep 10
    for ((i=0; i<625000; i++)); do
        array2[$i]=$i
    done

    # Keep the process running
    echo "Child process $$ allocated ~5MB, sleeping..."
    sleep 60  # Sleep for 1 minute to keep memory allocated
}

# Main process allocates memory
echo "Parent process $$ starting..."
main_array=()

# Parent process allocates memory (approximately 10MB)
echo "Parent allocating ~10MB memory..."
for ((i=0; i<1250000; i++)); do
    main_array[$i]=$i
done
sleep 10

# Fork first child process
echo "Forking first child process..."
allocate_memory &
child1_pid=$!
echo "First child process has PID: $child1_pid"

# Fork second child process
echo "Forking second child process..."
allocate_memory &
child2_pid=$!
echo "Second child process has PID: $child2_pid"

echo "All processes running. Parent will wait before exiting."
sleep 60

# Clean up child processes
kill $child1_pid $child2_pid 2>/dev/null
wait

echo "Script completed"
