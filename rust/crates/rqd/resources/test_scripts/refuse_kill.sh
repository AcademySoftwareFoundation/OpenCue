#!/bin/bash
# Echo counter every 10 seconds and trap SIGTERM
counter=0

# Function to handle SIGTERM
handle_signal() {
    echo "Received $1. Not Exiting..."
    counter=0
    while true; do
        echo "Killed Counter: $counter"
        counter=$((counter + 1))
        sleep 10

        if [ $counter -ge 12 ]; then
            echo "Reached 2 minutes runtime. Exiting..."
            exit 0
        fi
    done
    exit 0
}

# Set up trap for SIGTERM
trap 'handle_signal SIGTERM' SIGTERM
trap 'handle_signal SIGHUP' SIGHUP
trap 'handle_signal SIGINT' SIGINT
trap 'handle_signal SIGQUIT' SIGQUIT
trap 'handle_signal SIGILL' SIGILL
trap 'handle_signal SIGTRAP' SIGTRAP
trap 'handle_signal SIGABRT' SIGABRT
trap 'handle_signal SIGBUS' SIGBUS
trap 'handle_signal SIGFPE' SIGFPE
trap 'handle_signal SIGUSR1' SIGUSR1
trap 'handle_signal SIGSEGV' SIGSEGV
trap 'handle_signal SIGUSR2' SIGUSR2
trap 'handle_signal SIGPIPE' SIGPIPE
trap 'handle_signal SIGALRM' SIGALRM
trap 'handle_signal SIGTERM' SIGTERM
trap 'handle_signal EXIT' EXIT


# Main loop
while true; do
    echo "Counter: $counter"
    counter=$((counter + 1))
    sleep 10
done
