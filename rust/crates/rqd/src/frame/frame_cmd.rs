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

use miette::{miette, IntoDiagnostic, Result};
use std::fmt::Display;
use std::io::Write;
use std::{fs, fs::File};
use tokio::process::Command;
use uuid::Uuid;

pub struct FrameCmdBuilder {
    cmd: Command,
    shell: String,
    exit_file_path: Option<String>,
    become_user: Option<BecomeUser>,
    entrypoint_file_path: String,
    end_cmd: Option<String>,
}

struct BecomeUser {
    uid: u32,
    gid: u32,
    username: String,
}

impl Display for BecomeUser {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let passwd = Uuid::new_v4().to_string();
        write!(
            f,
            r#"
# Add and become user
useradd -u {} -g {} -p {} {}
su {}
"#,
            self.uid, self.gid, passwd, self.username, self.username
        )
    }
}

impl FrameCmdBuilder {
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    pub fn new(shell: &String, entrypoint_file_path: String) -> Self {
        let cmd = Command::new(shell);
        Self {
            cmd,
            shell: shell.clone(),
            exit_file_path: None,
            become_user: None,
            entrypoint_file_path,
            end_cmd: None,
        }
    }

    #[cfg(target_os = "windows")]
    pub fn new(shell: &String, entrypoint_file_path: String) -> Self {
        let cmd = Command::new(shell);
        Self {
            cmd,
            shell: shell.clone(),
            exit_file_path: None,
            become_user: None,
            entrypoint_file_path,
            end_cmd: None,
        }
    }

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    pub fn build(&mut self) -> Result<(&mut Command, String)> {
        use std::os::unix::fs::PermissionsExt;

        let args: Vec<&str> = self
            .cmd
            .as_std()
            .get_args()
            .filter_map(|arg| arg.to_str())
            .collect();
        let cmd_str = args.join(" ");
        let mut file = File::create(&self.entrypoint_file_path).into_diagnostic()?;

        let add_user = match &self.become_user {
            Some(add_user) => add_user.to_string(),
            None => "".to_string(),
        };

        // If an exit_file_path is passed, build a script that traps the inner command and write its
        // output to the exit_file_path.
        //
        // The wrapper runs the command in the background and `wait`s for it: bash only runs trap
        // handlers between foreground commands, so a foreground child would make the wrapper deaf
        // to signals until the command finished. The background+wait pattern lets a trapped signal
        // interrupt `wait` immediately, get forwarded to the command, after which the wrapper
        // resumes waiting for the command's real exit status.
        //
        // The exit status is written to the exit file with a write-then-rename so a recovering RQD
        // can never observe a partially written file: either the file does not exist yet, or it
        // holds the complete status.
        let script = match &self.exit_file_path {
            Some(exit_file_path) => format!(
                r#"#!{shell}
# Forward a trapped signal to the command
handle_signal() {{
    local signal=$1
    if [ -n "$command_pid" ] && kill -0 $command_pid 2>/dev/null; then
        kill -$signal $command_pid 2>/dev/null
    fi
}}

# Set up signal handling
trap 'handle_signal TERM' SIGTERM
trap 'handle_signal INT' SIGINT
trap 'handle_signal HUP' SIGHUP
{add_user}

# Start the command in the background and wait for it, so traps fire promptly
eval '{cmd_str}' &
command_pid=$!
wait $command_pid
exit_code=$?

# `wait` returns 128+signal when interrupted by a trapped signal while the command
# is still alive; keep waiting until the command has really exited. `kill -0` also
# succeeds while the command is an unreaped zombie, in which case the extra `wait`
# reaps it and returns its real exit status.
while [ $exit_code -gt 128 ] && kill -0 $command_pid 2>/dev/null; do
    wait $command_pid
    exit_code=$?
done

# Atomically write the exit code to the exit file
echo $exit_code > {exit_file_path}.tmp && mv {exit_file_path}.tmp {exit_file_path}
exit $exit_code
"#,
                shell = self.shell,
                exit_file_path = exit_file_path,
                add_user = add_user,
                cmd_str = cmd_str
            ),
            None => format!(
                r#"#!{}
# Maybe add user
{}

# Execute Actual command
{}
                        "#,
                self.shell, add_user, cmd_str
            ),
        };

        self.end_cmd = Some(script.clone());

        file.write_all(script.as_bytes()).into_diagnostic()?;
        // Explicitly close the file before execution to avoid "Text file busy" errors
        drop(file);
        // Make the entrypoint file executable
        fs::set_permissions(
            &self.entrypoint_file_path,
            fs::Permissions::from_mode(0o755),
        )
        .map_err(|e| miette!("Failed to set entrypoint file permissions: {}", e))?;

        self.cmd = Command::new(&self.entrypoint_file_path);
        Ok((&mut self.cmd, script.clone()))
    }

    #[cfg(target_os = "windows")]
    pub fn build(&mut self) -> Result<(&mut Command, String)> {
        // Validate that the configured shell is cmd.exe (the only supported shell on Windows)
        let shell_lower = self.shell.to_lowercase();
        let shell_name = std::path::Path::new(&shell_lower)
            .file_name()
            .and_then(|f| f.to_str())
            .unwrap_or(&shell_lower);
        if shell_name != "cmd.exe" && shell_name != "cmd" {
            return Err(miette!(
                "Unsupported shell on Windows: '{}'. Only cmd.exe is supported.",
                self.shell
            ));
        }

        let args: Vec<&str> = self
            .cmd
            .as_std()
            .get_args()
            .filter_map(|arg| arg.to_str())
            .collect();
        let cmd_str = args.join(" ");
        let mut file = File::create(&self.entrypoint_file_path).into_diagnostic()?;

        let script = match &self.exit_file_path {
            Some(exit_file_path) => format!(
                "@echo off\r\n{}\r\nset exit_code=%ERRORLEVEL%\r\necho %exit_code% > {}\r\nexit /b %exit_code%\r\n",
                cmd_str, exit_file_path
            ),
            None => format!("@echo off\r\n{}\r\n", cmd_str),
        };

        self.end_cmd = Some(script.clone());
        file.write_all(script.as_bytes()).into_diagnostic()?;
        drop(file);

        let mut cmd = Command::new(&self.shell);
        cmd.arg("/c").arg(&self.entrypoint_file_path);
        self.cmd = cmd;
        Ok((&mut self.cmd, script.clone()))
    }

    /// Adds a taskset reservation for the `proc_list`:
    /// ```bash
    ///   taskset -p 1,2,3
    /// ```
    #[cfg(target_os = "linux")]
    pub fn with_taskset(&mut self, cpu_list: Vec<u32>) -> &mut Self {
        use itertools::Itertools;

        let taskset_list = cpu_list.into_iter().map(|v| v.to_string()).join(",");
        self.cmd.arg("taskset").arg("-c").arg(taskset_list.as_str());
        self
    }

    #[cfg(target_os = "macos")]
    // taskset is noop on macos. There's not a native way to allocate threads to sockets
    pub fn with_taskset(&mut self, _cpu_list: Vec<u32>) -> &mut Self {
        self
    }

    #[cfg(target_os = "windows")]
    // taskset is noop on windows. There's not a native way to allocate threads to sockets
    pub fn with_taskset(&mut self, _cpu_list: Vec<u32>) -> &mut Self {
        self
    }

    /// Adds a nice call
    /// ```bash
    ///   /bin/nice
    /// ```
    #[cfg(target_os = "linux")]
    pub fn with_nice(&mut self) -> &mut Self {
        self.cmd.arg("/bin/nice");
        self
    }

    /// Adds a nice call
    /// ```bash
    ///   /bin/nice
    /// ```
    #[cfg(target_os = "macos")]
    pub fn with_nice(&mut self) -> &mut Self {
        self.cmd.arg("/bin/nice");
        self
    }

    #[cfg(target_os = "windows")]
    pub fn with_nice(&mut self) -> &mut Self {
        self
    }

    /// Main command requested by the frame.
    pub fn with_frame_cmd(&mut self, frame_cmd: String) -> &mut Self {
        self.cmd.arg(frame_cmd);
        self
    }

    #[cfg(target_os = "macos")]
    pub fn with_exit_file(&mut self, exit_file_path: String) -> &mut Self {
        self.exit_file_path = Some(exit_file_path);
        self
    }

    #[cfg(target_os = "linux")]
    pub fn with_exit_file(&mut self, exit_file_path: String) -> &mut Self {
        self.exit_file_path = Some(exit_file_path);
        self
    }

    #[cfg(target_os = "windows")]
    pub fn with_exit_file(&mut self, exit_file_path: String) -> &mut Self {
        // Meant for the recovery mode feature. Which is disabled on windows for not being stable
        // self.exit_file_path = Some(exit_file_path);
        self
    }

    #[allow(dead_code)]
    pub fn with_become_user(&mut self, uid: u32, gid: u32, username: String) -> &mut Self {
        self.become_user = Some(BecomeUser { uid, gid, username });
        self
    }
}

#[cfg(test)]
#[cfg(any(target_os = "linux", target_os = "macos"))]
mod tests {
    use super::FrameCmdBuilder;
    use std::process::Command as StdCommand;

    struct BuiltScript {
        _temp: tempfile::TempDir,
        entrypoint: String,
        exit_file: String,
        script: String,
    }

    fn build_script(frame_cmd: &str) -> BuiltScript {
        let temp = tempfile::tempdir().unwrap();
        let entrypoint = temp
            .path()
            .join("entrypoint.sh")
            .to_string_lossy()
            .to_string();
        let exit_file = temp
            .path()
            .join("exit_status")
            .to_string_lossy()
            .to_string();
        let shell = "/bin/bash".to_string();
        let mut builder = FrameCmdBuilder::new(&shell, entrypoint.clone());
        builder
            .with_frame_cmd(frame_cmd.to_string())
            .with_exit_file(exit_file.clone());
        let (_cmd, script) = builder.build().unwrap();
        BuiltScript {
            _temp: temp,
            entrypoint,
            exit_file,
            script,
        }
    }

    /// The exit-file harness must be active on every unix platform. This is the regression
    /// guard for the era when `with_exit_file` was a no-op on Linux, which silently disabled
    /// frame recovery there.
    #[test]
    fn test_exit_file_enabled_on_this_platform() {
        let built = build_script("echo hello");
        assert!(
            built.script.contains(&built.exit_file),
            "generated script must reference the exit file: {}",
            built.script
        );
    }

    #[test]
    fn test_script_structure() {
        let built = build_script("echo hello");
        let script = &built.script;

        // The command must run in the background: bash defers trap handlers while a
        // foreground child runs, so a foreground command would make the wrapper deaf to
        // kill requests until the frame finished on its own.
        assert!(
            script.contains("eval 'echo hello' &"),
            "command must run in the background: {script}"
        );
        assert!(
            script.contains("wait $command_pid"),
            "wrapper must wait for the background command: {script}"
        );
        // Signals must be forwarded to the frame process.
        for trap in [
            "trap 'handle_signal TERM' SIGTERM",
            "trap 'handle_signal INT' SIGINT",
            "trap 'handle_signal HUP' SIGHUP",
        ] {
            assert!(script.contains(trap), "missing {trap}: {script}");
        }
        // The exit status must be written atomically (write to temp + rename) so a
        // recovering RQD can never read a partially written status.
        assert!(
            script.contains(&format!(
                "echo $exit_code > {exit}.tmp && mv {exit}.tmp {exit}",
                exit = built.exit_file
            )),
            "exit file must be written atomically: {script}"
        );

        // The entrypoint file must be executable.
        use std::os::unix::fs::PermissionsExt;
        let mode = std::fs::metadata(&built.entrypoint)
            .unwrap()
            .permissions()
            .mode();
        assert_eq!(mode & 0o111, 0o111, "entrypoint must be executable");
    }

    /// Executes the generated wrapper and checks that a plain exit code is both propagated
    /// as the wrapper's own exit status and persisted in the exit file.
    #[test]
    fn test_script_propagates_and_persists_exit_code() {
        let built = build_script("exit 7");

        let status = StdCommand::new(&built.entrypoint)
            .status()
            .expect("entrypoint should execute");
        assert_eq!(status.code(), Some(7));

        let persisted = std::fs::read_to_string(&built.exit_file).unwrap();
        assert_eq!(persisted.trim(), "7");
    }

    /// SIGTERM delivered to the wrapper alone (not the whole process group) must be
    /// forwarded to the frame command, and the resulting 128+15 status must be persisted.
    /// This is what keeps kill requests working for frames that survived an RQD restart.
    #[test]
    fn test_script_forwards_sigterm_and_persists_status() {
        let built = build_script("sleep 30");

        let mut child = StdCommand::new(&built.entrypoint)
            .spawn()
            .expect("entrypoint should spawn");

        // Wait until the wrapper's background command exists: traps are installed before
        // the command is started, so its presence proves the wrapper is ready for signals.
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
        loop {
            let listed = StdCommand::new("pgrep")
                .args(["-P", &child.id().to_string()])
                .output()
                .expect("pgrep should run");
            if !String::from_utf8_lossy(&listed.stdout).trim().is_empty() {
                break;
            }
            assert!(
                std::time::Instant::now() < deadline,
                "wrapper never started its background command"
            );
            std::thread::sleep(std::time::Duration::from_millis(50));
        }

        let pid = nix::unistd::Pid::from_raw(child.id() as i32);
        nix::sys::signal::kill(pid, nix::sys::signal::Signal::SIGTERM).unwrap();

        let status = child.wait().unwrap();
        assert_eq!(
            status.code(),
            Some(143),
            "wrapper should exit with 128+SIGTERM after forwarding the signal"
        );

        let persisted = std::fs::read_to_string(&built.exit_file).unwrap();
        assert_eq!(persisted.trim(), "143");
    }
}
