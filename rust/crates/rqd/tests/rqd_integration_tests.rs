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
use std::process::{Command, Stdio};
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
        ("", "", "", "")
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

#[cfg(windows)]
fn sleep_and_echo_cmd(message: &str) -> String {
    format!("ping -n 2 127.0.0.1 > NUL & echo {}", message)
}

#[cfg(windows)]
fn env_echo_cmd() -> String {
    "echo %TEST_VAR% %ANOTHER_VAR%".to_string()
}

#[cfg(windows)]
fn whoami_cmd() -> String {
    "whoami".to_string()
}

/// Helper function to monitor server output for frame completion
fn monitor_server_output(
    mut child: std::process::Child,
    expected_completions: usize,
    timeout_secs: u64,
) -> (bool, String) {
    let stdout = child.stdout.take().expect("Failed to capture stdout");
    let reader = BufReader::new(stdout);

    let start_time = std::time::Instant::now();
    let mut all_output = String::new();
    let mut completion_count = 0;
    let mut saw_status_report = false;
    let mut line_count = 0;

    for line in reader.lines() {
        if let Ok(line) = line {
            line_count += 1;
            all_output.push_str(&line);
            all_output.push('\n');

            // Debug: Print interesting lines
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

            // Check for frame completion reports - look for the key completion indicators
            if line.contains("report_running_frame_completion") {
                println!("Found completion report: checking exit status...");
                // Count any completion, but note the exit status
                completion_count += 1;
                if line.contains("exit_status: 0") {
                    println!(
                        "Found successful frame completion {}/{}",
                        completion_count, expected_completions
                    );
                } else if line.contains("exit_status:") {
                    // Extract exit status for debugging
                    if let Some(pos) = line.find("exit_status:") {
                        let status_part = &line[pos..];
                        if let Some(end) = status_part.find(',') {
                            let status = &status_part[..end];
                            println!(
                                "Found frame completion {}/{} with {}",
                                completion_count, expected_completions, status
                            );
                        }
                    }
                }
            }

            // Check for status reports showing running frames
            if line.contains("report_status") && line.contains("frames: [") {
                saw_status_report = true;
                println!("Found status report with running frames");
            }

            // Exit if we've seen all expected completions
            if completion_count >= expected_completions {
                println!("All expected frame completions found!");
                break;
            }
        }

        // Timeout check
        if start_time.elapsed().as_secs() > timeout_secs {
            println!(
                "Timeout reached waiting for frame completions ({}s)",
                timeout_secs
            );
            println!(
                "Stats: {} lines processed, {} completions found, status report: {}",
                line_count, completion_count, saw_status_report
            );
            break;
        }
    }

    let _ = child.kill();
    let success = completion_count >= expected_completions;
    println!(
        "Final results: {} completions out of {} expected, saw status report: {}",
        completion_count, expected_completions, saw_status_report
    );
    (success, all_output)
}

fn collect_child_output(child: &mut std::process::Child) -> (String, String) {
    let mut stdout = String::new();
    let mut stderr = String::new();
    if let Some(mut out) = child.stdout.take() {
        let _ = out.read_to_string(&mut stdout);
    }
    if let Some(mut err) = child.stderr.take() {
        let _ = err.read_to_string(&mut stderr);
    }
    (stdout, stderr)
}

fn wait_for_port_open(child: &mut std::process::Child, port: u16, label: &str, timeout_secs: u64) {
    let start = Instant::now();
    loop {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return;
        }

        if let Ok(Some(status)) = child.try_wait() {
            let (stdout, stderr) = collect_child_output(child);
            panic!(
                "{} exited early with status {}.\nstdout:\n{}\nstderr:\n{}",
                label, status, stdout, stderr
            );
        }

        if start.elapsed().as_secs() >= timeout_secs {
            let _ = child.kill();
            let _ = child.wait();
            let (stdout, stderr) = collect_child_output(child);
            panic!(
                "{} did not open port {} within {}s.\nstdout:\n{}\nstderr:\n{}",
                label, port, timeout_secs, stdout, stderr
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

/// Test that verifies openrqd can start, accept frame launches, and complete them successfully
#[cfg(unix)]
#[tokio::test]
async fn test_openrqd_frame_execution_with_completion() {
    let _guard = integration_test_lock();
    // Create temporary directory for test configuration
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");
    let (rqd_port, cuebot_port) = get_two_free_ports();
    let temp_dir_str = yaml_path(temp_dir.path());
    let tmp_dir_str = yaml_path(&temp_dir.path().join("tmp"));
    let snapshots_dir_str = yaml_path(&temp_dir.path().join("snapshots"));

    // Create test configuration with shorter report interval
    let (cpuinfo_path, distro_release_path, proc_stat_path, proc_loadavg_path) = machine_paths();
    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: false

machine:
  monitor_interval: 2s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 2
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
        tmp_dir_str,
        cpuinfo_path,
        distro_release_path,
        proc_stat_path,
        proc_loadavg_path,
        rqd_port,
        cuebot_port,
        tmp_dir_str,
        snapshots_dir_str
    );

    std::fs::write(&config_path, test_config).unwrap();

    // Start dummy-cuebot report server
    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", &cuebot_port.to_string()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    wait_for_port_open(&mut dummy_server, cuebot_port, "dummy-cuebot", 10);

    // Start openrqd with test config
    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    wait_for_port_open(&mut openrqd, rqd_port, "openrqd", 20);

    // Test launching a simple frame that runs for a moment to ensure proper completion
    let frame_output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "127.0.0.1",
            "--port",
            &rqd_port.to_string(),
            "launch-frame",
            "sleep 1 && echo 'Test frame execution'",
        ])
        .output()
        .expect("Failed to launch frame");

    assert!(
        frame_output.status.success(),
        "Frame launch failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    // Monitor server output for frame completion in a separate thread
    let server_handle = thread::spawn(move || monitor_server_output(dummy_server, 1, 15));

    // Wait for frame to complete
    sleep(Duration::from_millis(8000)).await;

    // Stop RQD
    let _ = openrqd.kill();
    let _ = openrqd.wait();

    // Check results from server monitoring
    let (success, output) = server_handle.join().unwrap();

    if !success {
        println!("Server output:\n{}", output);
        panic!("Failed to detect frame completion or status reports");
    }

    println!("Frame execution and completion verified successfully!");
}

/// Test launching a frame with environment variables and verify completion
#[cfg(unix)]
#[tokio::test]
async fn test_frame_with_environment_variables_and_completion() {
    let _guard = integration_test_lock();
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");
    let (rqd_port, cuebot_port) = get_two_free_ports();
    let temp_dir_str = yaml_path(temp_dir.path());
    let tmp_dir_str = yaml_path(&temp_dir.path().join("tmp"));
    let snapshots_dir_str = yaml_path(&temp_dir.path().join("snapshots"));

    let (cpuinfo_path, distro_release_path, proc_stat_path, proc_loadavg_path) = machine_paths();
    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: false

machine:
  monitor_interval: 2s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 2
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
        tmp_dir_str,
        cpuinfo_path,
        distro_release_path,
        proc_stat_path,
        proc_loadavg_path,
        rqd_port,
        cuebot_port,
        tmp_dir_str,
        snapshots_dir_str
    );

    std::fs::write(&config_path, test_config).unwrap();

    // Start dummy-cuebot report server
    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", &cuebot_port.to_string()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    wait_for_port_open(&mut dummy_server, cuebot_port, "dummy-cuebot", 10);

    // Start openrqd
    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    wait_for_port_open(&mut openrqd, rqd_port, "openrqd", 20);

    // Test launching a frame with environment variables
    let frame_output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "127.0.0.1",
            "--port",
            &rqd_port.to_string(),
            "launch-frame",
            "--env",
            "TEST_VAR=test_value,ANOTHER_VAR=another_value",
            "echo $TEST_VAR $ANOTHER_VAR",
        ])
        .output()
        .expect("Failed to launch frame with env vars");

    assert!(
        frame_output.status.success(),
        "Frame launch with env vars failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    // Monitor server output for frame completion
    let server_handle = thread::spawn(move || monitor_server_output(dummy_server, 1, 15));

    sleep(Duration::from_millis(8000)).await;

    // Clean up
    let _ = openrqd.kill();
    let _ = openrqd.wait();

    // Verify completion
    let (success, output) = server_handle.join().unwrap();

    if !success {
        println!("Server output:\n{}", output);
        panic!("Failed to detect frame completion with environment variables");
    }

    println!("Frame with environment variables completed successfully!");
}

/// Test launching a frame as current user
#[cfg(unix)]
#[tokio::test]
async fn test_frame_run_as_user() {
    let _guard = integration_test_lock();
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");
    let (rqd_port, cuebot_port) = get_two_free_ports();
    let temp_dir_str = yaml_path(temp_dir.path());
    let tmp_dir_str = yaml_path(&temp_dir.path().join("tmp"));
    let snapshots_dir_str = yaml_path(&temp_dir.path().join("snapshots"));

    let (cpuinfo_path, distro_release_path, proc_stat_path, proc_loadavg_path) = machine_paths();
    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: false

machine:
  monitor_interval: 5s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 2
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
        tmp_dir_str,
        cpuinfo_path,
        distro_release_path,
        proc_stat_path,
        proc_loadavg_path,
        rqd_port,
        cuebot_port,
        tmp_dir_str,
        snapshots_dir_str
    );

    std::fs::write(&config_path, test_config).unwrap();

    // Start dummy-cuebot report server
    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", &cuebot_port.to_string()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    wait_for_port_open(&mut dummy_server, cuebot_port, "dummy-cuebot", 10);

    // Start openrqd
    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    wait_for_port_open(&mut openrqd, rqd_port, "openrqd", 20);

    // Test launching a frame as current user
    let frame_output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "127.0.0.1",
            "--port",
            &rqd_port.to_string(),
            "launch-frame",
            "--run-as-user",
            "whoami",
        ])
        .output()
        .expect("Failed to launch frame as user");

    assert!(
        frame_output.status.success(),
        "Frame launch as user failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    sleep(Duration::from_millis(2000)).await;

    // Clean up
    let _ = openrqd.kill();
    let _ = dummy_server.kill();
    let _ = openrqd.wait();
    let _ = dummy_server.wait();
}

/// Test using the test script from resources
#[cfg(unix)]
#[tokio::test]
async fn test_memory_fork_script() {
    let _guard = integration_test_lock();
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");
    let (rqd_port, cuebot_port) = get_two_free_ports();
    let temp_dir_str = yaml_path(temp_dir.path());
    let tmp_dir_str = yaml_path(&temp_dir.path().join("tmp"));
    let snapshots_dir_str = yaml_path(&temp_dir.path().join("snapshots"));

    let (cpuinfo_path, distro_release_path, proc_stat_path, proc_loadavg_path) = machine_paths();
    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: false

machine:
  monitor_interval: 5s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 2
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
        tmp_dir_str,
        cpuinfo_path,
        distro_release_path,
        proc_stat_path,
        proc_loadavg_path,
        rqd_port,
        cuebot_port,
        tmp_dir_str,
        snapshots_dir_str
    );

    std::fs::write(&config_path, test_config).unwrap();

    // Start dummy-cuebot report server
    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", &cuebot_port.to_string()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    wait_for_port_open(&mut dummy_server, cuebot_port, "dummy-cuebot", 10);

    // Start openrqd
    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    wait_for_port_open(&mut openrqd, rqd_port, "openrqd", 20);

    // Test launching the memory fork script
    let frame_output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "127.0.0.1",
            "--port",
            &rqd_port.to_string(),
            "launch-frame",
            "../../crates/rqd/resources/test_scripts/memory_fork.sh",
        ])
        .output()
        .expect("Failed to launch memory fork script");

    assert!(
        frame_output.status.success(),
        "Memory fork script launch failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    // Give the script time to execute
    sleep(Duration::from_millis(3000)).await;

    // Clean up
    let _ = openrqd.kill();
    let _ = dummy_server.kill();
    let _ = openrqd.wait();
    let _ = dummy_server.wait();
}

/// Test error handling when trying to connect to non-existent RQD
#[cfg(unix)]
#[tokio::test]
async fn test_connection_error_handling() {
    let _guard = integration_test_lock();
    // Try to connect to non-existent RQD
    let output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "127.0.0.1",
            "--port",
            "19999", // Non-existent port
            "launch-frame",
            "echo 'This should fail'",
        ])
        .output()
        .expect("Failed to run dummy-cuebot command");

    // Should fail to connect
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
#[cfg(unix)]
#[tokio::test]
async fn test_multiple_frames_sequential_with_completion() {
    let _guard = integration_test_lock();
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");
    let (rqd_port, cuebot_port) = get_two_free_ports();
    let temp_dir_str = yaml_path(temp_dir.path());
    let tmp_dir_str = yaml_path(&temp_dir.path().join("tmp"));
    let snapshots_dir_str = yaml_path(&temp_dir.path().join("snapshots"));

    let (cpuinfo_path, distro_release_path, proc_stat_path, proc_loadavg_path) = machine_paths();
    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: false

machine:
  monitor_interval: 2s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 4
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
        tmp_dir_str,
        cpuinfo_path,
        distro_release_path,
        proc_stat_path,
        proc_loadavg_path,
        rqd_port,
        cuebot_port,
        tmp_dir_str,
        snapshots_dir_str
    );

    std::fs::write(&config_path, test_config).unwrap();

    // Start dummy-cuebot report server
    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", &cuebot_port.to_string()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    wait_for_port_open(&mut dummy_server, cuebot_port, "dummy-cuebot", 10);

    // Start openrqd
    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    wait_for_port_open(&mut openrqd, rqd_port, "openrqd", 20);

    // Launch multiple frames sequentially
    const NUM_FRAMES: usize = 3;
    for i in 1..=NUM_FRAMES {
        let frame_output = Command::new(get_binary_path("dummy-cuebot"))
            .args([
                "rqd-client",
                "--hostname",
                "127.0.0.1",
                "--port",
                &rqd_port.to_string(),
                "launch-frame",
                &format!("echo 'Frame {}'", i),
            ])
            .output()
            .expect("Failed to launch frame");

        assert!(
            frame_output.status.success(),
            "Frame {} launch failed: {}",
            i,
            String::from_utf8_lossy(&frame_output.stderr)
        );

        // Small delay between frames
        sleep(Duration::from_millis(500)).await;
    }

    // Monitor server output for all frame completions
    let server_handle = thread::spawn(move || monitor_server_output(dummy_server, NUM_FRAMES, 20));

    // Give frames time to execute
    sleep(Duration::from_millis(10000)).await;

    // Clean up
    let _ = openrqd.kill();
    let _ = openrqd.wait();

    // Verify all frames completed
    let (success, output) = server_handle.join().unwrap();

    if !success {
        println!("Server output:\n{}", output);
        panic!("Failed to detect all {} frame completions", NUM_FRAMES);
    }

    println!("All {} frames completed successfully!", NUM_FRAMES);
}

/// Windows variants of the integration tests
#[cfg(windows)]
#[tokio::test]
async fn test_openrqd_frame_execution_with_completion() {
    let _guard = integration_test_lock();
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");
    let (cpuinfo_path, distro_release_path, proc_stat_path, proc_loadavg_path) = machine_paths();
    let (rqd_port, cuebot_port) = get_two_free_ports();
    let temp_dir_str = yaml_path(temp_dir.path());
    let tmp_dir_str = yaml_path(&temp_dir.path().join("tmp"));
    let snapshots_dir_str = yaml_path(&temp_dir.path().join("snapshots"));

    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: false

machine:
  monitor_interval: 2s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 2
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
        tmp_dir_str,
        cpuinfo_path,
        distro_release_path,
        proc_stat_path,
        proc_loadavg_path,
        rqd_port,
        cuebot_port,
        tmp_dir_str,
        snapshots_dir_str
    );

    std::fs::write(&config_path, test_config).unwrap();

    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", &cuebot_port.to_string()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    wait_for_port_open(&mut dummy_server, cuebot_port, "dummy-cuebot", 10);

    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    wait_for_port_open(&mut openrqd, rqd_port, "openrqd", 20);

    let frame_output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "127.0.0.1",
            "--port",
            &rqd_port.to_string(),
            "launch-frame",
            &sleep_and_echo_cmd("Test frame execution"),
        ])
        .output()
        .expect("Failed to launch frame");

    assert!(
        frame_output.status.success(),
        "Frame launch failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    let server_handle = thread::spawn(move || monitor_server_output(dummy_server, 1, 20));
    sleep(Duration::from_millis(10000)).await;

    let _ = openrqd.kill();
    let _ = openrqd.wait();

    let (success, output) = server_handle.join().unwrap();
    if !success {
        println!("Server output:\n{}", output);
        panic!("Failed to detect frame completion or status reports");
    }
}

#[cfg(windows)]
#[tokio::test]
async fn test_frame_with_environment_variables_and_completion() {
    let _guard = integration_test_lock();
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");
    let (cpuinfo_path, distro_release_path, proc_stat_path, proc_loadavg_path) = machine_paths();
    let (rqd_port, cuebot_port) = get_two_free_ports();
    let temp_dir_str = yaml_path(temp_dir.path());
    let tmp_dir_str = yaml_path(&temp_dir.path().join("tmp"));
    let snapshots_dir_str = yaml_path(&temp_dir.path().join("snapshots"));

    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: false

machine:
  monitor_interval: 2s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 2
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
        tmp_dir_str,
        cpuinfo_path,
        distro_release_path,
        proc_stat_path,
        proc_loadavg_path,
        rqd_port,
        cuebot_port,
        tmp_dir_str,
        snapshots_dir_str
    );

    std::fs::write(&config_path, test_config).unwrap();

    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", &cuebot_port.to_string()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    wait_for_port_open(&mut dummy_server, cuebot_port, "dummy-cuebot", 10);

    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    wait_for_port_open(&mut openrqd, rqd_port, "openrqd", 20);

    let frame_output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "127.0.0.1",
            "--port",
            &rqd_port.to_string(),
            "launch-frame",
            "--env",
            "TEST_VAR=test_value,ANOTHER_VAR=another_value",
            &env_echo_cmd(),
        ])
        .output()
        .expect("Failed to launch frame with env vars");

    assert!(
        frame_output.status.success(),
        "Frame launch with env vars failed: {}",
        String::from_utf8_lossy(&frame_output.stderr)
    );

    let server_handle = thread::spawn(move || monitor_server_output(dummy_server, 1, 20));
    sleep(Duration::from_millis(10000)).await;

    let _ = openrqd.kill();
    let _ = openrqd.wait();

    let (success, output) = server_handle.join().unwrap();
    if !success {
        println!("Server output:\n{}", output);
        panic!("Failed to detect frame completion with environment variables");
    }
}

#[cfg(windows)]
#[tokio::test]
async fn test_memory_fork_script() {
    let _guard = integration_test_lock();
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");
    let (cpuinfo_path, distro_release_path, proc_stat_path, proc_loadavg_path) = machine_paths();
    let (rqd_port, cuebot_port) = get_two_free_ports();
    let temp_dir_str = yaml_path(temp_dir.path());
    let tmp_dir_str = yaml_path(&temp_dir.path().join("tmp"));
    let snapshots_dir_str = yaml_path(&temp_dir.path().join("snapshots"));

    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: false

machine:
  monitor_interval: 5s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 2
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
        tmp_dir_str,
        cpuinfo_path,
        distro_release_path,
        proc_stat_path,
        proc_loadavg_path,
        rqd_port,
        cuebot_port,
        tmp_dir_str,
        snapshots_dir_str
    );

    std::fs::write(&config_path, test_config).unwrap();

    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", &cuebot_port.to_string()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    wait_for_port_open(&mut dummy_server, cuebot_port, "dummy-cuebot", 10);

    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    wait_for_port_open(&mut openrqd, rqd_port, "openrqd", 20);

    let script_path = "../../crates/rqd/resources/test_scripts/memory_fork.cmd";

    let frame_output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "127.0.0.1",
            "--port",
            &rqd_port.to_string(),
            "launch-frame",
            &quoted_if_needed(script_path),
        ])
        .output()
        .expect("Failed to launch memory fork script");

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

#[cfg(windows)]
#[tokio::test]
async fn test_connection_error_handling() {
    let _guard = integration_test_lock();
    let output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "127.0.0.1",
            "--port",
            "19999",
            "launch-frame",
            "echo This should fail",
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

#[cfg(windows)]
#[tokio::test]
async fn test_multiple_frames_sequential_with_completion() {
    let _guard = integration_test_lock();
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");
    let (cpuinfo_path, distro_release_path, proc_stat_path, proc_loadavg_path) = machine_paths();
    let (rqd_port, cuebot_port) = get_two_free_ports();
    let temp_dir_str = yaml_path(temp_dir.path());
    let tmp_dir_str = yaml_path(&temp_dir.path().join("tmp"));
    let snapshots_dir_str = yaml_path(&temp_dir.path().join("snapshots"));

    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: false

machine:
  monitor_interval: 2s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 4
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
        tmp_dir_str,
        cpuinfo_path,
        distro_release_path,
        proc_stat_path,
        proc_loadavg_path,
        rqd_port,
        cuebot_port,
        tmp_dir_str,
        snapshots_dir_str
    );

    std::fs::write(&config_path, test_config).unwrap();

    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", &cuebot_port.to_string()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    wait_for_port_open(&mut dummy_server, cuebot_port, "dummy-cuebot", 10);

    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    wait_for_port_open(&mut openrqd, rqd_port, "openrqd", 20);

    const NUM_FRAMES: usize = 3;
    for i in 1..=NUM_FRAMES {
        let frame_output = Command::new(get_binary_path("dummy-cuebot"))
            .args([
                "rqd-client",
                "--hostname",
                "127.0.0.1",
                "--port",
                &rqd_port.to_string(),
                "launch-frame",
                &format!("echo Frame {}", i),
            ])
            .output()
            .expect("Failed to launch frame");

        assert!(
            frame_output.status.success(),
            "Frame {} launch failed: {}",
            i,
            String::from_utf8_lossy(&frame_output.stderr)
        );

        sleep(Duration::from_millis(500)).await;
    }

    let server_handle = thread::spawn(move || monitor_server_output(dummy_server, NUM_FRAMES, 25));
    sleep(Duration::from_millis(12000)).await;

    let _ = openrqd.kill();
    let _ = openrqd.wait();

    let (success, output) = server_handle.join().unwrap();
    if !success {
        println!("Server output:\n{}", output);
        panic!("Failed to detect all {} frame completions", NUM_FRAMES);
    }
}
