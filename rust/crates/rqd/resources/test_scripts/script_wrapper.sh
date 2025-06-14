#!/bin/bash

wait_for_output() {
    echo "Writing output... $1"

    # Wait for the command to complete
    wait $command_pid
    exit_code=$1

    # Write the exit code to the specified file
    echo $exit_code > output_signal.txt
    exit $exit_code
}

# Function to handle signals
handle_signal() {
    local signal=$1
    echo "Forwarding $signal signal to child process..." >&2
    # Forward the signal to the child process if it exists
    if [ -n "$command_pid" ] && kill -0 $command_pid 2>/dev/null; then
        kill -$signal $command_pid
        echo "waiting on child process... $command_pid"
        wait_for_output $signal
    fi
    # Don't exit - let the script continue to monitor the child process
}

# Set up signal handling
trap 'handle_signal TERM' SIGTERM
trap 'handle_signal INT' SIGINT
trap 'handle_signal HUP' SIGHUP

# Start the command and get its PID
eval "$1"
exit_code=$?

# Capture the pid of the command spawn by the eval expression
command_pid=$!

wait_for_output $exit_code
