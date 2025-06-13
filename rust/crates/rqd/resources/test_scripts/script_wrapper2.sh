#!/bin/bash

# Default output file
OUTPUT_FILE="command_exit_code.txt"

# Function to write exit code and terminate
# handle_signal() {
#     local signal=$1
#     local sig_name=${signal#SIG}
#     echo "Exit code: $sig_name" > "$OUTPUT_FILE"
#     exit $sig_name
# }

# # Handle signals
# trap 'handle_signal SIGTERM' SIGTERM
# trap 'handle_signal SIGHUP' SIGHUP
# trap 'handle_signal SIGINT' SIGINT

# # Check if a command was provided
# if [ $# -eq 0 ]; then
#     echo "Error: No command specified."
#     echo "Usage: $0 [command]"
#     write_exit_code_and_exit 1
# fi

# Execute the command
eval "$@"

# Capture the exit code
# COMMAND_EXIT_CODE=$?

# Write the exit code to file
# write_exit_code_and_exit $COMMAND_EXIT_CODE
