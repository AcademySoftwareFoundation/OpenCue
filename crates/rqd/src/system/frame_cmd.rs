use std::{collections::HashMap, os::unix::process::CommandExt, process::Command};

use itertools::Itertools;

pub struct FrameCmdBuilder {
    cmd: Command,
}

impl FrameCmdBuilder {
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    pub fn new(shell: &String) -> Self {
        let mut cmd = Command::new(shell);
        cmd.arg("-c");
        Self { cmd }
    }

    #[cfg(target_os = "windows")]
    pub fn new() -> Self {
        let mut cmd = Command::new("cmd.exe");
        cmd.arg("/c");
        Self { cmd }
    }

    pub fn build(&mut self) -> &mut Command {
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

    #[cfg(target_os = "macos")]
    pub fn with_nice(&mut self) -> &mut Self {
        self.cmd.arg("/bin/nice");
        self
    }

    #[cfg(target_os = "windows")]
    pub fn with_nice(&mut self) -> &mut Self {
        self
    }

    /// The main command requested by the frame.
    pub fn with_frame_cmd(&mut self, frame_cmd: String) -> &mut Self {
        self.cmd.arg(frame_cmd);
        self
    }
}
