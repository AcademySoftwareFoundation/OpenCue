# RQD Module Overview

The `rqd` module is a core component of the OpenCue system, acting as the agent responsible for managing and executing rendering tasks on a host machine. This document serves as a high-level guide for navigating the `rqd` module's structure and understanding its primary functions.

## Project Structure

The `rqd` module is organized into several key components:

1. **Configuration (`config`)**
   - Manages the loading and application of configuration settings for the `rqd` module.
   - Handles environment variables and configuration files.

2. **Frame Management (`frame`)**
   - Responsible for managing rendering frames, including starting, monitoring, and completing tasks.
   - Includes support for running frames in Docker containers.
   - Tracks frame execution status and logs relevant information.

3. **System Monitoring (`system`)**
   - Contains platform-specific implementations for monitoring system resources and processes.
   - Provides information about CPU, memory, and other system metrics to ensure efficient resource allocation.

4. **GRPC Servants (`servant`)**
   - Implements the server-side logic for handling GRPC requests from clients.
   - Manages communication between the `rqd` module and other components in the OpenCue ecosystem.

5. **Reporting (`report`)**
   - Handles reporting of frame completion and system status to the OpenCue central server.
   - Implements retry mechanisms and backoff strategies to ensure reliable communication.

## Key Features

- **Task Execution**: The `rqd` module executes rendering tasks, utilizing available CPU and GPU resources while adhering to configured limits and constraints.
- **Resource Monitoring**: Continuously monitors the system to ensure optimal performance and resource utilization.
- **Container Support**: Offers experimental support for running tasks within Docker containers for enhanced isolation and compatibility.
- **Configurable Environment**: Supports a wide range of configuration options via environment variables and YAML configuration files.
- **Extensive Logging**: Provides detailed logs for debugging and understanding the execution flow and system behavior.
