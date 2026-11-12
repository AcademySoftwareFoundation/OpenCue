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

//! Command line definition. Every doc comment here ends up in `--help`.

use clap::builder::BoolishValueParser;
use clap::{ArgAction, Args, Parser, Subcommand, ValueEnum};

use crate::criteria::{Burst, RangeFilter};

const CONNECTION_HELP: &str = "\
Connection:
  The Cuebot address is resolved in this order:
    1. --server
    2. --facility (looked up in the config file)
    3. CUEBOT_HOSTS (comma separated)
    4. CUEBOT_FACILITY, then cuebot.facility_default from the config file

  The config file is the pycue one: OPENCUE_CONFIG_FILE, OPENCUE_CONF, or
  ~/.config/opencue/opencue.yaml.";

/// OpenCue administration tool.
///
/// Manage shows, allocations, subscriptions, hosts, jobs and procs on a Cuebot.
/// Every command is `cueadmin <NOUN> <VERB>`, for example `cueadmin host lock`.
/// Destructive commands ask for confirmation unless --force is given.
#[derive(Debug, Parser)]
#[command(name = "cueadmin", version, after_long_help = CONNECTION_HELP)]
pub struct Cli {
    /// Cuebot address to connect to, as HOST or HOST:PORT.
    ///
    /// Repeat the flag or separate addresses with commas to give fallbacks;
    /// they are tried in random order.
    #[arg(
        long,
        global = true,
        value_name = "HOST",
        value_delimiter = ',',
        help_heading = "Global Options"
    )]
    pub server: Vec<String>,

    /// Facility to connect to, as named under cuebot.facility in the config file.
    #[arg(
        long,
        global = true,
        value_name = "CODE",
        conflicts_with = "server",
        help_heading = "Global Options"
    )]
    pub facility: Option<String>,

    /// Print debug logging to stderr.
    #[arg(short, long, global = true, help_heading = "Global Options")]
    pub verbose: bool,

    /// Skip confirmation prompts.
    #[arg(
        short,
        long,
        global = true,
        visible_alias = "yes",
        short_alias = 'y',
        help_heading = "Global Options"
    )]
    pub force: bool,

    #[command(subcommand)]
    pub command: Command,
}

#[derive(Debug, Subcommand)]
pub enum Command {
    /// Manage shows.
    #[command(subcommand)]
    Show(ShowCommand),

    /// Manage allocations.
    #[command(subcommand, visible_alias = "allocation")]
    Alloc(AllocCommand),

    /// Manage show subscriptions to allocations.
    #[command(subcommand, visible_alias = "sub")]
    Subscription(SubscriptionCommand),

    /// Manage render hosts.
    #[command(subcommand)]
    Host(HostCommand),

    /// Manage jobs.
    #[command(subcommand)]
    Job(JobCommand),

    /// Inspect running procs (frames booked on hosts).
    #[command(subcommand)]
    Proc(ProcCommand),

    /// Inspect services.
    #[command(subcommand)]
    Service(ServiceCommand),
}

// ---------------------------------------------------------------------------------------------
// show
// ---------------------------------------------------------------------------------------------

#[derive(Debug, Subcommand)]
pub enum ShowCommand {
    /// List shows with their running and pending work.
    #[command(visible_alias = "ls")]
    List,

    /// Create a new show.
    Create {
        /// Name of the new show.
        show: String,
    },

    /// Delete a show.
    Delete {
        /// Show to delete.
        show: String,
    },

    /// Enable a show, allowing jobs to be launched on it.
    Enable {
        /// Show to enable.
        show: String,
    },

    /// Disable a show.
    Disable {
        /// Show to disable.
        show: String,
    },

    /// Turn frame dispatching on or off for a show.
    ///
    /// When off, no frames from the show are dispatched to hosts.
    Dispatching {
        /// Show to change.
        show: String,
        /// on or off.
        #[arg(value_name = "ON|OFF", value_parser = BoolishValueParser::new(), action = ArgAction::Set)]
        enabled: bool,
    },

    /// Turn booking on or off for a show.
    ///
    /// Booking is new proc assignment. With booking off, procs keep running
    /// frames of jobs they already have, but no new jobs get booked.
    Booking {
        /// Show to change.
        show: String,
        /// on or off.
        #[arg(value_name = "ON|OFF", value_parser = BoolishValueParser::new(), action = ArgAction::Set)]
        enabled: bool,
    },

    /// Set the default min cores for new jobs, before any filters apply.
    DefaultMinCores {
        /// Show to change.
        show: String,
        /// Number of cores.
        cores: f32,
    },

    /// Set the default max cores for new jobs, before any filters apply.
    DefaultMaxCores {
        /// Show to change.
        show: String,
        /// Number of cores.
        cores: f32,
    },

    /// Archive a show by making it an alias of another show.
    ///
    /// Jobs submitted to the archived show are run by the allocations
    /// subscribed to the target show.
    Archive {
        /// Show to archive.
        show: String,
        /// Show that takes over the archived show's jobs.
        target: String,
    },

    /// Choose which scheduler owns a show.
    ///
    /// When on, Maestro owns the show while it runs in managed mode
    /// (maestro.enabled=managed) and the legacy dispatcher skips it. Turning it
    /// on with no Maestro in managed mode strands the show: nothing dispatches it.
    SchedulerManaged {
        /// Show to change.
        show: String,
        /// on or off.
        #[arg(value_name = "ON|OFF", value_parser = BoolishValueParser::new(), action = ArgAction::Set)]
        enabled: bool,
    },
}

// ---------------------------------------------------------------------------------------------
// alloc
// ---------------------------------------------------------------------------------------------

#[derive(Debug, Subcommand)]
pub enum AllocCommand {
    /// List allocations with their core and host usage.
    #[command(visible_alias = "ls")]
    List,

    /// Create a new allocation.
    Create {
        /// Facility the allocation belongs to.
        facility: String,
        /// Allocation name, without the facility prefix.
        name: String,
        /// Host tag that places hosts into the allocation.
        tag: String,
    },

    /// Delete an allocation. It must have no hosts.
    Delete {
        /// Allocation to delete, as facility.name.
        alloc: String,
    },

    /// Rename an allocation. The facility stays the same.
    Rename {
        /// Allocation to rename, as facility.name.
        alloc: String,
        /// New name. A facility prefix, if given, is ignored.
        new_name: String,
    },

    /// Move every host of one allocation into another.
    Transfer {
        /// Allocation to take the hosts from.
        src: String,
        /// Allocation to move the hosts into.
        dst: String,
    },

    /// Change the host tag of an allocation.
    Tag {
        /// Allocation to re-tag.
        alloc: String,
        /// New host tag.
        tag: String,
    },
}

// ---------------------------------------------------------------------------------------------
// subscription
// ---------------------------------------------------------------------------------------------

#[derive(Debug, Subcommand)]
pub enum SubscriptionCommand {
    /// List subscriptions of shows, or of an allocation.
    #[command(visible_alias = "ls")]
    List {
        /// Shows to list subscriptions for.
        #[arg(value_name = "SHOW", required_unless_present = "alloc")]
        shows: Vec<String>,
        /// List every show's subscription to this allocation instead.
        #[arg(long, conflicts_with = "shows")]
        alloc: Option<String>,
    },

    /// Subscribe a show to an allocation.
    Create {
        /// Show to subscribe.
        show: String,
        /// Allocation to subscribe to.
        alloc: String,
        /// Guaranteed number of cores.
        size: f32,
        /// Maximum number of cores the show can burst to.
        burst: f32,
    },

    /// Remove a show's subscription to an allocation.
    Delete {
        /// Subscribed show.
        show: String,
        /// Subscribed allocation.
        alloc: String,
    },

    /// Set the guaranteed number of cores of a subscription.
    Size {
        /// Subscribed show.
        show: String,
        /// Subscribed allocation.
        alloc: String,
        /// Guaranteed number of cores.
        cores: f32,
    },

    /// Set the burst of a subscription.
    Burst {
        /// Subscribed show.
        show: String,
        /// Subscribed allocation.
        alloc: String,
        /// Number of cores, or a percentage of the subscription size (e.g. 20%)
        /// to add on top of it.
        #[arg(value_name = "CORES|PERCENT%")]
        burst: Burst,
    },
}

// ---------------------------------------------------------------------------------------------
// host
// ---------------------------------------------------------------------------------------------

/// Which hosts a host command operates on.
#[derive(Debug, Args)]
#[group(required = true, multiple = false)]
pub struct HostSelection {
    /// Exact names of the hosts to operate on.
    #[arg(value_name = "HOST")]
    pub hosts: Vec<String>,

    /// Operate on every host whose name contains one of these substrings.
    #[arg(short, long = "match", value_name = "SUBSTR", value_delimiter = ',')]
    pub matches: Vec<String>,
}

#[derive(Debug, Subcommand)]
pub enum HostCommand {
    /// List hosts, optionally filtered.
    #[command(visible_alias = "ls")]
    List {
        /// Only hosts whose name contains one of these substrings.
        #[arg(value_name = "SUBSTR")]
        matches: Vec<String>,
        /// Only hosts in these hardware states.
        #[arg(long, value_delimiter = ',')]
        state: Vec<HardwareState>,
        /// Only hosts in these allocations.
        #[arg(long, value_delimiter = ',')]
        alloc: Vec<String>,
        /// Only hosts in this lock state.
        #[arg(long)]
        lock_state: Option<LockState>,
        /// Sort by most idle cores and memory first, instead of by name.
        #[arg(long)]
        sort_idle: bool,
    },

    /// Lock hosts so they take no new frames.
    Lock(HostSelection),

    /// Unlock hosts.
    Unlock(HostSelection),

    /// Move hosts into another allocation.
    Move {
        /// Allocation to move the hosts into.
        alloc: String,
        #[command(flatten)]
        selection: HostSelection,
    },

    /// Delete hosts.
    Delete(HostSelection),

    /// Lock hosts and reboot them once they are idle.
    SafeReboot(HostSelection),

    /// Put hosts into the REPAIR hardware state.
    Repair(HostSelection),

    /// Put hosts back into the UP hardware state.
    #[command(visible_alias = "fixed")]
    Up(HostSelection),

    /// Set how hosts thread the frames they run.
    ThreadMode {
        /// Thread mode to set.
        mode: ThreadMode,
        #[command(flatten)]
        selection: HostSelection,
    },
}

/// Host hardware state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum HardwareState {
    Up,
    Down,
    Rebooting,
    RebootWhenIdle,
    Repair,
}

/// Host lock state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum LockState {
    Open,
    Locked,
    NimbyLocked,
}

/// Host thread mode.
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum ThreadMode {
    /// Thread frames based on the memory they reserve.
    Auto,
    /// Give every frame all the cores of the host.
    All,
    /// Let the frame decide.
    Variable,
}

// ---------------------------------------------------------------------------------------------
// job
// ---------------------------------------------------------------------------------------------

#[derive(Debug, Subcommand)]
pub enum JobCommand {
    /// List active job names, optionally filtered.
    #[command(visible_alias = "ls")]
    List {
        /// Only jobs whose name contains one of these substrings.
        #[arg(value_name = "SUBSTR")]
        matches: Vec<String>,
        /// Show a table with group, cores, waiting frames and priority.
        #[arg(short, long)]
        long: bool,
    },

    /// Pause jobs.
    Pause {
        /// Jobs to pause.
        #[arg(value_name = "JOB", required = true)]
        jobs: Vec<String>,
    },

    /// Resume paused jobs.
    #[command(visible_alias = "unpause")]
    Resume {
        /// Jobs to resume.
        #[arg(value_name = "JOB", required = true)]
        jobs: Vec<String>,
    },

    /// Kill jobs.
    Kill {
        /// Jobs to kill.
        #[arg(value_name = "JOB", required_unless_present = "all")]
        jobs: Vec<String>,
        /// Kill every active job on the Cuebot.
        #[arg(long, conflicts_with = "jobs")]
        all: bool,
        /// Reason recorded with the kill.
        #[arg(long)]
        reason: Option<String>,
    },

    /// Retry the dead frames of jobs.
    Retry {
        /// Jobs whose dead frames to retry.
        #[arg(value_name = "JOB", required_unless_present = "all")]
        jobs: Vec<String>,
        /// Retry dead frames of every active job on the Cuebot.
        #[arg(long, conflicts_with = "jobs")]
        all: bool,
    },

    /// Drop every dependency the jobs are waiting on.
    DropDepends {
        /// Jobs to release.
        #[arg(value_name = "JOB", required = true)]
        jobs: Vec<String>,
    },

    /// Set the minimum cores of a job.
    MinCores {
        /// Job to change.
        job: String,
        /// Number of cores.
        cores: f32,
    },

    /// Set the maximum cores of a job.
    MaxCores {
        /// Job to change.
        job: String,
        /// Number of cores.
        cores: f32,
    },

    /// Set the priority of a job.
    Priority {
        /// Job to change.
        job: String,
        /// New priority.
        priority: i32,
    },
}

// ---------------------------------------------------------------------------------------------
// proc
// ---------------------------------------------------------------------------------------------

/// Filters shared by the proc commands.
#[derive(Debug, Args)]
pub struct ProcFilter {
    /// Only procs of these shows.
    #[arg(long, value_delimiter = ',')]
    pub show: Vec<String>,

    /// Only procs on these hosts.
    #[arg(long, value_delimiter = ',')]
    pub host: Vec<String>,

    /// Only procs on hosts in these allocations.
    #[arg(long, value_delimiter = ',')]
    pub alloc: Vec<String>,

    /// Only procs of these jobs.
    #[arg(long, value_delimiter = ',')]
    pub job: Vec<String>,

    /// Only procs that reserved this much memory, in GB.
    ///
    /// Give a range as MIN-MAX, a lower bound as gtVALUE (or just VALUE), or
    /// an upper bound as ltVALUE.
    #[arg(long, value_name = "GB")]
    pub memory: Option<RangeFilter>,

    /// Only procs that have been running this long, in hours.
    ///
    /// Same format as --memory, e.g. 1.5, 3-4.5 or lt0.5.
    #[arg(long, value_name = "HOURS")]
    pub duration: Option<RangeFilter>,

    /// Return at most this many procs.
    #[arg(long)]
    pub limit: Option<i32>,
}

#[derive(Debug, Subcommand)]
pub enum ProcCommand {
    /// List running procs.
    #[command(visible_alias = "ls")]
    List(ProcFilter),

    /// Print the log path of each running proc, one per line.
    Logs(ProcFilter),
}

// ---------------------------------------------------------------------------------------------
// service
// ---------------------------------------------------------------------------------------------

#[derive(Debug, Subcommand)]
pub enum ServiceCommand {
    /// List the default services, or a show's service overrides.
    #[command(visible_alias = "ls")]
    List {
        /// List this show's service overrides instead of the defaults.
        #[arg(long)]
        show: Option<String>,
    },
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::CommandFactory;

    fn parse(args: &[&str]) -> Result<Cli, clap::Error> {
        Cli::try_parse_from(std::iter::once("cueadmin").chain(args.iter().copied()))
    }

    #[test]
    fn cli_is_well_formed() {
        Cli::command().debug_assert();
    }

    #[test]
    fn global_flags_go_anywhere() {
        let cli = parse(&[
            "host", "lock", "-m", "vrack", "--force", "--server", "a,b:9",
        ])
        .unwrap();
        assert!(cli.force);
        assert_eq!(cli.server, ["a", "b:9"]);
        let Command::Host(HostCommand::Lock(sel)) = cli.command else {
            panic!("wrong command")
        };
        assert_eq!(sel.matches, ["vrack"]);
        assert!(sel.hosts.is_empty());
    }

    #[test]
    fn host_commands_need_a_selection() {
        assert!(parse(&["host", "lock"]).is_err());
        assert!(parse(&["host", "lock", "h1", "-m", "vrack"]).is_err());
        assert!(parse(&["host", "move", "fac.alloc"]).is_err());
        let cli = parse(&["host", "move", "fac.alloc", "h1", "h2"]).unwrap();
        let Command::Host(HostCommand::Move { alloc, selection }) = cli.command else {
            panic!("wrong command")
        };
        assert_eq!(alloc, "fac.alloc");
        assert_eq!(selection.hosts, ["h1", "h2"]);
    }

    #[test]
    fn on_off_values() {
        for (value, expected) in [
            ("on", true),
            ("OFF", false),
            ("yes", true),
            ("false", false),
        ] {
            let cli = parse(&["show", "booking", "pipe", value]).unwrap();
            let Command::Show(ShowCommand::Booking { enabled, .. }) = cli.command else {
                panic!("wrong command")
            };
            assert_eq!(enabled, expected, "{value}");
        }
        assert!(parse(&["show", "booking", "pipe", "maybe"]).is_err());
    }

    #[test]
    fn kill_needs_jobs_or_all() {
        assert!(parse(&["job", "kill"]).is_err());
        assert!(parse(&["job", "kill", "j1", "--all"]).is_err());
        assert!(parse(&["job", "kill", "--all"]).is_ok());
        assert!(parse(&["job", "kill", "j1", "j2"]).is_ok());
    }

    #[test]
    fn subscription_list_needs_shows_or_alloc() {
        assert!(parse(&["sub", "list"]).is_err());
        assert!(parse(&["sub", "list", "pipe", "--alloc", "a"]).is_err());
        assert!(parse(&["sub", "list", "--alloc", "a"]).is_ok());
        assert!(parse(&["subscription", "ls", "pipe", "dev"]).is_ok());
    }

    #[test]
    fn server_and_facility_conflict() {
        assert!(parse(&["show", "list", "--server", "a", "--facility", "local"]).is_err());
    }
}
