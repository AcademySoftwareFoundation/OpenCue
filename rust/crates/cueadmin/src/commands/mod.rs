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

//! Command handlers, one module per noun.

use std::io::{BufRead, Write};

use miette::{IntoDiagnostic, Result};

use crate::cli::Command;
use crate::client::Cuebot;

mod alloc;
mod host;
mod job;
mod proc;
mod service;
mod show;
mod subscription;

/// Shared state for running a command.
pub struct Context {
    pub cuebot: Cuebot,
    pub force: bool,
}

impl Context {
    /// Asks the user to confirm `action`. Always true with `--force`.
    pub fn confirm(&self, action: &str) -> Result<bool> {
        if self.force {
            return Ok(true);
        }
        let stdin = std::io::stdin();
        confirm_with(action, &mut stdin.lock(), &mut std::io::stdout())
    }
}

fn confirm_with(action: &str, input: &mut impl BufRead, output: &mut impl Write) -> Result<bool> {
    write!(output, "Please confirm. {action}? [y/n] ").into_diagnostic()?;
    output.flush().into_diagnostic()?;
    let mut answer = String::new();
    input.read_line(&mut answer).into_diagnostic()?;
    let confirmed = matches!(answer.trim(), "y" | "Y" | "yes" | "YES" | "Yes");
    if !confirmed {
        writeln!(output, "Canceled").into_diagnostic()?;
    }
    Ok(confirmed)
}

/// Runs `command` against the connected Cuebot.
pub async fn run(ctx: &Context, command: Command) -> Result<()> {
    match command {
        Command::Show(cmd) => show::run(ctx, cmd).await,
        Command::Alloc(cmd) => alloc::run(ctx, cmd).await,
        Command::Subscription(cmd) => subscription::run(ctx, cmd).await,
        Command::Host(cmd) => host::run(ctx, cmd).await,
        Command::Job(cmd) => job::run(ctx, cmd).await,
        Command::Proc(cmd) => proc::run(ctx, cmd).await,
        Command::Service(cmd) => service::run(ctx, cmd).await,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn answer(input: &str) -> (bool, String) {
        let mut output = Vec::new();
        let confirmed = confirm_with("Kill 2 job(s)", &mut input.as_bytes(), &mut output).unwrap();
        (confirmed, String::from_utf8(output).unwrap())
    }

    #[test]
    fn confirmation() {
        assert_eq!(
            answer("y\n"),
            (true, "Please confirm. Kill 2 job(s)? [y/n] ".to_string())
        );
        assert!(answer("yes\n").0);
        let (confirmed, output) = answer("n\n");
        assert!(!confirmed);
        assert!(output.ends_with("Canceled\n"));
        // A closed stdin cancels instead of proceeding.
        assert!(!answer("").0);
    }
}
