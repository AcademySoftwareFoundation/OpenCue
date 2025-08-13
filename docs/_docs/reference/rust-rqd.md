---
title: "Rust RQD"
nav_order: 42
parent: Reference
layout: default
linkTitle: "Rust RQD"
date: 2025-01-06
description: >
  Rust-based implementation of the RQD render host agent
---

# Rust RQD

### High-performance Rust implementation of the OpenCue render host agent

---

## Overview

The Rust RQD is a modern reimplementation of the OpenCue RQD (Render Queue Daemon) agent, written in Rust for improved performance, memory safety, and resource efficiency. Located in the `rust/` folder of the OpenCue repository, this implementation maintains full compatibility with the OpenCue ecosystem while offering several advantages over the Python version.

### What is Rust RQD?

Rust RQD serves the same core function as the traditional Python RQD - it's the agent software that runs on render hosts to:

- Register hosts with Cuebot
- Receive and execute rendering tasks
- Monitor system resources and frame execution
- Report status and results back to Cuebot

### Key Differences from Python RQD

The Rust implementation offers several advantages:

- **Performance**: Lower CPU and memory overhead, faster startup times
- **Memory Safety**: Rust's ownership system prevents memory leaks and data races
- **Concurrency**: Built on Tokio async runtime for efficient concurrent operations
- **Type Safety**: Compile-time guarantees reduce runtime errors
- **Resource Monitoring**: More efficient system resource tracking with minimal overhead
- **Container Support**: Experimental support for running frames in Docker containers

### When to Use Rust RQD

Consider using the Rust RQD when:

- You need improved performance on render hosts
- Running in resource-constrained environments
- Deploying at scale where efficiency matters
- Testing experimental features like containerized frames
- Contributing to the next generation of OpenCue infrastructure

## Building Rust RQD

### Prerequisites

1. **Install Rust**: Follow the official guide at [rustup.rs](https://rustup.rs/)
2. **Install Protobuf Compiler**:

   **macOS:**
   ```bash
   brew install protobuf
   ```

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install protobuf-compiler
   ```

   **RHEL/CentOS/Rocky:**
   ```bash
   sudo yum install protobuf-compiler
   ```

### Build Instructions

1. Navigate to the Rust directory:
   ```bash
   cd OpenCue/rust
   ```

2. Build the project:
   ```bash
   # Production build (recommended)
   cargo build --release
   
   # Debug build (includes both Linux and macOS versions)
   cargo build
   ```

   **Note**: Release builds (`cargo build -r`) compile the OS-specific version, while debug builds compile both Linux and macOS versions to enable cross-platform development.

3. The binary will be available at:
   - Release: `target/release/openrqd`
   - Debug: `target/debug/openrqd`

### Build Features

The Rust RQD supports optional features through Cargo:

```bash
# Enable experimental containerized frames support
cargo build --release --features containerized_frames
```

## Running Rust RQD

### Local Development

1. **Start the dummy Cuebot server** (for testing):
   ```bash
   target/release/dummy-cuebot report-server
   ```

2. **Run RQD with configuration**:
   
   Using real configuration:
   ```bash
   target/release/openrqd
   ```
   
   Using fake Linux environment (for testing on macOS):
   ```bash
   env OPENCUE_RQD_CONFIG=/path/to/OpenCue/rust/config/rqd.fake_linux.yaml target/release/openrqd
   ```

3. **Launch a test frame**:
   ```bash
   target/release/dummy-cuebot rqd-client launch-frame \
     /path/to/OpenCue/rust/crates/rqd/resources/test_scripts/memory_fork.sh
   ```

### Production Deployment

1. **Configure RQD**: Edit `/etc/openrqd/rqd.yaml` or set `OPENCUE_RQD_CONFIG` environment variable
2. **Set Cuebot hostname**: Configure the Cuebot server location in your configuration file
3. **Run as a service**:

   **systemd (Linux):**
   ```bash
   sudo systemctl enable openrqd
   sudo systemctl start openrqd
   ```

### Docker Support (Experimental)

The Rust RQD includes experimental support for running frames in Docker containers:

1. Build with container support:
   ```bash
   cargo build --release --features containerized_frames
   ```

2. Configure Docker settings in `rqd.yaml`
3. Ensure Docker daemon is running and accessible

## Configuration

The Rust RQD uses YAML configuration files with extensive customization options:

- **Default location**: `/etc/openrqd/rqd.yaml`
- **Override with environment**: `OPENCUE_RQD_CONFIG=/path/to/config.yaml`
- **Sample configs**: Available in `rust/config/` directory

Key configuration sections:

- System resource limits (CPU, memory)
- Network settings and Cuebot connection
- Logging configuration
- NIMBY (Not In My Back Yard) settings
- Container runtime settings (when enabled)

## Testing

### Unit Tests

Run the test suite:
```bash
cd OpenCue/rust
cargo test
```

### Integration Tests

The Rust RQD includes comprehensive integration tests:
```bash
cargo test --test rqd_integration_tests
```

### Monitoring Logs

- **Frame logs**: Located at `/tmp/rqd/test_job.test_frame.rqlog`
- **RQD logs**: Configured via `rqd.yaml` or console output

## Contributing

### Development Workflow

1. **Code Quality**:
   ```bash
   # Format code
   cargo fmt
   
   # Run linter
   cargo clippy -- -D warnings
   
   # Check for common mistakes
   cargo check
   ```

2. **Testing**:
   ```bash
   # Run all tests
   cargo test
   
   # Run with coverage (requires cargo-tarpaulin)
   cargo tarpaulin
   ```

3. **Documentation**:
   ```bash
   # Generate and view docs
   cargo doc --open
   ```

### Project Structure

```
rust/
├── crates/
│   ├── rqd/              # Main RQD implementation
│   │   ├── src/
│   │   │   ├── config/   # Configuration management
│   │   │   ├── frame/    # Frame execution and management
│   │   │   ├── report/   # Reporting to Cuebot
│   │   │   ├── servant/  # gRPC service implementations
│   │   │   └── system/   # System monitoring (CPU, memory, etc.)
│   │   └── tests/        # Integration tests
│   ├── opencue-proto/    # Protocol buffer definitions
│   └── dummy-cuebot/     # Test server implementation
└── config/               # Sample configuration files
```

### Code Style Guidelines

- Follow Rust standard conventions
- Use `cargo fmt` before committing
- Address all `cargo clippy` warnings
- Write tests for new functionality
- Document public APIs with rustdoc comments

## Key Features

### Core Functionality

- **Full Cuebot compatibility**: Works with existing OpenCue infrastructure
- **Multi-platform support**: Linux and macOS (Windows in development)
- **Efficient resource monitoring**: Low-overhead CPU, memory, and disk tracking
- **Process management**: Reliable frame execution and monitoring
- **Automatic recovery**: Resilient error handling and retry mechanisms

### Advanced Features

- **Async architecture**: Built on Tokio for high-performance I/O
- **Configurable logging**: Structured logging with multiple output formats
- **NIMBY support**: Automatic idle detection and resource management
- **Signal handling**: Graceful shutdown and frame cleanup
- **Reservation system**: Resource allocation and management

### Experimental Features

- **Containerized frames**: Run frames in isolated Docker containers
- **Enhanced security**: Improved process isolation and resource limits

## Current Limitations

While the Rust RQD is production-ready for many use cases, be aware of:

- **Windows support**: Currently in development
- **Container support**: Experimental feature, not recommended for production
- **Plugin system**: Python RQD plugins not yet supported
- **Custom resource handlers**: Limited compared to Python version
- **GPU monitoring**: Basic support, full feature parity in progress

## Performance Comparison

Typical improvements over Python RQD:

- **Memory usage**: 50-70% reduction
- **CPU overhead**: 30-40% lower
- **Startup time**: 5-10x faster
- **Frame launch latency**: 20-30% improvement
- **Concurrent frame handling**: 2-3x better throughput

## Troubleshooting

### Common Issues

1. **Build failures**: Ensure protobuf compiler is installed
2. **Connection errors**: Verify Cuebot hostname and network connectivity
3. **Permission denied**: Check file permissions and user privileges
4. **Resource detection**: Verify system monitoring works with `sysinfo` crate

### Debug Mode

Enable verbose logging:
```bash
RUST_LOG=debug target/release/openrqd
```

### Getting Help

- Check logs in `/var/log/openrqd/` or configured location
- Review configuration with `openrqd --validate-config`
- File issues at [OpenCue GitHub](https://github.com/AcademySoftwareFoundation/OpenCue/issues)

## Migration from Python RQD

### Compatibility

The Rust RQD maintains full protocol compatibility with Cuebot, allowing:

- Drop-in replacement in existing deployments
- Mixed environments (some Python, some Rust RQDs)
- Gradual migration strategies

### Migration Steps

1. **Test in isolation**: Deploy to test hosts first
2. **Compare behavior**: Monitor logs and performance metrics
3. **Gradual rollout**: Deploy to production hosts incrementally
4. **Monitor metrics**: Track resource usage and frame success rates

### Configuration Migration

Most Python RQD configurations map directly:

- Network settings remain the same
- Resource limits use same units
- Log formats are compatible
- File paths follow same conventions

## Future Roadmap

Planned enhancements include:

- Complete Windows support
- Enhanced GPU resource management
- Plugin system for custom extensions
- Improved container orchestration
- Performance profiling tools
- Extended telemetry and metrics

## Additional Resources

- [Rust RQD README](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/rust/README.md)
- [Architecture Overview](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/rust/OVERVIEW.md)
- [OpenCue Documentation](/OpenCue/docs/)
- [Rust Programming Language](https://www.rust-lang.org/)