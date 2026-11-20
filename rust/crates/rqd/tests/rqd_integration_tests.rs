// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

use std::io::{BufRead, BufReader, Read};
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::mpsc::{self, Receiver, RecvTimeoutError, Sender};
use std::sync::Once;
use std::thread;
use std::time::Duration;
use std::{
    net::{TcpListener, TcpStream},
    time::Instant,
};
use tempfile::TempDir;
use tokio::time::sleep;

static INIT: Once = Once::new();
static TEST_MUTEX: std::sync::Mutex<()> = std::sync::Mutex::new(());

/// Ensure dummy-cuebot is built before running tests
fn ensure_dummy_cuebot_built() {
    INIT.call_once(|| {
        println!("Building dummy-cuebot binary for tests...");
        let output = Command::new("cargo")
            .args(["build", "-p", "dummy-cuebot", "-r"])
            .current_dir("../../") // Go to workspace root
            .output()
            .expect("Failed to execute cargo build for dummy-cuebot");

        if !output.status.success() {
            panic!(
                "Failed to build dummy-cuebot: {}",
                String::from_utf8_lossy(&output.stderr)
            );
        }
        println!("Successfully built dummy-cuebot binary");
    });
}

/// Helper function to determine the correct binary path based on build profile
fn get_binary_path(binary_name: &str) -> String {
    ensure_dummy_cuebot_built();

    let binary_name = if cfg!(windows) {
        format!("{}.exe", binary_name)
    } else {
        binary_name.to_string()
    };

    // Check if we're running in debug or release mode by looking for the binaries
    let release_path = format!("../../target/release/{}", binary_name);
    let debug_path = format!("../../target/debug/{}", binary_name);

    // First check if release binary exists
    if std::path::Path::new(&release_path).exists() {
        release_path
    } else if std::path::Path::new(&debug_path).exists() {
        debug_path
    } else {
        // Default to debug path as that's what tests typically use
        debug_path
    }
}

fn machine_paths() -> (&'static str, &'static str, &'static str, &'static str) {
    if cfg!(windows) {
        (
            "now_available_on_windows",
            "now_available_on_windows",
            "now_available_on_windows",
            "now_available_on_windows",
        )
    } else {
        (
            "../../crates/rqd/resources/cpuinfo/cpuinfo_srdsvr09_48-12-4",
            "../../crates/rqd/resources/distro-release/rocky",
            "../../crates/rqd/resources/proc/stat",
            "../../crates/rqd/resources/proc/loadavg",
        )
    }
}

fn quoted_if_needed(path: &str) -> String {
    if path.contains(' ') {
        format!("\"{}\"", path)
    } else {
        path.to_string()
    }
}

fn yaml_path(path: &Path) -> String {
    path.to_string_lossy().replace('\\', "/")
}

// --- OS-specific command helpers ---

fn sleep_and_echo_cmd(message: &str) -> String {
    if cfg!(windows) {
        format!("ping -n 2 127.0.0.1 > NUL & echo {}", message)
    } else {
        format!("sleep 1 && echo '{}'", message)
    }
}

fn env_echo_cmd() -> String {
    if cfg!(windows) {
        "echo %TEST_VAR% %ANOTHER_VAR%".to_string()
    } else {
        "echo $TEST_VAR $ANOTHER_VAR".to_string()
    }
}

fn echo_cmd(message: &str) -> String {
    if cfg!(windows) {
        format!("echo {}", message)
    } else {
        format!("echo '{}'", message)
    }
}

fn memory_fork_script_path() -> &'static str {
    if cfg!(windows) {
        "../../crates/rqd/resources/test_scripts/memory_fork.cmd"
    } else {
        "../../crates/rqd/resources/test_scripts/memory_fork.sh"
    }
}

fn timeout_secs() -> u64 {
    if cfg!(windows) {
        20
    } else {
        15
    }
}

fn wait_millis() -> u64 {
    if cfg!(windows) {
        10000
    } else {
        8000
    }
}

/// Reads a child's stdout and stderr on background threads and forwards each line over a
/// channel. Draining both pipes keeps the child from blocking on a full pipe, and the channel
/// lets callers wait with a deadline. Lines are still drained after the receiver is dropped.
fn stream_output(child: &mut Child) -> Receiver<String> {
    let (tx, rx) = mpsc::channel();
    if let Some(stdout) = child.stdout.take() {
        forward_lines(stdout, tx.clone());
    }
    if let Some(stderr) = child.stderr.take() {
        forward_lines(stderr, tx);
    }
    rx
}

fn forward_lines<R: Read + Send + 'static>(pipe: R, tx: Sender<String>) {
    thread::spawn(move || {
        for line in BufReader::new(pipe).lines().map_while(Result::ok) {
            let _ = tx.send(line);
        }
    });
}

/// Collects whatever a child has written, waiting at most a second for each further line.
fn collect_output(output: &Receiver<String>) -> String {
    let mut collected = String::new();
    while let Ok(line) = output.recv_timeout(Duration::from_secs(1)) {
        collected.push_str(&line);
        collected.push('\n');
    }
    collected
}

/// Watches dummy-cuebot's output for frame completion reports until `expected_completions`
/// arrive or `timeout_secs` pass, whichever comes first, then kills the server.
fn monitor_server_output(
    mut child: Child,
    output: Receiver<String>,
    expected_completions: usize,
    timeout_secs: u64,
) -> (bool, String) {
    let deadline = Instant::now() + Duration::from_secs(timeout_secs);
    let mut all_output = String::new();
    let mut completion_count = 0;
    let mut saw_status_report = false;
    let mut line_count = 0;

    while completion_count < expected_completions {
        let line = match output.recv_timeout(deadline.saturating_duration_since(Instant::now())) {
            Ok(line) => line,
            Err(RecvTimeoutError::Timeout) => {
                println!(
                    "Timeout reached waiting for frame completions ({}s)",
                    timeout_secs
                );
                break;
            }
            Err(RecvTimeoutError::Disconnected) => {
                println!("dummy-cuebot closed its output before all completions arrived");
                break;
            }
        };

        line_count += 1;
        all_output.push_str(&line);
        all_output.push('\n');

        if line.contains("RqdReport:") {
            println!(
                "Report line {}: {}",
                line_count,
                if line.len() > 150 {
                    &line[..150]
                } else {
                    &line
                }
            );
        }

        if line.contains("report_running_frame_completion") {
            completion_count += 1;
            if line.contains("exit_status: 0") {
                println!(
                    "Found successful frame completion {}/{}",
                    completion_count, expected_completions
                );
            } else if let Some(pos) = line.find("exit_status:") {
                let status_part = &line[pos..];
                if let Some(end) = status_part.find(',') {
                    println!(
                        "Found frame completion {}/{} with {}",
                        completion_count,
                        expected_completions,
                        &status_part[..end]
                    );
                }
            }
        }

        if line.contains("report_status") && line.contains("frames: [") {
            saw_status_report = true;
            println!("Found status report with running frames");
        }
    }

    let _ = child.kill();
    let _ = child.wait();
    let success = completion_count >= expected_completions;
    println!(
        "Final results: {} lines, {} completions out of {} expected, saw status report: {}",
        line_count, completion_count, expected_completions, saw_status_report
    );
    (success, all_output)
}

fn wait_for_port_open(
    child: &mut Child,
    output: &Receiver<String>,
    port: u16,
    label: &str,
    timeout_secs: u64,
) {
    let start = Instant::now();
    loop {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return;
        }

        if let Ok(Some(status)) = child.try_wait() {
            panic!(
                "{} exited early with status {}.\noutput:\n{}",
                label,
                status,
                collect_output(output)
            );
        }

        if start.elapsed().as_secs() >= timeout_secs {
            let _ = child.kill();
            let _ = child.wait();
            panic!(
                "{} did not open port {} within {}s.\noutput:\n{}",
                label,
                port,
                timeout_secs,
                collect_output(output)
            );
        }

        thread::sleep(Duration::from_millis(200));
    }
}

fn get_free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .expect("Failed to bind to an ephemeral port")
        .local_addr()
        .expect("Failed to read local_addr")
        .port()
}

fn get_two_free_ports() -> (u16, u16) {
    let first = get_free_port();
    let mut second = get_free_port();
    while second == first {
        second = get_free_port();
    }
    (first, second)
}

fn integration_test_lock() -> std::sync::MutexGuard<'static, ()> {
    TEST_MUTEX.lock().unwrap_or_else(|err| err.into_inner())
}

// --- Test environment setup ---

struct TestEnv {
    temp_dir: TempDir,
    dummy_server: Child,
    dummy_output: Receiver<String>,
    openrqd: Child,
    rqd_port: u16,
    config_path: std::path::PathBuf,
}

fn make_test_config(
    temp_dir: &TempDir,
    rqd_port: u16,
    cuebot_port: u16,
    monitor_interval: &str,
    worker_threads: u32,
) -> String {
    let temp_dir_str = yaml_path(temp_dir.path());
    let tmp_dir_str = yaml_path(&temp_dir.path().join("tmp"));
    let snapshots_dir_str = yaml_path(&temp_dir.path().join("snapshots"));
    let (cpuinfo_path, distro_release_path, proc_stat_path, proc_loadavg_path) = machine_paths();

    format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: false

machine:
  monitor_interval: {}
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: {}
  temp_path: "{}"
  cpuinfo_path: "{}"
  distro_release_path: "{}"
  proc_stat_path: "{}"
  proc_loadavg_path: "{}"

grpc:
  rqd_port: {}
  cuebot_endpoints: ["127.0.0.1:{}"]

runner:
  run_on_docker: false
  default_uid: 1000
  temp_path: "{}"
  snapshots_path: "{}"
"#,
        temp_dir_str,
        monitor_interval,
        worker_threads,
        tmp_dir_str,
        cpuinfo_path,
        distro_release_path,
        proc_stat_path,
        proc_loadavg_path,
        rqd_port,
        cuebot_port,
        tmp_dir_str,
        snapshots_dir_str
    )
}

fn setup_test_env(monitor_interval: &str, worker_threads: u32) -> TestEnv {
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");
    let (rqd_port, cuebot_port) = get_two_free_ports();

    let test_config = make_test_config(
        &temp_dir,
        rqd_port,
        cuebot_port,
        monitor_interval,
        worker_threads,
    );
    std::fs::write(&config_path, test_config).unwrap();

    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", &cuebot_port.to_string()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");
    let dummy_output = stream_output(&mut dummy_server);

    wait_for_port_open(
        &mut dummy_server,
        &dummy_output,
        cuebot_port,
        "dummy-cuebot",
        10,
    );

    let (openrqd, _) = start_openrqd(&config_path, rqd_port, "openrqd");

    TestEnv {
        temp_dir,
        dummy_server,
        dummy_output,
        openrqd,
        rqd_port,
        config_path,
    }
}

/// Starts openrqd and waits for it to listen on `rqd_port`. Returns the process and its output.
fn start_openrqd(config_path: &Path, rqd_port: u16, label: &str) -> (Child, Receiver<String>) {
    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");
    let output = stream_output(&mut openrqd);
    wait_for_port_open(&mut openrqd, &output, rqd_port, label, 20);
    (openrqd, output)
}

/// Restarts openrqd with the test's config and waits up to 40s for dummy-cuebot to receive a
/// frame completion, returning dummy-cuebot's output. On failure, panics with `failure` and the
/// output of both processes.
#[cfg(unix)]
fn restart_and_wait_for_completion(env: TestEnv, failure: &str) -> String {
    let (mut openrqd, rqd_output) =
        start_openrqd(&env.config_path, env.rqd_port, "openrqd (restarted)");
    let (success, output) = monitor_server_output(env.dummy_server, env.dummy_output, 1, 40);

    let rqd_exit = openrqd.try_wait().ok().flatten();
    let _ = openrqd.kill();
    let _ = openrqd.wait();

    if !success {
        let rqd_output = collect_output(&rqd_output);
        let tail: Vec<&str> = rqd_output.lines().rev().take(200).collect();
        println!("Server output:\n{}", output);
        println!(
            "Restarted openrqd output (last {} lines):\n{}",
            tail.len(),
            tail.into_iter().rev().collect::<Vec<_>>().join("\n")
        );
        panic!("{failure} (restarted openrqd exit status: {rqd_exit:?})");
    }
    output
}

/// Returns true when a frame entrypoint wrapper spawned from `temp_dir` is still running.
/// The wrapper's command line contains the entrypoint script path, which lives under the
/// test's private temp dir, so matching on that path only sees this test's frame.
#[cfg(unix)]
fn frame_wrapper_running(temp_dir: &Path) -> bool {
    let output = Command::new("pgrep")
        .args(["-f", temp_dir.to_str().unwrap()])
        .output()
        .expect("pgrep should run");
    !String::from_utf8_lossy(&output.stdout).trim().is_empty()
}

#[cfg(unix)]
fn snapshot_count(temp_dir: &Path) -> usize {
    std::fs::read_dir(temp_dir.join("snapshots"))
        .map(|dir| {
            dir.filter_map(|entry| entry.ok())
                .filter(|entry| entry.file_name().to_string_lossy().ends_with(".bin"))
                .count()
        })
        .unwrap_or(0)
}

fn launch_frame(rqd_port: u16, command: &str, extra_args: &[&str]) -> std::process::Output {
    let mut args = vec!["rqd-client", "--hostname", "127.0.0.1", "--port"];
    let port_str = rqd_port.to_string();
    args.push(&port_str);
    args.push("launch-frame");
    args.extend_from_slice(extra_args);
    args.push(command);

    Command::new(get_binary_path("dummy-cuebot"))
        .args(&args)
        .output()
        .expect("Failed to launch frame")
}

// --- Tests ---

/// Test that verifies openrqd can start, accept frame launches, and complete them successfully
#[tokio::test]
async fn test_openrqd_frame_execution_with_completion() {
    let _guard = integration_test_lock();
    let env = setup_test_env("2s", 2);
    let TestEnv {
        dummy_server,
        dummy_output,
        mut openrqd,
        rqd_port,
        ..
    } = env;

    let frame_output = launch_frame(rqd_port, &sleep_and_echo_cmd("Test frame execution"), &[]);

    assert!(
        frame_output.status.success(),
        "Frame launch failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    let server_handle =
        thread::spawn(move || monitor_server_output(dummy_server, dummy_output, 1, timeout_secs()));
    sleep(Duration::from_millis(wait_millis())).await;

    let _ = openrqd.kill();
    let _ = openrqd.wait();

    let (success, output) = server_handle.join().unwrap();

    if !success {
        println!("Server output:\n{}", output);
        panic!("Failed to detect frame completion or status reports");
    }

    println!("Frame execution and completion verified successfully!");
}

/// Test launching a frame with environment variables and verify completion
#[tokio::test]
async fn test_frame_with_environment_variables_and_completion() {
    let _guard = integration_test_lock();
    let env = setup_test_env("2s", 2);
    let TestEnv {
        dummy_server,
        dummy_output,
        mut openrqd,
        rqd_port,
        ..
    } = env;

    let frame_output = launch_frame(
        rqd_port,
        &env_echo_cmd(),
        &["--env", "TEST_VAR=test_value,ANOTHER_VAR=another_value"],
    );

    assert!(
        frame_output.status.success(),
        "Frame launch with env vars failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    let server_handle =
        thread::spawn(move || monitor_server_output(dummy_server, dummy_output, 1, timeout_secs()));
    sleep(Duration::from_millis(wait_millis())).await;

    let _ = openrqd.kill();
    let _ = openrqd.wait();

    let (success, output) = server_handle.join().unwrap();

    if !success {
        println!("Server output:\n{}", output);
        panic!("Failed to detect frame completion with environment variables");
    }

    println!("Frame with environment variables completed successfully!");
}

/// Test launching a frame as current user (unix only)
#[cfg(unix)]
#[tokio::test]
async fn test_frame_run_as_user() {
    let _guard = integration_test_lock();
    let env = setup_test_env("5s", 2);
    let TestEnv {
        mut dummy_server,
        mut openrqd,
        rqd_port,
        ..
    } = env;

    let frame_output = launch_frame(rqd_port, "whoami", &["--run-as-user"]);

    assert!(
        frame_output.status.success(),
        "Frame launch as user failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    sleep(Duration::from_millis(2000)).await;

    let _ = openrqd.kill();
    let _ = dummy_server.kill();
    let _ = openrqd.wait();
    let _ = dummy_server.wait();
}

/// Test using the test script from resources
#[tokio::test]
async fn test_memory_fork_script() {
    let _guard = integration_test_lock();
    let env = setup_test_env("5s", 2);
    let TestEnv {
        mut dummy_server,
        mut openrqd,
        rqd_port,
        ..
    } = env;

    let script_path = memory_fork_script_path();
    let frame_output = launch_frame(rqd_port, &quoted_if_needed(script_path), &[]);

    assert!(
        frame_output.status.success(),
        "Memory fork script launch failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    sleep(Duration::from_millis(3000)).await;

    let _ = openrqd.kill();
    let _ = dummy_server.kill();
    let _ = openrqd.wait();
    let _ = dummy_server.wait();
}

/// A server that stops writing must not stall the monitor past its deadline.
#[test]
fn test_monitor_times_out_on_silent_server() {
    let mut silent = if cfg!(windows) {
        Command::new("powershell")
            .args(["-NoProfile", "-Command", "Start-Sleep -Seconds 60"])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
    } else {
        Command::new("sleep")
            .arg("60")
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
    }
    .expect("Failed to start silent child");
    let output = stream_output(&mut silent);

    let start = Instant::now();
    let (success, _) = monitor_server_output(silent, output, 1, 2);

    assert!(!success, "a silent server should not report completions");
    assert!(
        start.elapsed() < Duration::from_secs(10),
        "monitor overran its 2s deadline: {:?}",
        start.elapsed()
    );
}

/// Test error handling when trying to connect to non-existent RQD
#[tokio::test]
async fn test_connection_error_handling() {
    let _guard = integration_test_lock();
    let output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "127.0.0.1",
            "--port",
            "19999", // Non-existent port
            "launch-frame",
            &echo_cmd("This should fail"),
        ])
        .output()
        .expect("Failed to run dummy-cuebot command");

    assert!(
        !output.status.success(),
        "Expected connection failure but command succeeded"
    );

    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("Failed to connect")
            || stderr.contains("Connection refused")
            || stderr.contains("error connecting")
            || stderr.contains("transport error"),
        "Expected connection error message but got: {}",
        stderr
    );
}

/// Test that multiple frames can be launched sequentially and all complete successfully
#[tokio::test]
async fn test_multiple_frames_sequential_with_completion() {
    let _guard = integration_test_lock();
    let env = setup_test_env("2s", 4);
    let TestEnv {
        dummy_server,
        dummy_output,
        mut openrqd,
        rqd_port,
        ..
    } = env;

    const NUM_FRAMES: usize = 3;
    let frame_delay = if cfg!(windows) {
        Duration::from_secs(10)
    } else {
        Duration::from_millis(500)
    };

    for i in 1..=NUM_FRAMES {
        let frame_output = launch_frame(rqd_port, &echo_cmd(&format!("Frame {}", i)), &[]);

        assert!(
            frame_output.status.success(),
            "Frame {} launch failed: {}",
            i,
            String::from_utf8_lossy(&frame_output.stderr)
        );

        sleep(frame_delay).await;
    }

    let monitor_timeout = if cfg!(windows) { 25 } else { 20 };
    let server_handle = thread::spawn(move || {
        monitor_server_output(dummy_server, dummy_output, NUM_FRAMES, monitor_timeout)
    });

    let post_launch_wait = if cfg!(windows) { 12000 } else { 10000 };
    sleep(Duration::from_millis(post_launch_wait)).await;

    let _ = openrqd.kill();
    let _ = openrqd.wait();

    let (success, output) = server_handle.join().unwrap();

    if !success {
        println!("Server output:\n{}", output);
        panic!("Failed to detect all {} frame completions", NUM_FRAMES);
    }

    println!("All {} frames completed successfully!", NUM_FRAMES);
}

/// Live-restart test: SIGKILL rqd while a frame is running, verify the frame process
/// survives, then restart rqd with the same config and verify it recovers the frame and
/// reports its successful completion to Cuebot.
#[cfg(unix)]
#[tokio::test]
async fn test_rqd_restart_recovers_running_frame() {
    let _guard = integration_test_lock();
    let mut env = setup_test_env("2s", 2);

    let frame_output = launch_frame(env.rqd_port, "sleep 6 && echo 'survived rqd restart'", &[]);
    assert!(
        frame_output.status.success(),
        "Frame launch failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    // Let the frame start and its snapshot land on disk.
    sleep(Duration::from_millis(2000)).await;
    assert!(
        snapshot_count(env.temp_dir.path()) > 0,
        "expected a frame snapshot on disk before killing rqd"
    );
    assert!(
        frame_wrapper_running(env.temp_dir.path()),
        "expected the frame process to be running before killing rqd"
    );

    // Hard-kill rqd: no graceful shutdown, exactly like a crash or a live upgrade.
    env.openrqd.kill().expect("openrqd should be killable");
    let _ = env.openrqd.wait();

    // The frame must not die with rqd.
    assert!(
        frame_wrapper_running(env.temp_dir.path()),
        "frame process should survive rqd being SIGKILLed"
    );

    // Restart rqd with the same config; it must recover the frame from its snapshot.
    let output = restart_and_wait_for_completion(
        env,
        "Recovered frame completion was not reported after rqd restart",
    );
    assert!(
        output.contains("exit_status: 0"),
        "recovered frame should complete successfully, server output:\n{}",
        output
    );

    println!("Frame survived rqd restart and completed successfully!");
}

/// Downtime-completion test: the frame finishes while rqd is down. On restart, rqd must
/// recover the frame's real exit status from the exit file and report it to Cuebot instead
/// of losing the frame or reporting a synthetic failure.
#[cfg(unix)]
#[tokio::test]
async fn test_rqd_restart_reports_frame_finished_while_down() {
    let _guard = integration_test_lock();
    let mut env = setup_test_env("2s", 2);

    // Distinctive non-zero exit code proves the status came from the exit file and not
    // from a default success/failure path.
    let frame_output = launch_frame(env.rqd_port, "sleep 3 && exit 3", &[]);
    assert!(
        frame_output.status.success(),
        "Frame launch failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    // Wait for the snapshot, then hard-kill rqd while the frame is still running.
    sleep(Duration::from_millis(1500)).await;
    assert!(
        snapshot_count(env.temp_dir.path()) > 0,
        "expected a frame snapshot on disk before killing rqd"
    );
    env.openrqd.kill().expect("openrqd should be killable");
    let _ = env.openrqd.wait();

    // Let the frame finish during the downtime window.
    sleep(Duration::from_millis(4000)).await;
    assert!(
        !frame_wrapper_running(env.temp_dir.path()),
        "frame should have finished while rqd was down"
    );

    let output = restart_and_wait_for_completion(
        env,
        "Completion of a frame that finished during rqd downtime was not reported",
    );
    assert!(
        output.contains("exit_status: 3"),
        "the frame's real exit code (3) should be recovered from the exit file, server output:\n{}",
        output
    );

    println!("Frame that finished during rqd downtime was reported correctly!");
}
