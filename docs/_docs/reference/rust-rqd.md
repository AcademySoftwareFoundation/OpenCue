---
title: "Rust RQD"
nav_order: 40
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

## Installation

### Using Pre-built Binaries (Recommended)

The easiest way to get started with Rust RQD is to use the pre-built binaries from GitHub releases:

1. **Download the appropriate binary** for your platform from the [OpenCue releases page](https://github.com/AcademySoftwareFoundation/OpenCue/releases):

   - **Linux (GNU)**: `openrqd-VERSION-x86_64-unknown-linux-gnu`
   - **Linux (MUSL)**: `openrqd-VERSION-x86_64-unknown-linux-musl` (static binary, no dependencies)
   - **macOS (Intel)**: `openrqd-VERSION-x86_64-apple-darwin`
   - **macOS (Apple Silicon)**: `openrqd-VERSION-aarch64-apple-darwin`

2. **Make the binary executable**:
   ```bash
   chmod +x openrqd-VERSION-PLATFORM
   ```

3. **Optionally, rename and move to your PATH**:
   ```bash
   mv openrqd-VERSION-PLATFORM /usr/local/bin/openrqd
   ```

#### Available Binary Platforms

The following pre-built binaries are available for each OpenCue release:

| Platform | Filename Pattern | Description |
|----------|------------------|-------------|
| **Linux (GNU)** | `openrqd-VERSION-x86_64-unknown-linux-gnu` | Standard Linux binary, requires glibc |
| **Linux (MUSL)** | `openrqd-VERSION-x86_64-unknown-linux-musl` | Static binary with no runtime dependencies, ideal for containers |
| **macOS (Intel)** | `openrqd-VERSION-x86_64-apple-darwin` | Intel-based Mac systems |
| **macOS (Apple Silicon)** | `openrqd-VERSION-aarch64-apple-darwin` | M1/M2/M3 Mac systems |

**Which Linux binary should I use?**
- Use the **GNU** version for most Linux distributions (Ubuntu, Debian, RHEL, CentOS, etc.)
- Use the **MUSL** version for Alpine Linux, containers, or when you need a completely self-contained binary

### Building from Source

If you need to customize the build or contribute to development, you can build from source:

#### Prerequisites

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

#### Build Instructions

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

#### Build Features

The Rust RQD supports optional features through Cargo:

```bash
# Enable experimental containerized frames support
cargo build --release --features containerized_frames
```

## Running Rust RQD

### Quick Start with Pre-built Binary

1. **Download and prepare the binary** (as shown in the Installation section above)

2. **Create a basic configuration** (optional - RQD can run with defaults):
   ```bash
   mkdir -p ~/.config/openrqd
   # Copy sample config and modify as needed
   ```

3. **Run RQD**:
   ```bash
   # If you placed it in your PATH
   openrqd
   
   # Or run directly
   ./openrqd-VERSION-PLATFORM
   ```

### Local Development

1. **Start the dummy Cuebot server** (for testing, requires building from source):
   ```bash
   target/release/dummy-cuebot report-server
   ```

2. **Run RQD with configuration**:
   
   Using real configuration:
   ```bash
   # With pre-built binary
   openrqd
   
   # With source build
   target/release/openrqd
   ```
   
   Using fake Linux environment (for testing on macOS):
   ```bash
   env OPENCUE_RQD_CONFIG=/path/to/OpenCue/rust/config/rqd.fake_linux.yaml openrqd
   ```

3. **Launch a test frame** (requires building dummy-cuebot from source):
   ```bash
   target/release/dummy-cuebot rqd-client launch-frame \
     /path/to/OpenCue/rust/crates/rqd/resources/test_scripts/memory_fork.sh
   ```

### Production Deployment

1. **Install the binary**: Download the appropriate pre-built binary for your platform and install it:
   ```bash
   # Download from GitHub releases
   curl -L -o openrqd https://github.com/AcademySoftwareFoundation/OpenCue/releases/latest/download/openrqd-VERSION-PLATFORM
   chmod +x openrqd
   sudo mv openrqd /usr/local/bin/
   ```

2. **Configure RQD**: Edit `/etc/openrqd/rqd.yaml` or set `OPENCUE_RQD_CONFIG` environment variable
3. **Set Cuebot hostname**: Configure the Cuebot server location in your configuration file
4. **Run as a service**:

   **systemd (Linux):**
   ```bash
   sudo systemctl enable openrqd
   sudo systemctl start openrqd
   ```

   Use the unit file shipped in `rust/crates/rqd/resources/openrqd.service`, or make sure your own sets `KillMode=process` — see [Frame Recovery Across Restarts](#frame-recovery-across-restarts).

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
- Frame recovery across restarts (see below)
- Log-based exit-status rules (see below)

### Frame Recovery Across Restarts

RQD can be restarted — for an upgrade, or for a config change that is not live-reloadable — without losing the frames running on the host. Frames are spawned in their own session (`setsid`), so they outlive the RQD process, and every running frame is snapshotted to `runner.snapshots_path`. On startup RQD reads those snapshots back and re-attaches to the frames it left behind.

To report a frame's real outcome, RQD needs its exit status even though it is no longer the process's parent. Each frame therefore runs under a small wrapper script that records the exit code to an exit file in `runner.temp_path`, written with a write-then-rename so a recovering RQD can never read a half-written status. The wrapper also traps `SIGTERM`/`SIGINT`/`SIGHUP` and forwards them to the frame, so kill requests keep working for recovered frames.

What a restarted RQD does with each snapshot:

| State of the frame process | Reported to Cuebot |
| --- | --- |
| Still running | Re-attached: logs keep streaming, and the real exit status is reported when the frame finishes |
| Finished during the downtime | The real exit status, read from the exit file |
| Gone, leaving no exit file | Exit `1` / `SIGTERM`, so Cuebot reschedules the frame immediately instead of waiting for stuck-frame detection |

A frame is matched by pid **and** the process start time recorded when it was spawned, so a pid the OS recycled while RQD was down is never mistaken for the frame.

#### systemd requires `KillMode=process`

On Linux the whole feature depends on systemd not killing the frames along with RQD. With the default `KillMode=control-group`, `systemctl restart openrqd` sends `SIGTERM` (and, after `TimeoutSec`, `SIGKILL`) to every process in the unit's cgroup — the frames included — regardless of the session they run in. The shipped unit file (`rust/crates/rqd/resources/openrqd.service`) sets:

```ini
[Service]
KillMode=process
```

If you deploy your own unit file, carry that setting over, otherwise every restart kills the host's frames.

#### Remote service restart (`RestartRqdNow` / `RestartRqdIdle`)

The Monitor Hosts "Restart service now" / "Restart service when idle" actions use frame recovery to bounce the RQD service without killing frames: RQD exits with code `42` and relies on the unit's `Restart=on-failure` to be brought back up, after which it recovers the running frames from their snapshots. RQD refuses the request (`FAILED_PRECONDITION`) when it cannot work as advertised:

- no service supervisor is detected (systemd sets `INVOCATION_ID`; other supervised setups, e.g. a container with a restart policy, can opt in with `machine.allow_unsupervised_restart: true`),
- `runner.frame_recovery_enabled` is off while frames are running, or
- frames are running on Docker (`runner.run_on_docker`), where snapshot recovery is not supported yet.

If you deploy your own unit file, keep `Restart=on-failure` (or `always`) alongside `KillMode=process`, and note that `RestartSec` sets the length of the service outage.

#### Turning recovery off

The exit-file harness is the on/off switch for the feature:

```yaml
runner:
  # Default: true
  frame_recovery_enabled: false
```

With it off, frames run their command directly — no wrapper, no exit file — exactly as RQD behaved before recovery existed. Snapshots are still written and still re-attached, so a frame is never silently lost; it is simply reported as terminated (exit `1` / `SIGTERM`) instead of with its real exit status.

Behavior notes:

- **Live-reloaded**: the flag is re-read on the same interval as the exit-status rules (`log_exit_status_rules_reload_interval`) and consulted when a frame is launched, so it can be flipped on a busy host without restarting RQD. Frames already running keep the wrapper they were launched with, and their exit files are still honored on recovery.
- **Disable explicitly**: the default is `true`, so commenting the key out re-enables recovery at the next reload — set it to `false` rather than removing the line.
- **Windows**: the exit-file harness is disabled, so recovery is not available there.
- **Containerized frames**: recovery is not supported for frames run in Docker.

### Log-Based Exit-Status Rules

When a frame exits with a non-zero code, RQD can reclassify the failure by scanning the tail of the frame log against operator-defined regular expressions. On the first matching rule, RQD reports that rule's `exit_status` to Cuebot instead of the process's real exit code. This lets operators single out failures that deserve special dispatcher handling — for example a Houdini license shortage that exits `3` but should be retried differently — without the render wrapper having to translate the error into an exit code itself.

Configure it in the `runner` section of `rqd.yaml`:

```yaml
runner:
  # Number of trailing log lines scanned on failure (default: 50).
  # Set to 0, or leave log_exit_status_rules empty, to disable scanning.
  log_scan_last_lines: 50

  # Ordered regex -> exit-status rules. Evaluated top-to-bottom; first match wins.
  log_exit_status_rules:
    - name: "HOUDINI_LICENSE_ERROR"
      regex: "A usable license to run the application is installed but they are all in use"
      exit_status: 330
```

Behavior notes:

- **Disabled by default**: the feature does nothing until `log_exit_status_rules` is non-empty and `log_scan_last_lines` is greater than `0`.
- **Failures only**: successful frames (exit `0`) are never scanned, so there is no overhead on the happy path.
- **First match wins**: place more specific patterns above general ones.
- **`name`**: a human-readable identifier used only in RQD's log messages to make matches easy to trace.
- **Invalid regex is skipped** (with a warning) rather than disabling the whole rule set.
- **Efficient tail read**: the log tail is read backward in fixed-size chunks and stops once enough lines are collected — typically only a few kilobytes are read even for large logs, with a hard 1 MiB cap so a pathologically large log is never read in full.

#### Cuebot-side handling: automatic layer backoff

A substitute exit status is most useful when Cuebot is told what to do with it. Cuebot's
`dispatcher.layer_delay.rules` property (in `opencue.properties`) maps exit statuses to a number of
minutes; when a frame reports a configured status, Cuebot defers booking of the frame's whole layer
for that long (`layer.ts_start_after`) instead of consuming a retry or killing the frame — the
right behavior for a shared-resource shortage like a license pool, where every frame of the layer
would hit the same wall:

```properties
# Comma-separated exit_status:minutes pairs. Empty (default) disables the feature.
# Must agree with the exit statuses configured in rqd.yaml log_exit_status_rules.
dispatcher.layer_delay.rules=330:5
```

The exit status is an arbitrary number chosen in `rqd.yaml` and repeated in `opencue.properties`;
`330` is the conventional license-shortage code. Delayed layers are visible in CueGUI (tinted row
plus a *Start After* column) and in the `cuebot_layers_delayed` / `cuebot_layer_delays_total`
Prometheus metrics.

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
- **Multi-platform support**: Linux, MacOS and Windows 
- **Efficient resource monitoring**: Low-overhead CPU, memory, and disk tracking
- **Process management**: Reliable frame execution and monitoring
- **Automatic recovery**: Resilient error handling and retry mechanisms

### Advanced Features

- **Async architecture**: Built on Tokio for high-performance I/O
- **Configurable logging**: Structured logging with multiple output formats
- **NIMBY support**: Automatic idle detection and resource management
- **Signal handling**: Graceful shutdown and frame cleanup
- **Reservation system**: Resource allocation and management
- **Frame recovery across restarts**: Frames survive an RQD restart and are re-attached from on-disk snapshots, keeping their real exit status
- **Log-based exit-status rules**: Reclassify failed frames by matching their log output against configurable regex rules (e.g. flag license shortages)

### Experimental Features

- **Containerized frames**: Run frames in isolated Docker containers
- **Enhanced security**: Improved process isolation and resource limits

## Current Limitations

While the Rust RQD is production-ready for many use cases, be aware of:

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
