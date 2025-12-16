# OpenCue Rust modules

Opencue [Rust](https://www.rust-lang.org/) modules:

Project crates:
 * scheduler: Standalone scheduler service that replaces scheduling logic from Cuebot
 * rqd: rewrite of [OpenCue/rqd](https://github.com/AcademySoftwareFoundation/OpenCue/tree/master/rqd)
 * dummy-cuebot: A cli tool to interact with rqd's gRPC interface
 * opencue_proto: Wrapper around grpc's generated code for the project protobuf modules
 * monitoring-indexer: OpenCue monitoring event indexer (Kafka to Elasticsearch)

Sample configuration files are available in the `config/` directory:
 * `config/rqd.yaml` - RQD configuration
 * `config/rqd.fake_linux.yaml` - RQD configuration for simulating Linux on macOS
 * `config/monitoring-indexer.yaml` - Monitoring indexer configuration

## Build Instructions

Follow these steps to build and run the Rust-based RQD and Dummy Cuebot modules.

1. Install protobuf

**MacOS:**

Example on **macOS**, you can use Homebrew to install `protobuf`:
```bash
brew install protobuf
```

**Linux:**

Example on **Ubuntu**, you can use apt:
```bash
sudo apt-get install protobuf-compiler
```

2. Build the entire project
```bash
cd OpenCue/rust
cargo build -r
```
Building at release mode (`cargo build -r`) will compile the OS specific version of rqd, while
building at debug mode (`cargo build`) compiles both linux and macos versions. This is done to enable
developing the linux version on macos environments.

3. Start the `dummy-cuebot` report server:

```bash
target/release/dummy-cuebot report-server
```

4. In another terminal, start the RQD service:

Run with a simulation of a linux environment:
```bash
env OPENCUE_RQD_CONFIG=/PATH-TO-OPENCUE/OpenCue/rust/config/rqd.fake_linux.yaml target/release/openrqd
```

**Notes:**
- Ensure you have the correct path to your OpenCue configuration file.
- The example above uses a fake configuration file for demonstration purposes.
- The `OPENCUE_RQD_CONFIG` environment variable points to the configuration file for the RQD service.

5. Launch a test frame:

```bash
target/release/dummy-cuebot rqd-client launch-frame /PATH-TO-OPENCUE/Opencue/rust/crates/rqd/resources/test_scripts/memory_fork.sh
```

**Notes:**
- The `launch-frame` command starts a test frame using the specified script.
- The script `memory_fork.sh` is a sample script that simulates a rendering task for testing purposes.
- You should see output indicating that the frame has been launched and is being processed by the RQD service.
- You can monitor the logs in the terminal where you started the RQD service to see the progress and status of the frame execution.
- You can follow the logs for jobs created by dummy-cuebot on `/tmp/rqd/test_job.test_frame.rqlog`

## Running the Scheduler

The scheduler is a standalone service that handles job scheduling and frame dispatch. 

1. Run the scheduler with a configuration file:

```bash
env OPENCUE_SCHEDULER_CONFIG=/PATH-TO-OPENCUE/OpenCue/rust/config/scheduler.yaml target/release/cue-scheduler
```

Or specify scheduling parameters via command-line arguments:

```bash
target/release/cue-scheduler --facility <facility> --alloc_tags=<show:tag> --manual_tags=<tag>
```

**Notes:**
- Configuration is loaded from `config/scheduler.yaml` or the path specified by `OPENCUE_SCHEDULER_CONFIG`
- Command-line arguments override configuration file values
- The scheduler can be run in dry-run mode for testing (set `rqd.dry_run_mode: true` in config)

2. Run the scheduler using Docker:

```bash
docker build -f Dockerfile.scheduler -t opencue/scheduler .
docker run -v /path/to/config:/etc/cue-scheduler opencue/scheduler
```

**Notes:**
- Mount your configuration file to `/etc/cue-scheduler/scheduler.yaml` in the container
- See `Dockerfile.scheduler` for the container build configuration
