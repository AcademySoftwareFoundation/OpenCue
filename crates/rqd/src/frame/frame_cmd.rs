use std::{collections::HashMap, os::unix::process::CommandExt, process::Command};

use itertools::Itertools;

pub struct FrameCmdBuilder {
    cmd: Command,
    exit_file: Option<String>,
}

impl FrameCmdBuilder {
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    pub fn new(shell: &String) -> Self {
        let mut cmd = Command::new(shell);
        cmd.arg("-c");
        Self {
            cmd,
            exit_file: None,
        }
    }

    pub fn build(&mut self) -> &mut Command {
        let args: Vec<&str> = self.cmd.get_args().filter_map(|arg| arg.to_str()).collect();
        let cmd_str = args[1..].join(" ");

        // Reset cmd to rewrite it properly.
        // self.cmd.arg(val) is used until this point loosely to collect argument without taking into
        // consideration that `-c` expects a single argument. The folowing logic recreates the command
        // unifying everything after -c.
        self.cmd = Command::new(self.cmd.get_program());
        self.cmd.arg("-c");

        if let Some(exit_file) = &self.exit_file {
            let full_command = format!(
                "{}; code=$?; echo $code > {}; exit $code",
                cmd_str, exit_file,
            );
            self.cmd.arg(full_command);
        } else {
            self.cmd.arg(cmd_str);
        }

        &mut self.cmd
    }

    /// Adds a taskset reservation for the `proc_list`:
    /// ```bash
    ///   taskset -p 1,2,3
    /// ```
    #[cfg(target_os = "linux")]
    pub fn with_taskset(&mut self, cpu_list: Vec<u32>) -> &mut Self {
        let taskset_list = cpu_list.into_iter().map(|v| v.to_string()).join(",");
        self.cmd.arg("taskset").arg("-p").arg(taskset_list.as_str());
        self
    }

    #[cfg(target_os = "macos")]
    // taskset is noop on macos. There's not a native way to allocate threads to sockets
    pub fn with_taskset(&mut self, cpu_list: Vec<u32>) -> &mut Self {
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
        self.exit_file = Some(exit_file_path);
        self
    }
}
