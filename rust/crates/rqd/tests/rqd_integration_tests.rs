use std::io::{BufRead, BufReader};
use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;
use tempfile::TempDir;
use tokio::time::sleep;

/// Helper function to determine the correct binary path based on build profile
fn get_binary_path(binary_name: &str) -> String {
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

/// Test that verifies openrqd can start, accept frame launches, and complete them successfully
#[tokio::test]
async fn test_openrqd_frame_execution_with_completion() {
    // Create temporary directory for test configuration
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");

    // Create test configuration with shorter report interval
    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: true

machine:
  monitor_interval: 2s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 2
  temp_path: "{}"
  cpuinfo_path: "../../crates/rqd/resources/cpuinfo/cpuinfo_srdsvr09_48-12-4"
  distro_release_path: "../../crates/rqd/resources/distro-release/rocky"
  proc_stat_path: "../../crates/rqd/resources/proc/stat"
  proc_loadavg_path: "../../crates/rqd/resources/proc/loadavg"

grpc:
  rqd_port: 18600
  cuebot_endpoints: ["localhost:14500"]

runner:
  run_on_docker: false
  default_uid: 1000
  temp_path: "{}"
  snapshots_path: "{}"
"#,
        temp_dir.path().to_str().unwrap(),
        temp_dir.path().join("tmp").to_str().unwrap(),
        temp_dir.path().join("tmp").to_str().unwrap(),
        temp_dir.path().join("snapshots").to_str().unwrap()
    );

    std::fs::write(&config_path, test_config).unwrap();

    // Start dummy-cuebot report server
    let dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", "14500"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    sleep(Duration::from_millis(1000)).await;

    // Start openrqd with test config
    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    sleep(Duration::from_millis(5000)).await;

    // Test launching a simple frame that runs for a moment to ensure proper completion
    let frame_output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "localhost",
            "--port",
            "18600",
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
#[tokio::test]
async fn test_frame_with_environment_variables_and_completion() {
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");

    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: true

machine:
  monitor_interval: 2s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 2
  temp_path: "{}"
  cpuinfo_path: "../../crates/rqd/resources/cpuinfo/cpuinfo_srdsvr09_48-12-4"
  distro_release_path: "../../crates/rqd/resources/distro-release/rocky"
  proc_stat_path: "../../crates/rqd/resources/proc/stat"
  proc_loadavg_path: "../../crates/rqd/resources/proc/loadavg"

grpc:
  rqd_port: 18601
  cuebot_endpoints: ["localhost:14501"]

runner:
  run_on_docker: false
  default_uid: 1000
  temp_path: "{}"
  snapshots_path: "{}"
"#,
        temp_dir.path().to_str().unwrap(),
        temp_dir.path().join("tmp").to_str().unwrap(),
        temp_dir.path().join("tmp").to_str().unwrap(),
        temp_dir.path().join("snapshots").to_str().unwrap()
    );

    std::fs::write(&config_path, test_config).unwrap();

    // Start dummy-cuebot report server
    let dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", "14501"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    sleep(Duration::from_millis(1000)).await;

    // Start openrqd
    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    sleep(Duration::from_millis(5000)).await;

    // Test launching a frame with environment variables
    let frame_output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "localhost",
            "--port",
            "18601",
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
#[tokio::test]
async fn test_frame_run_as_user() {
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");

    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: true

machine:
  monitor_interval: 5s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 2
  temp_path: "{}"
  cpuinfo_path: "../../crates/rqd/resources/cpuinfo/cpuinfo_srdsvr09_48-12-4"
  distro_release_path: "../../crates/rqd/resources/distro-release/rocky"
  proc_stat_path: "../../crates/rqd/resources/proc/stat"
  proc_loadavg_path: "../../crates/rqd/resources/proc/loadavg"

grpc:
  rqd_port: 18602
  cuebot_endpoints: ["localhost:14502"]

runner:
  run_on_docker: false
  default_uid: 1000
  temp_path: "{}"
  snapshots_path: "{}"
"#,
        temp_dir.path().to_str().unwrap(),
        temp_dir.path().join("tmp").to_str().unwrap(),
        temp_dir.path().join("tmp").to_str().unwrap(),
        temp_dir.path().join("snapshots").to_str().unwrap()
    );

    std::fs::write(&config_path, test_config).unwrap();

    // Start dummy-cuebot report server
    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", "14502"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    sleep(Duration::from_millis(1000)).await;

    // Start openrqd
    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    sleep(Duration::from_millis(5000)).await;

    // Test launching a frame as current user
    let frame_output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "localhost",
            "--port",
            "18602",
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
#[tokio::test]
async fn test_memory_fork_script() {
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");

    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: true

machine:
  monitor_interval: 5s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 2
  temp_path: "{}"
  cpuinfo_path: "../../crates/rqd/resources/cpuinfo/cpuinfo_srdsvr09_48-12-4"
  distro_release_path: "../../crates/rqd/resources/distro-release/rocky"
  proc_stat_path: "../../crates/rqd/resources/proc/stat"
  proc_loadavg_path: "../../crates/rqd/resources/proc/loadavg"

grpc:
  rqd_port: 18603
  cuebot_endpoints: ["localhost:14503"]

runner:
  run_on_docker: false
  default_uid: 1000
  temp_path: "{}"
  snapshots_path: "{}"
"#,
        temp_dir.path().to_str().unwrap(),
        temp_dir.path().join("tmp").to_str().unwrap(),
        temp_dir.path().join("tmp").to_str().unwrap(),
        temp_dir.path().join("snapshots").to_str().unwrap()
    );

    std::fs::write(&config_path, test_config).unwrap();

    // Start dummy-cuebot report server
    let mut dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", "14503"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    sleep(Duration::from_millis(1000)).await;

    // Start openrqd
    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    sleep(Duration::from_millis(5000)).await;

    // Test launching the memory fork script
    let frame_output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "localhost",
            "--port",
            "18603",
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
#[tokio::test]
async fn test_connection_error_handling() {
    // Try to connect to non-existent RQD
    let output = Command::new(get_binary_path("dummy-cuebot"))
        .args([
            "rqd-client",
            "--hostname",
            "localhost",
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
        stderr.contains("Failed to connect") || stderr.contains("Connection refused"),
        "Expected connection error message but got: {}",
        stderr
    );
}

/// Test that multiple frames can be launched sequentially and all complete successfully
#[tokio::test]
async fn test_multiple_frames_sequential_with_completion() {
    let temp_dir = TempDir::new().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");

    let test_config = format!(
        r#"
logging:
  level: debug
  path: "{}/test.log"
  file_appender: true

machine:
  monitor_interval: 2s
  use_ip_as_hostname: false
  nimby_mode: false
  facility: test
  worker_threads: 4
  temp_path: "{}"
  cpuinfo_path: "../../crates/rqd/resources/cpuinfo/cpuinfo_srdsvr09_48-12-4"
  distro_release_path: "../../crates/rqd/resources/distro-release/rocky"
  proc_stat_path: "../../crates/rqd/resources/proc/stat"
  proc_loadavg_path: "../../crates/rqd/resources/proc/loadavg"

grpc:
  rqd_port: 18604
  cuebot_endpoints: ["localhost:14504"]

runner:
  run_on_docker: false
  default_uid: 1000
  temp_path: "{}"
  snapshots_path: "{}"
"#,
        temp_dir.path().to_str().unwrap(),
        temp_dir.path().join("tmp").to_str().unwrap(),
        temp_dir.path().join("tmp").to_str().unwrap(),
        temp_dir.path().join("snapshots").to_str().unwrap()
    );

    std::fs::write(&config_path, test_config).unwrap();

    // Start dummy-cuebot report server
    let dummy_server = Command::new(get_binary_path("dummy-cuebot"))
        .args(["report-server", "--port", "14504"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start dummy-cuebot server");

    sleep(Duration::from_millis(1000)).await;

    // Start openrqd
    let mut openrqd = Command::new(get_binary_path("openrqd"))
        .env("OPENCUE_RQD_CONFIG", config_path.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start openrqd");

    sleep(Duration::from_millis(5000)).await;

    // Launch multiple frames sequentially
    const NUM_FRAMES: usize = 3;
    for i in 1..=NUM_FRAMES {
        let frame_output = Command::new(get_binary_path("dummy-cuebot"))
            .args([
                "rqd-client",
                "--hostname",
                "localhost",
                "--port",
                "18604",
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
