# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Rust implementation of OpenCue components - a render farm management system. The project consists of three main crates:

- **rqd**: The main worker daemon that executes rendering tasks
- **dummy-cuebot**: A testing/development server for interacting with rqd
- **opencue-proto**: gRPC protocol definitions and generated code

## Build and Development Commands

### Prerequisites
```bash
# macOS
brew install protobuf

# Ubuntu/Debian
sudo apt-get install protobuf-compiler
```

### Build Commands
```bash
# Build entire project (release mode - OS-specific)
cargo build -r

# Build in debug mode (includes both Linux and macOS versions)
cargo build

# Build specific crate
cargo build -p rqd
cargo build -p dummy-cuebot
cargo build -p opencue-proto

# Run tests (unit tests only)
cargo test

# Run all tests including integration tests (requires database setup)
cargo test --features integration-tests

# Run only integration tests
cargo test --features integration-tests integration_tests

# Run clippy linting
cargo clippy -- -D warnings

# Format code
cargo fmt
```

### Running the System

1. **Start dummy-cuebot report server:**
```bash
target/release/dummy-cuebot report-server
```

2. **Start RQD service:**
```bash
# With fake Linux environment simulation
env OPENCUE_RQD_CONFIG=config/rqd.fake_linux.yaml target/release/openrqd

# With default config
target/release/openrqd
```

3. **Launch a test frame:**
```bash
target/release/dummy-cuebot rqd-client launch-frame crates/rqd/resources/test_scripts/memory_fork.sh
```

### Development Testing
```bash
# Run a single test
cargo test test_name

# Run tests with output
cargo test -- --nocapture

# Run tests for specific crate
cargo test -p rqd

# Check logs for test frames
tail -f /tmp/rqd/test_job.test_frame.rqlog
```

## Architecture Overview

### Core Components

**MachineMonitor** (`crates/rqd/src/system/machine.rs`):
- Central orchestrator for system monitoring and resource management
- Manages CPU/GPU reservations and NIMBY (user activity detection)
- Handles process cleanup and zombie detection

**FrameManager** (`crates/rqd/src/frame/manager.rs`):
- Manages frame lifecycle: validation, spawning, monitoring, cleanup
- Supports frame recovery after restarts via snapshot system
- Handles resource affinity and Docker containerization

**ReportClient** (`crates/rqd/src/report/report_client.rs`):
- Handles communication with Cuebot server
- Implements retry logic with exponential backoff
- Supports endpoint rotation for high availability

**RqdServant** (`crates/rqd/src/servant/rqd_servant.rs`):
- gRPC service implementation
- Handles incoming commands from Cuebot
- Delegates to appropriate managers

### Key Architectural Patterns

1. **Async/Await Throughout**: Full async architecture with Tokio runtime
2. **Resource Management**: Careful resource reservation and cleanup
3. **Platform Abstraction**: Separate Linux/macOS system implementations
4. **Configuration System**: YAML-based config with environment variable overrides
5. **Error Handling**: Uses `miette` for user-friendly error reporting

### Configuration

- **Default config location**: `~/.local/share/rqd.yaml`
- **Environment override**: `OPENCUE_RQD_CONFIG` environment variable
- **Environment prefix**: `OPENRQD_` for individual settings
- **Test config**: `config/rqd.fake_linux.yaml` for development

### Frame Execution Flow

1. **Validation**: Machine state, user permissions, resource availability
2. **Resource Reservation**: CPU cores and GPUs via CoreStateManager
3. **User Management**: Creates system users if needed
4. **Frame Spawning**: Launches in separate threads with optional Docker
5. **Monitoring**: Tracks execution, resource usage, process health
6. **Cleanup**: Releases resources and reports completion

### Development Notes

- **Resource Isolation**: Frames run in separate process groups
- **Container Support**: Optional Docker containerization via `containerized_frames` feature
- **Recovery System**: Restores running frames from snapshots after restarts
- **Kill Monitoring**: Tracks frame termination with forced kill capability
- **NIMBY Support**: Prevents frame execution when user is active

### Important Files

- `crates/rqd/src/main.rs`: RQD entry point and application setup
- `crates/rqd/src/config/config.rs`: Configuration structure definitions
- `crates/rqd/src/system/reservation.rs`: Resource reservation system
- `crates/dummy-cuebot/src/main.rs`: Testing server entry point
- `crates/opencue-proto/build.rs`: Protocol buffer build configuration

### Platform-Specific Code

- `crates/rqd/src/system/linux.rs`: Linux-specific system monitoring
- `crates/rqd/src/system/macos.rs`: macOS-specific system monitoring
- Build configuration automatically selects appropriate implementation

### Logging and Debugging

- **Log location**: Configurable via logging config
- **Log levels**: trace, debug, info, warn, error
- **Frame logs**: Individual frame execution logs in `/tmp/rqd/`
- **Structured logging**: Uses `tracing` crate for structured logging

## Code Review and Standards

### Rules

- When reviewing code check:
 - If all public methods are documented on their head comment
 - Verify for all changed functions if the preexisting documentation needs to be updated
 - Analyse possible race conditions introduced by the changes
 - Evaluate the overall quality of the change taking into consideration rust standards
 - Check for introduced panic conditions that are not properly documented
