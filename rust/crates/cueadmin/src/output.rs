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

//! Tables for each kind of object cueadmin lists.
//!
//! Raw columns keep exact values for scripts: memory in KB, times as epoch seconds, durations in
//! seconds, cores as plain numbers and enums by their proto names.

use opencue_proto::facility::Allocation;
use opencue_proto::host::{
    HardwareState, Host, HostLockHostsResponse, HostUnlockHostsResponse, LockState, Proc,
    ThreadMode,
};
use opencue_proto::job::Job;
use opencue_proto::service::Service;
use opencue_proto::show::Show;
use opencue_proto::subscription::Subscription;

use crate::format::{format_duration, format_mem, format_num, format_time, usage_bar};
use crate::table::{Cell, Column, Noun, Table, Tone};

const PROC_BAR_WIDTH: usize = 8;

/// A yes/no cell: `✓` or a dim `·`.
fn check(value: bool) -> Cell {
    if value {
        Cell::new("✓", true).tone(Tone::Good)
    } else {
        Cell::new("·", false).tone(Tone::Dim)
    }
}

/// Cores with two decimals, which keeps right-aligned columns lined up.
fn cores(value: f64) -> Cell {
    Cell::new(format!("{value:.2}"), format_num(value))
}

fn mem(kb: i64) -> Cell {
    Cell::new(format_mem(kb), kb)
}

/// A pretty-only cell for a totals row.
fn total(value: impl ToString) -> Cell {
    Cell::pretty(value.to_string())
}

/// Tone for a usage ratio: yellow above `warn`, red above `bad`.
fn usage_tone(ratio: f64, warn: f64, bad: f64) -> Tone {
    if ratio > bad {
        Tone::Bad
    } else if ratio > warn {
        Tone::Warn
    } else {
        Tone::Plain
    }
}

/// Converts Cuebot core units (hundredths of a core) to cores.
fn units_to_cores(units: i32) -> f64 {
    units as f64 / 100.0
}

/// Running procs. `now` is the current epoch, used for runtimes.
pub fn procs(procs: &[Proc], now: i64) -> Table {
    let mut table = Table::new(
        Noun {
            one: "proc",
            many: "procs",
        },
        &[
            Column::new("Host", "host"),
            Column::new("Job", "job"),
            Column::new("Frame", "frame"),
            Column::new("Cores", "cores").right(),
            Column::pretty("Memory"),
            Column::raw("used_memory_kb"),
            Column::raw("reserved_memory_kb"),
            Column::new("Runtime", "runtime_secs").right(),
            Column::new("Start", "start_time").wide(),
        ],
    );
    for proc in procs {
        let ratio = if proc.reserved_memory > 0 {
            proc.used_memory as f64 / proc.reserved_memory as f64
        } else {
            0.0
        };
        let runtime = now - proc.dispatch_time as i64;
        table.row(vec![
            Cell::same(proc.name.split('/').next().unwrap_or_default()),
            Cell::same(&proc.job_name),
            Cell::same(&proc.frame_name),
            cores(proc.reserved_cores as f64),
            Cell::pretty(format!(
                "{}  {} / {}",
                usage_bar(ratio, PROC_BAR_WIDTH),
                format_mem(proc.used_memory),
                format_mem(proc.reserved_memory)
            ))
            .tone(usage_tone(ratio, 0.8, 0.95)),
            Cell::raw(proc.used_memory),
            Cell::raw(proc.reserved_memory),
            Cell::new(format_duration(runtime), runtime.max(0)),
            Cell::new(format_time(proc.dispatch_time as i64), proc.dispatch_time),
        ]);
    }
    table
}

fn hardware_state(host: &Host) -> Cell {
    let state = HardwareState::try_from(host.state).ok();
    let tone = match state {
        Some(HardwareState::Up) => Tone::Good,
        Some(HardwareState::Rebooting | HardwareState::RebootWhenIdle) => Tone::Warn,
        _ => Tone::Bad,
    };
    Cell::same(state.map_or("UNKNOWN", |s| s.as_str_name())).tone(tone)
}

fn lock_state(host: &Host) -> Cell {
    let state = LockState::try_from(host.lock_state).ok();
    let tone = match state {
        Some(LockState::Open) => Tone::Plain,
        _ => Tone::Warn,
    };
    Cell::same(state.map_or("UNKNOWN", |s| s.as_str_name())).tone(tone)
}

/// Hosts. `now` is the current epoch, used for uptime.
pub fn hosts(hosts: &[Host], now: i64) -> Table {
    let mut table = Table::new(
        Noun {
            one: "host",
            many: "hosts",
        },
        &[
            Column::new("Host", "host"),
            Column::new("State", "state"),
            Column::new("Lock", "lock_state"),
            Column::new("Alloc", "alloc"),
            Column::pretty("Idle cores").right(),
            Column::raw("idle_cores"),
            Column::raw("cores"),
            Column::pretty("Idle mem").right(),
            Column::raw("idle_memory_kb"),
            Column::raw("memory_kb"),
            Column::new("Load", "load").right(),
            Column::new("Uptime", "uptime_secs").right(),
            Column::raw("boot_time"),
            Column::new("Free mem", "free_memory_kb").right().wide(),
            Column::new("Free swap", "free_swap_kb").right().wide(),
            Column::new("Free MCP", "free_mcp_kb").right().wide(),
            Column::new("OS", "os").wide(),
            Column::new("Thread", "thread_mode").wide(),
            Column::new("NIMBY", "nimby").wide(),
        ],
    );
    for host in hosts {
        let uptime = (now - host.boot_time as i64).max(0);
        let idle_tone = if host.idle_cores > 0.0 {
            Tone::Plain
        } else {
            Tone::Dim
        };
        table.row(vec![
            Cell::same(&host.name),
            hardware_state(host),
            lock_state(host),
            Cell::same(&host.alloc_name),
            Cell::pretty(format!(
                "{} / {}",
                format_num(host.idle_cores as f64),
                format_num(host.cores as f64)
            ))
            .tone(idle_tone),
            Cell::raw(format_num(host.idle_cores as f64)),
            Cell::raw(format_num(host.cores as f64)),
            Cell::pretty(format!(
                "{} / {}",
                format_mem(host.idle_memory),
                format_mem(host.memory)
            )),
            Cell::raw(host.idle_memory),
            Cell::raw(host.memory),
            Cell::same(host.load),
            Cell::new(format_duration(uptime), uptime),
            Cell::raw(host.boot_time),
            mem(host.free_memory),
            mem(host.free_swap),
            mem(host.free_mcp),
            Cell::same(&host.os),
            Cell::same(
                ThreadMode::try_from(host.thread_mode).map_or("UNKNOWN", |s| s.as_str_name()),
            ),
            check(host.nimby_enabled),
        ]);
    }
    table
}

/// Outcome of a bulk `host lock --nimby` or `host unlock --nimby`.
#[derive(Debug, Default, PartialEq)]
pub struct BulkLockOutcome {
    /// Whether this is a lock (true) or an unlock (false).
    pub locking: bool,
    /// Hosts now locked or unlocked.
    pub changed: Vec<String>,
    /// Hosts whose lock changed in Cuebot but whose RQD could not be reached.
    pub unreachable: Vec<String>,
    /// Matched hosts left alone because another source holds their lock.
    pub skipped: Vec<String>,
    /// Frames killed and returned to waiting.
    pub frames_killed: i32,
    /// Frames whose kill could not be confirmed. They keep running until their host reports
    /// them done.
    pub frames_deferred: Vec<String>,
}

impl From<HostLockHostsResponse> for BulkLockOutcome {
    fn from(r: HostLockHostsResponse) -> Self {
        Self {
            locking: true,
            changed: r.locked,
            unreachable: r.unreachable,
            skipped: r.skipped,
            frames_killed: r.frames_killed,
            frames_deferred: r.frames_deferred,
        }
    }
}

impl From<HostUnlockHostsResponse> for BulkLockOutcome {
    fn from(r: HostUnlockHostsResponse) -> Self {
        Self {
            locking: false,
            changed: r.unlocked,
            unreachable: r.unreachable,
            skipped: r.skipped,
            ..Default::default()
        }
    }
}

impl BulkLockOutcome {
    /// Counts, unreachable hosts and unconfirmed frame kills, for people.
    pub fn summary(&self) -> String {
        let mut out = if self.locking {
            format!(
                "Locked: {}, unreachable: {}, skipped: {}, frames killed: {}\n",
                self.changed.len(),
                self.unreachable.len(),
                self.skipped.len(),
                self.frames_killed
            )
        } else {
            format!(
                "Unlocked: {}, unreachable: {}, skipped: {}\n",
                self.changed.len(),
                self.unreachable.len(),
                self.skipped.len()
            )
        };
        if !self.unreachable.is_empty() {
            out.push_str(&format!(
                "Unreachable hosts: {}\n",
                self.unreachable.join(", ")
            ));
        }
        if !self.frames_deferred.is_empty() {
            out.push_str("Frames whose kill could not be confirmed (still running):\n");
            for frame in &self.frames_deferred {
                out.push_str(&format!("  {frame}\n"));
            }
        }
        out
    }

    /// Every matched host, whatever happened to it.
    pub fn matched(&self) -> impl Iterator<Item = &str> {
        self.changed
            .iter()
            .chain(&self.unreachable)
            .chain(&self.skipped)
            .map(String::as_str)
    }

    /// One row per matched host with what happened to it.
    pub fn hosts(&self) -> Table {
        let mut table = Table::new(
            Noun {
                one: "host",
                many: "hosts",
            },
            &[Column::new("Host", "host"), Column::new("Result", "result")],
        );
        let changed = if self.locking { "locked" } else { "unlocked" };
        for (names, result) in [
            (&self.changed, changed),
            (&self.unreachable, "unreachable"),
            (&self.skipped, "skipped"),
        ] {
            for name in names {
                table.row(vec![Cell::same(name), Cell::same(result)]);
            }
        }
        table
    }
}

/// Shows with their stats.
pub fn shows(shows: &[Show]) -> Table {
    let mut table = Table::new(
        Noun {
            one: "show",
            many: "shows",
        },
        &[
            Column::new("Show", "show"),
            Column::new("Active", "active"),
            Column::new("Reserved cores", "reserved_cores").right(),
            Column::new("Running frames", "running_frames").right(),
            Column::new("Pending frames", "pending_frames").right(),
            Column::new("Pending jobs", "pending_jobs").right(),
        ],
    );
    let (mut reserved, mut running, mut pending, mut jobs) = (0.0, 0i64, 0i64, 0i64);
    for show in shows {
        let stats = show.show_stats.unwrap_or_default();
        reserved += stats.reserved_cores as f64;
        running += stats.running_frames as i64;
        pending += stats.pending_frames as i64;
        jobs += stats.pending_jobs as i64;
        table.row(vec![
            Cell::same(&show.name),
            check(show.active),
            cores(stats.reserved_cores as f64),
            Cell::same(stats.running_frames),
            Cell::same(stats.pending_frames),
            Cell::same(stats.pending_jobs),
        ]);
    }
    table.totals(vec![
        total("Total"),
        Cell::default(),
        total(format!("{reserved:.2}")),
        total(running),
        total(pending),
        total(jobs),
    ]);
    table
}

/// Services. Minimum cores come from Cuebot in core units and minimum memory in KB.
pub fn services(services: &[Service]) -> Table {
    let mut table = Table::new(
        Noun {
            one: "service",
            many: "services",
        },
        &[
            Column::new("Name", "name"),
            Column::new("Threadable", "threadable"),
            Column::new("Min cores", "min_cores").right(),
            Column::new("Min memory", "min_memory_kb").right(),
            Column::new("Tags", "tags"),
        ],
    );
    for service in services {
        let min_cores = format_num(units_to_cores(service.min_cores));
        table.row(vec![
            Cell::same(&service.name),
            check(service.threadable),
            Cell::same(min_cores),
            mem(service.min_memory),
            Cell::new(service.tags.join(", "), service.tags.join(",")),
        ]);
    }
    table
}

/// Allocations, sorted by facility and then name.
pub fn allocations(allocations: &[Allocation]) -> Table {
    let mut allocations: Vec<&Allocation> = allocations.iter().collect();
    allocations.sort_by(|a, b| (&a.facility, &a.name).cmp(&(&b.facility, &b.name)));

    let mut table = Table::new(
        Noun {
            one: "allocation",
            many: "allocations",
        },
        &[
            Column::new("Name", "name"),
            Column::new("Tag", "tag"),
            Column::new("Running", "running_cores").right(),
            Column::new("Available", "available_cores").right(),
            Column::new("Cores", "cores").right(),
            Column::new("Hosts", "hosts").right(),
            Column::new("Locked", "locked_hosts").right(),
            Column::new("Down", "down_hosts").right(),
            Column::new("Billable", "billable"),
        ],
    );
    let mut sums = [0.0f64; 6];
    for alloc in allocations {
        let stats = alloc.stats.unwrap_or_default();
        let values = [
            stats.running_cores as f64,
            stats.available_cores as f64,
            stats.cores as f64,
            stats.hosts as f64,
            stats.locked_hosts as f64,
            stats.down_hosts as f64,
        ];
        for (sum, value) in sums.iter_mut().zip(values) {
            *sum += value;
        }
        table.row(vec![
            Cell::same(&alloc.name),
            Cell::same(&alloc.tag),
            cores(values[0]),
            cores(values[1]),
            Cell::same(format_num(values[2])),
            Cell::same(stats.hosts),
            Cell::same(stats.locked_hosts).tone(if stats.locked_hosts > 0 {
                Tone::Warn
            } else {
                Tone::Plain
            }),
            Cell::same(stats.down_hosts).tone(if stats.down_hosts > 0 {
                Tone::Bad
            } else {
                Tone::Plain
            }),
            check(alloc.billable),
        ]);
    }
    table.totals(vec![
        total("Total"),
        Cell::default(),
        total(format!("{:.2}", sums[0])),
        total(format!("{:.2}", sums[1])),
        total(format_num(sums[2])),
        total(sums[3]),
        total(sums[4]),
        total(sums[5]),
        Cell::default(),
    ]);
    table
}

/// Subscriptions, titled `Subscriptions for <title>` in pretty mode. Sizes are converted from
/// core units to cores.
pub fn subscriptions(subscriptions: &[Subscription], title: &str) -> Table {
    let mut table = Table::new(
        Noun {
            one: "subscription",
            many: "subscriptions",
        },
        &[
            Column::new("Allocation", "allocation"),
            Column::new("Show", "show"),
            Column::new("Size", "size").right(),
            Column::new("Burst", "burst").right(),
            Column::new("Running", "running_cores").right(),
            Column::new("Used", "used_pct").right(),
        ],
    )
    .title(format!("Subscriptions for {title}"));
    let (mut size, mut burst, mut running) = (0.0, 0.0, 0.0);
    for sub in subscriptions {
        let sub_size = units_to_cores(sub.size);
        let sub_running = units_to_cores(sub.reserved_cores);
        size += sub_size;
        burst += units_to_cores(sub.burst);
        running += sub_running;
        let used = if sub.size != 0 {
            sub.reserved_cores as f64 / sub.size as f64
        } else {
            0.0
        };
        table.row(vec![
            Cell::same(&sub.allocation_name),
            Cell::same(&sub.show_name),
            Cell::same(format_num(sub_size)),
            Cell::same(format_num(units_to_cores(sub.burst))),
            cores(sub_running),
            Cell::new(format!("{:.0}%", used * 100.0), format_num(used * 100.0))
                .tone(usage_tone(used, 0.8, 1.0)),
        ]);
    }
    table.totals(vec![
        total("Total"),
        Cell::default(),
        total(format_num(size)),
        total(format_num(burst)),
        total(format!("{running:.2}")),
        Cell::default(),
    ]);
    table
}

/// Jobs with their priority and core settings. Paused jobs are dimmed.
pub fn jobs(jobs: &[Job]) -> Table {
    let mut table = Table::new(
        Noun {
            one: "job",
            many: "jobs",
        },
        &[
            Column::new("Job", "job"),
            Column::raw("paused"),
            Column::new("Group", "group"),
            Column::new("Running", "running_frames").right(),
            Column::new("Cores", "reserved_cores").right(),
            Column::new("Waiting", "waiting_frames").right(),
            Column::new("Priority", "priority").right(),
            Column::new("Min cores", "min_cores").right().wide(),
            Column::new("Max cores", "max_cores").right().wide(),
        ],
    );
    for job in jobs {
        let stats = job.job_stats.unwrap_or_default();
        let name = if job.is_paused {
            format!("{} (paused)", job.name)
        } else {
            job.name.clone()
        };
        let mut row = vec![
            Cell::new(name, &job.name),
            Cell::raw(job.is_paused),
            Cell::same(&job.group),
            Cell::same(stats.running_frames),
            cores(stats.reserved_cores as f64),
            Cell::same(stats.waiting_frames),
            Cell::same(job.priority),
            cores(job.min_cores as f64),
            cores(job.max_cores as f64),
        ];
        if job.is_paused {
            row = row.into_iter().map(|c| c.tone(Tone::Dim)).collect();
        }
        table.row(row);
    }
    table
}

#[cfg(test)]
mod tests {
    use super::*;
    use opencue_proto::facility::AllocationStats;
    use opencue_proto::job::JobStats;

    fn raw_row(table: &Table, index: usize) -> Vec<String> {
        table
            .to_raw()
            .lines()
            .nth(index + 1)
            .unwrap()
            .split('\t')
            .map(str::to_string)
            .collect()
    }

    fn raw_header(table: &Table) -> Vec<String> {
        let raw = table.to_raw();
        raw.lines()
            .next()
            .unwrap()
            .split('\t')
            .map(str::to_string)
            .collect()
    }

    #[test]
    fn proc_table() {
        let proc = Proc {
            name: "host01/0".into(),
            job_name: "pipe-shot-job".into(),
            frame_name: "0001-render".into(),
            reserved_cores: 2.0,
            reserved_memory: 4 * 1024 * 1024,
            used_memory: 1024 * 1024,
            dispatch_time: 1000,
            ..Default::default()
        };
        let table = procs(&[proc], 1000 + 3_723);
        let pretty = table.to_pretty(false, false);
        assert!(pretty.contains("██░░░░░░  1.0G / 4.0G"), "{pretty}");
        assert!(pretty.contains("1h 02m"));
        assert!(!pretty.contains("Start"));
        assert!(table.to_pretty(true, false).contains("Start"));
        assert_eq!(
            raw_row(&table, 0),
            [
                "host01",
                "pipe-shot-job",
                "0001-render",
                "2",
                "1048576",
                "4194304",
                "3723",
                "1000"
            ]
        );
    }

    #[test]
    fn proc_without_reserved_memory() {
        let pretty = procs(&[Proc::default()], 0).to_pretty(false, false);
        assert!(pretty.contains("░░░░░░░░"));
    }

    #[test]
    fn host_table() {
        let host = Host {
            name: "host01".into(),
            cores: 16.0,
            idle_cores: 4.5,
            memory: 64 * 1024 * 1024,
            idle_memory: 2 * 1024 * 1024,
            boot_time: 0,
            state: HardwareState::Repair as i32,
            lock_state: LockState::NimbyLocked as i32,
            thread_mode: ThreadMode::Variable as i32,
            alloc_name: "local.general".into(),
            ..Default::default()
        };
        let table = hosts(&[host], 90_000);
        let pretty = table.to_pretty(false, false);
        for expected in [
            "host01",
            "REPAIR",
            "NIMBY_LOCKED",
            "local.general",
            "4.5 / 16",
            "2.0G / 64.0G",
            "1d 1h",
        ] {
            assert!(
                pretty.contains(expected),
                "{expected} missing from {pretty}"
            );
        }
        assert!(!pretty.contains("VARIABLE"));
        assert!(table.to_pretty(true, false).contains("VARIABLE"));

        let header = raw_header(&table);
        let row = raw_row(&table, 0);
        let field = |key: &str| &row[header.iter().position(|h| h == key).unwrap()];
        assert_eq!(field("idle_cores"), "4.5");
        assert_eq!(field("memory_kb"), "67108864");
        assert_eq!(field("uptime_secs"), "90000");
        assert_eq!(field("thread_mode"), "VARIABLE");
        assert_eq!(field("nimby"), "false");
    }

    #[test]
    fn bulk_lock_outcome() {
        let outcome = BulkLockOutcome::from(HostLockHostsResponse {
            locked: vec!["ws1".into(), "ws2".into()],
            unreachable: vec!["ws3".into()],
            skipped: vec!["ws4".into()],
            frames_killed: 5,
            frames_deferred: vec!["0042-comp".into()],
        });
        assert_eq!(
            outcome.summary(),
            "Locked: 2, unreachable: 1, skipped: 1, frames killed: 5\n\
             Unreachable hosts: ws3\n\
             Frames whose kill could not be confirmed (still running):\n  0042-comp\n"
        );
        let table = outcome.hosts();
        assert_eq!(raw_header(&table), ["host", "result"]);
        assert_eq!(raw_row(&table, 0), ["ws1", "locked"]);
        assert_eq!(raw_row(&table, 2), ["ws3", "unreachable"]);
        assert_eq!(raw_row(&table, 3), ["ws4", "skipped"]);
        assert_eq!(
            outcome.matched().collect::<Vec<_>>(),
            ["ws1", "ws2", "ws3", "ws4"]
        );

        let outcome = BulkLockOutcome::from(HostUnlockHostsResponse {
            unlocked: vec!["ws1".into()],
            unreachable: vec![],
            skipped: vec!["ws4".into()],
        });
        assert_eq!(
            outcome.summary(),
            "Unlocked: 1, unreachable: 0, skipped: 1\n"
        );
        assert_eq!(raw_row(&outcome.hosts(), 0), ["ws1", "unlocked"]);
    }

    #[test]
    fn subscription_table() {
        let sub = Subscription {
            allocation_name: "local.general".into(),
            show_name: "pipe".into(),
            size: 1000,
            burst: 1500,
            reserved_cores: 500,
            ..Default::default()
        };
        let table = subscriptions(&[sub], "pipe");
        let pretty = table.to_pretty(false, false);
        assert!(pretty.starts_with("Subscriptions for pipe\n"));
        for expected in ["10", "15", "5.00", "50%", "Total"] {
            assert!(
                pretty.contains(expected),
                "{expected} missing from {pretty}"
            );
        }
        assert_eq!(
            raw_row(&table, 0),
            ["local.general", "pipe", "10", "15", "5", "50"]
        );
    }

    #[test]
    fn allocations_sorted_with_totals() {
        let alloc = |name: &str, facility: &str| Allocation {
            name: name.into(),
            facility: facility.into(),
            stats: Some(AllocationStats {
                cores: 64.0,
                hosts: 4,
                ..Default::default()
            }),
            ..Default::default()
        };
        let table = allocations(&[alloc("b.one", "b"), alloc("a.two", "a")]);
        assert_eq!(raw_row(&table, 0)[0], "a.two");
        assert_eq!(raw_row(&table, 1)[0], "b.one");
        let pretty = table.to_pretty(false, false);
        assert!(pretty.contains("128"), "{pretty}");
        assert!(pretty.ends_with("2 allocations\n"));
    }

    #[test]
    fn paused_jobs_are_marked() {
        let job = Job {
            name: "pipe-shot-job".into(),
            is_paused: true,
            priority: 100,
            job_stats: Some(JobStats::default()),
            ..Default::default()
        };
        let table = jobs(&[job]);
        assert!(table
            .to_pretty(false, false)
            .contains("pipe-shot-job (paused)"));
        assert_eq!(raw_row(&table, 0)[..2], ["pipe-shot-job", "true"]);
    }

    #[test]
    fn service_cores_in_cores() {
        let service = Service {
            name: "maya".into(),
            min_cores: 150,
            min_memory: 3 * 1024 * 1024,
            tags: vec!["general".into(), "desktop".into()],
            ..Default::default()
        };
        let table = services(&[service]);
        let pretty = table.to_pretty(false, false);
        assert!(pretty.contains("1.5") && pretty.contains("3.0G"));
        assert!(pretty.contains("general, desktop"));
        assert_eq!(
            raw_row(&table, 0)[2..],
            ["1.5", "3145728", "general,desktop"]
        );
    }
}
