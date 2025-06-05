use miette::{IntoDiagnostic, Result, miette};
use std::io::Write;
use std::process::Command;
use std::{fs, fs::File};
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

impl ToString for BecomeUser {
    fn to_string(&self) -> String {
        let passwd = Uuid::new_v4().to_string();
        format!(
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

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    pub fn build(&mut self) -> Result<(&mut Command, String)> {
        use std::os::unix::fs::PermissionsExt;

        let args: Vec<&str> = self.cmd.get_args().filter_map(|arg| arg.to_str()).collect();
        let cmd_str = args.join(" ");
        let mut file = File::create(&self.entrypoint_file_path).into_diagnostic()?;

        let add_user = match &self.become_user {
            Some(add_user) => add_user.to_string(),
            None => "".to_string(),
        };

        let script = format!(
            r#"#!{}
wait_for_output() {{
    # Wait for the command to complete
    wait $command_pid
    exit_code=$1

    # Write the exit code to the specified file
    {}
    exit $exit_code
}}

# Function to handle signals
handle_signal() {{
    local signal=$1
    # Forward the signal to the child process if it exists
    if [ -n "$command_pid" ] && kill -0 $command_pid 2>/dev/null; then
        kill -$signal $command_pid
        wait_for_output $signal
    fi
}}

# Set up signal handling
trap 'handle_signal TERM' SIGTERM
trap 'handle_signal INT' SIGINT
trap 'handle_signal HUP' SIGHUP
{}

# Start the command and get its PID
eval '{}'
exit_code=$?
command_pid=$!

wait_for_output $exit_code
"#,
            self.shell,
            if let Some(exit_file) = &self.exit_file_path {
                format!("echo $exit_code > {}\n", exit_file)
            } else {
                String::new()
            },
            add_user,
            cmd_str
        );

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
    pub fn with_taskset(&mut self, cpu_list: Vec<u32>) -> &mut Self {
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

    pub fn with_exit_file(&mut self, exit_file_path: String) -> &mut Self {
        self.exit_file_path = Some(exit_file_path);
        self
    }

    pub fn with_become_user(&mut self, uid: u32, gid: u32, username: String) -> &mut Self {
        self.become_user = Some(BecomeUser { uid, gid, username });
        self
    }
}
