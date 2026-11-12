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

//! Table rendering. Column layouts match the Python cueadmin so existing scripts keep parsing.

use std::fmt::Write;

use opencue_proto::facility::Allocation;
use opencue_proto::host::{HardwareState, Host, LockState, Proc, ThreadMode};
use opencue_proto::job::Job;
use opencue_proto::service::Service;
use opencue_proto::show::Show;
use opencue_proto::subscription::Subscription;

use crate::format::{
    cutoff, format_duration, format_long_duration, format_mem, format_time, py_bool, py_float,
};

/// Renders running procs, one per line. `now` is the current epoch, used for runtimes.
pub fn procs(procs: &[Proc], now: i64) -> String {
    let mut out = String::new();
    let row = |out: &mut String, cells: [&str; 7]| {
        let _ = writeln!(
            out,
            "{:<10} {:<7} {:<24} {:<30} / {:<30} {:<12} {:<12}",
            cells[0], cells[1], cells[2], cells[3], cells[4], cells[5], cells[6]
        );
    };
    row(
        &mut out,
        [
            "Host", "Cores", "Memory", "Job", "Frame", "Start", "Runtime",
        ],
    );
    for proc in procs {
        let used_pct = if proc.reserved_memory > 0 {
            proc.used_memory as f64 / proc.reserved_memory as f64 * 100.0
        } else {
            0.0
        };
        row(
            &mut out,
            [
                proc.name.split('/').next().unwrap_or_default(),
                &format!("{:.2}", proc.reserved_cores),
                &format!(
                    "{} of {} ({used_pct:.2}%)",
                    format_mem(proc.used_memory),
                    format_mem(proc.reserved_memory)
                ),
                &cutoff(&proc.job_name, 30),
                &cutoff(&proc.frame_name, 30),
                &format_time(proc.dispatch_time as i64),
                &format_duration(now - proc.dispatch_time as i64),
            ],
        );
    }
    out
}

/// Renders hosts, one per line. `now` is the current epoch, used for uptime.
pub fn hosts(hosts: &[Host], now: i64) -> String {
    let mut out = String::new();
    let row = |out: &mut String, c: [&str; 15]| {
        let _ = writeln!(
            out,
            "{:<15} {:<4} {:<5} {:<8} {:<8} {:<9} {:<5} {:<5} {:<16} {:<8} {:<8} {:<6} {:<9} {:<10} {:<7}",
            c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8], c[9], c[10], c[11], c[12], c[13], c[14]
        );
    };
    row(
        &mut out,
        [
            "Host", "Load", "NIMBY", "freeMem", "freeSwap", "freeMcp", "Cores", "Mem", "Idle",
            "Os", "Uptime", "State", "Locked", "Alloc", "Thread",
        ],
    );
    for host in hosts {
        row(
            &mut out,
            [
                &host.name,
                &host.load.to_string(),
                py_bool(host.nimby_enabled),
                &format_mem(host.free_memory),
                &format_mem(host.free_swap),
                &format_mem(host.free_mcp),
                &py_float(host.cores as f64),
                &format_mem(host.memory),
                &format!(
                    "[ {:.2} / {} ]",
                    host.idle_cores,
                    format_mem(host.idle_memory)
                ),
                &host.os,
                &format_long_duration(now - host.boot_time as i64),
                HardwareState::try_from(host.state).map_or("UNKNOWN", |s| s.as_str_name()),
                LockState::try_from(host.lock_state).map_or("UNKNOWN", |s| s.as_str_name()),
                &host.alloc_name,
                ThreadMode::try_from(host.thread_mode).map_or("UNKNOWN", |s| s.as_str_name()),
            ],
        );
    }
    out
}

/// Renders shows with their stats.
pub fn shows(shows: &[Show]) -> String {
    let mut out = String::new();
    let _ = writeln!(
        out,
        "{:<8} {:<6} {:>15} {:>15} {:>15} {:>15}",
        "Show", "Active", "ReservedCores", "RunningFrames", "PendingFrames", "PendingJobs"
    );
    for show in shows {
        let stats = show.show_stats.unwrap_or_default();
        let _ = writeln!(
            out,
            "{:<8} {:<6} {:>15} {:>15} {:>15} {:>15}",
            show.name,
            py_bool(show.active),
            format!("{:.2}", stats.reserved_cores),
            stats.running_frames,
            stats.pending_frames,
            stats.pending_jobs
        );
    }
    out
}

/// Renders services. Minimum memory is given by Cuebot in KB.
pub fn services(services: &[Service]) -> String {
    let mut out = String::new();
    let _ = writeln!(
        out,
        "{:<20} {:<12} {:<20} {:<15} {:<36}",
        "Name", "Can Thread", "Min Cores Units", "Min Memory", "Tags"
    );
    for service in services {
        let _ = writeln!(
            out,
            "{:<20} {:<12} {:<20} {:<15} {:<36}",
            service.name,
            py_bool(service.threadable),
            service.min_cores,
            format_mem(service.min_memory),
            service.tags.join(" | ")
        );
    }
    out
}

/// Renders allocations, sorted by facility.
pub fn allocations(allocations: &[Allocation]) -> String {
    let mut allocations: Vec<&Allocation> = allocations.iter().collect();
    allocations.sort_by(|a, b| a.facility.cmp(&b.facility));

    let mut out = String::new();
    let _ = writeln!(
        out,
        "{:<25} {:>15} {:>8}  {:>8}  {:>8} {:>8} {:>8} {:>8} {:<8}",
        "Name", "Tag", "Running", "Avail", "Cores", "Hosts", "Locked", "Down", "Billable"
    );
    for alloc in allocations {
        let stats = alloc.stats.unwrap_or_default();
        let _ = writeln!(
            out,
            "{:<25} {:>15} {:>8}  {:>8}  {:>8} {:>8} {:>8} {:>8} {:<8}",
            alloc.name,
            alloc.tag,
            format!("{:.2}", stats.running_cores),
            format!("{:.2}", stats.available_cores),
            py_float(stats.cores as f64),
            stats.hosts,
            stats.locked_hosts,
            stats.down_hosts,
            py_bool(alloc.billable)
        );
    }
    out
}

/// Renders subscriptions under a `Subscriptions for <title>` heading. Sizes are converted from
/// core units to cores.
pub fn subscriptions(subscriptions: &[Subscription], title: &str) -> String {
    let mut out = String::new();
    let _ = writeln!(out, "Subscriptions for {title}");
    let _ = writeln!(
        out,
        "{:<30} {:<12} {:>6} {:>8} {:>8} {:>8}",
        "Allocation", "Show", "Size", "Burst", "Run", "Used"
    );
    for sub in subscriptions {
        let run = sub.reserved_cores as f64 / 100.0;
        let used = if sub.size != 0 {
            sub.reserved_cores as f64 / sub.size as f64 * 100.0
        } else {
            run
        };
        let _ = writeln!(
            out,
            "{:<30} {:<12} {:>6} {:>8} {:>8} {:>8}",
            sub.allocation_name,
            sub.show_name,
            py_float(sub.size as f64 / 100.0),
            py_float(sub.burst as f64 / 100.0),
            format!("{run:.2}"),
            format!("{used:.2}%")
        );
    }
    out
}

/// Renders jobs with their priority and core settings.
pub fn jobs(jobs: &[Job]) -> String {
    let mut out = String::new();
    let _ = writeln!(
        out,
        "{:<56} {:<15} {:>5} {:>7} {:>8} {:>5} {:>8} {:>8}",
        "Job", "Group", "Booked", "Cores", "Wait", "Pri", "MinCores", "MaxCores"
    );
    for job in jobs {
        let stats = job.job_stats.unwrap_or_default();
        let name = if job.is_paused {
            format!("{} [paused]", job.name)
        } else {
            job.name.clone()
        };
        let _ = writeln!(
            out,
            "{:<56} {:<15} {:>5} {:>7} {:>8} {:>5} {:>8} {:>8}",
            cutoff(&name, 52),
            cutoff(&job.group, 15),
            stats.running_frames,
            format!("{:.2}", stats.reserved_cores),
            stats.waiting_frames,
            job.priority,
            format!("{:.2}", job.min_cores),
            format!("{:.2}", job.max_cores)
        );
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use opencue_proto::facility::AllocationStats;
    use opencue_proto::job::JobStats;

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
        let out = procs(&[proc], 1000 + 3_723);
        let lines: Vec<&str> = out.lines().collect();
        assert!(lines[0].starts_with("Host       Cores   Memory"));
        assert!(lines[1].starts_with("host01     2.00    1.0G of 4.0G (25.00%)"));
        assert!(lines[1].contains("pipe-shot-job"));
        assert!(lines[1].contains("01:02:03"));
    }

    #[test]
    fn proc_without_reserved_memory() {
        let out = procs(&[Proc::default()], 0);
        assert!(out.contains("(0.00%)"));
    }

    #[test]
    fn host_table() {
        let host = Host {
            name: "host01".into(),
            cores: 16.0,
            idle_cores: 4.5,
            idle_memory: 2 * 1024 * 1024,
            boot_time: 0,
            state: HardwareState::Repair as i32,
            lock_state: LockState::NimbyLocked as i32,
            thread_mode: ThreadMode::Variable as i32,
            alloc_name: "local.general".into(),
            ..Default::default()
        };
        let out = hosts(&[host], 90_000);
        let row = out.lines().nth(1).unwrap();
        for expected in [
            "host01",
            "16.0",
            "[ 4.50 / 2.0G ]",
            "01:01",
            "REPAIR",
            "NIMBY_LOCKED",
            "local.general",
            "VARIABLE",
        ] {
            assert!(row.contains(expected), "{expected} missing from {row}");
        }
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
        let out = subscriptions(&[sub], "pipe");
        let lines: Vec<&str> = out.lines().collect();
        assert_eq!(lines[0], "Subscriptions for pipe");
        assert!(lines[2].contains("10.0"));
        assert!(lines[2].contains("15.0"));
        assert!(lines[2].contains("5.00"));
        assert!(lines[2].contains("50.00%"));
    }

    #[test]
    fn allocations_sorted_by_facility() {
        let alloc = |name: &str, facility: &str| Allocation {
            name: name.into(),
            facility: facility.into(),
            stats: Some(AllocationStats {
                cores: 64.0,
                ..Default::default()
            }),
            ..Default::default()
        };
        let out = allocations(&[alloc("b.one", "b"), alloc("a.two", "a")]);
        let names: Vec<&str> = out
            .lines()
            .skip(1)
            .map(|l| l.split_whitespace().next().unwrap())
            .collect();
        assert_eq!(names, ["a.two", "b.one"]);
        assert!(out.contains("64.0"));
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
        assert!(jobs(&[job]).contains("pipe-shot-job [paused]"));
    }
}
