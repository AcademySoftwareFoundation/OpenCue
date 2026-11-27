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

//! Per-frame cgroup v2 containment.
//!
//! With `runner.frame_cgroups` enabled on a Linux host with cgroup v2 and a delegated service
//! cgroup (`Delegate=yes`), rqd lays out its service cgroup as:
//!
//! ```text
//! <service>                     rqd itself
//! <service>/frames/<launch_id>  one cgroup per frame launch
//! ```
//!
//! A cgroup is named after the launch of a frame (`RunningFrame::launch_id`), not the frame id:
//! a frame retried on this host gets a cgroup of its own, so a kill still in progress for an
//! earlier run never reaches the retry.
//!
//! No controller is enabled below the service cgroup. Containment only needs the core interface
//! files (`cgroup.procs`, `cgroup.events`, `cgroup.kill`, `cgroup.freeze`), and enabling a domain
//! controller such as `memory` in `<service>/cgroup.subtree_control` would make the kernel refuse
//! new processes in `<service>` itself. systemd older than 254 starts a restarted rqd exactly
//! there, so the restart would fail.
//!
//! Every process a frame starts stays in the frame's cgroup whatever its session or process
//! group, so rqd can account for, signal and kill all of them, and reap what is left behind when
//! the frame's wrapper exits.
//!
//! The module only operates on cgroupfs files, so it builds on every unix target and its logic is
//! tested against a fake cgroupfs in a temp dir. It is only ever enabled on Linux.

#![cfg_attr(not(target_os = "linux"), allow(dead_code))]

use std::{
    collections::{HashMap, HashSet},
    fs::{self, File, OpenOptions},
    io::{self, Write},
    os::fd::RawFd,
    path::{Path, PathBuf},
    sync::OnceLock,
    time::{Duration, Instant},
};

use futures::future::join_all;
use miette::{miette, Result};
use nix::{
    errno::Errno,
    sys::signal::{kill, Signal},
    unistd::Pid,
};
use tracing::{debug, info, warn};
use uuid::Uuid;

const CGROUP_MOUNT: &str = "/sys/fs/cgroup";
const SELF_CGROUP: &str = "/proc/self/cgroup";
const FRAMES_CGROUP: &str = "frames";
/// How long a killed cgroup gets to empty before rqd gives up on removing it.
const REAP_TIMEOUT: Duration = Duration::from_secs(5);
const REAP_POLL_INTERVAL: Duration = Duration::from_millis(50);
/// Passes of the signal-based kill fallback, each one catching processes forked during the
/// previous pass.
const SIGNAL_KILL_PASSES: usize = 10;

static FRAME_CGROUPS: OnceLock<Option<FrameCgroups>> = OnceLock::new();

/// Sets up frame cgroups for this rqd instance when `enabled` by creating `<service>/frames`.
///
/// When the host can't contain frames (no cgroup v2, or a service cgroup that isn't delegated)
/// a warning is logged and frames are tracked by session, as when disabled. Must be called once
/// at startup, before any frame is launched or recovered.
pub fn init(enabled: bool) {
    let frame_cgroups = if enabled { setup_from_host() } else { None };
    if FRAME_CGROUPS.set(frame_cgroups).is_err() {
        warn!("Frame cgroups have already been initialized");
    }
}

fn setup_from_host() -> Option<FrameCgroups> {
    let setup = fs::read_to_string(SELF_CGROUP)
        .map_err(|err| miette!("Failed to read {SELF_CGROUP}: {err}"))
        .and_then(|own_cgroup| FrameCgroups::setup(Path::new(CGROUP_MOUNT), &own_cgroup));
    match setup {
        Ok(frame_cgroups) => {
            info!(
                "Frame cgroups enabled under {}",
                frame_cgroups.path.display()
            );
            Some(frame_cgroups)
        }
        Err(err) => {
            warn!(
                "runner.frame_cgroups is enabled but frame cgroups are unavailable, frames will \
                 be tracked by session. {err}"
            );
            None
        }
    }
}

/// Frame cgroups set up by [`init`], or `None` when the feature is disabled or unavailable.
pub fn frame_cgroups() -> Option<&'static FrameCgroups> {
    FRAME_CGROUPS.get().and_then(Option::as_ref)
}

/// Moves the calling process into the cgroup whose `cgroup.procs` is open as `procs_fd` (see
/// [`FrameCgroup::open_procs`]).
///
/// Safe to call from a `pre_exec` closure: it only issues a `write(2)`, which is
/// async-signal-safe, and doesn't allocate.
pub fn join(procs_fd: RawFd) -> io::Result<()> {
    // Writing "0" moves the writing process.
    let written = unsafe { libc::write(procs_fd, b"0".as_ptr().cast(), 1) };
    if written < 0 {
        Err(io::Error::last_os_error())
    } else {
        Ok(())
    }
}

/// The cgroup holding one child cgroup per frame (`<service>/frames`).
#[derive(Debug, Clone)]
pub struct FrameCgroups {
    path: PathBuf,
}

impl FrameCgroups {
    /// Creates `<service>/frames` in the delegated service cgroup rqd runs in, `own_cgroup` being
    /// the content of rqd's `/proc/self/cgroup` and `mount` the cgroup v2 mount point. rqd stays
    /// in the service cgroup and no controller is enabled (see the module docs).
    fn setup(mount: &Path, own_cgroup: &str) -> Result<Self> {
        if !mount.join("cgroup.controllers").exists() {
            return Err(miette!("cgroup v2 is not mounted at {}", mount.display()));
        }
        let frames = service_cgroup(mount, own_cgroup)?.join(FRAMES_CGROUP);
        create_cgroup_dir(&frames).map_err(|err| {
            miette!(
                "Failed to create {}: {err}. Is the service cgroup delegated (Delegate=yes)?",
                frames.display()
            )
        })?;
        Ok(Self { path: frames })
    }

    #[cfg(test)]
    pub(crate) fn at(path: impl Into<PathBuf>) -> Self {
        Self { path: path.into() }
    }

    fn frame_path(&self, launch_id: &Uuid) -> PathBuf {
        self.path.join(launch_id.to_string())
    }

    /// Creates the cgroup of the frame launch `launch_id`.
    pub fn create(&self, launch_id: &Uuid) -> Result<FrameCgroup> {
        let path = self.frame_path(launch_id);
        fs::create_dir(&path)
            .map_err(|err| miette!("Failed to create cgroup {}: {err}", path.display()))?;
        Ok(FrameCgroup { path })
    }

    /// Opens the cgroup of the frame launch `launch_id`, or returns `None` when the launch
    /// didn't get one or it has been removed.
    ///
    /// Fails when the cgroup can't be looked up, or when something other than a directory sits
    /// at its path: neither tells whether the launch still has processes.
    pub fn open(&self, launch_id: &Uuid) -> Result<Option<FrameCgroup>> {
        let path = self.frame_path(launch_id);
        match fs::metadata(&path) {
            Ok(metadata) if metadata.is_dir() => Ok(Some(FrameCgroup { path })),
            Ok(_) => Err(miette!("{} is not a cgroup directory", path.display())),
            Err(err) if err.kind() == io::ErrorKind::NotFound => Ok(None),
            Err(err) => Err(miette!(
                "Failed to look up cgroup {}: {err}",
                path.display()
            )),
        }
    }

    /// The launch id of the frame cgroup process `pid` runs in, read from `/proc/<pid>/cgroup`.
    /// `None` when the process is gone or isn't in a frame cgroup. Fails when that can't be told,
    /// the file being unreadable or the frame cgroup failing to be looked up.
    pub fn launch_of(&self, pid: u32) -> Result<Option<Uuid>> {
        self.launch_from(Path::new(&format!("/proc/{pid}/cgroup")))
    }

    /// [`Self::launch_of`] for the `/proc/<pid>/cgroup` file at `path`.
    fn launch_from(&self, path: &Path) -> Result<Option<Uuid>> {
        match fs::read_to_string(path) {
            Ok(proc_cgroup) => self.launch_in(&proc_cgroup),
            // A process that exits while its file is read fails the read with ESRCH
            Err(err)
                if err.kind() == io::ErrorKind::NotFound
                    || err.raw_os_error() == Some(Errno::ESRCH as i32) =>
            {
                Ok(None)
            }
            Err(err) => Err(miette!("Failed to read {}: {err}", path.display())),
        }
    }

    /// The launch id of the frame cgroup named by a `/proc/<pid>/cgroup` content.
    fn launch_in(&self, proc_cgroup: &str) -> Result<Option<Uuid>> {
        let launch_id = proc_cgroup
            .lines()
            .find_map(|line| line.strip_prefix("0::"))
            .and_then(|cgroup| Path::new(cgroup.trim()).file_name()?.to_str())
            .and_then(|name| Uuid::parse_str(name).ok());
        let Some(launch_id) = launch_id else {
            return Ok(None);
        };
        Ok(self.open(&launch_id)?.map(|_| launch_id))
    }

    /// Frame cgroups that don't belong to any of `launch_ids`.
    ///
    /// Meant for startup, after snapshot recovery, with the launch ids of the recovered frames:
    /// any other frame cgroup holds processes of a frame rqd has lost track of. Taken before
    /// any frame is launched, the list can't include a new launch, which gets a cgroup of its
    /// own. Reap them with [`reap_orphans`].
    pub fn orphans(&self, launch_ids: &[Uuid]) -> Result<Vec<FrameCgroup>> {
        let known: HashSet<String> = launch_ids.iter().map(Uuid::to_string).collect();
        let entries = fs::read_dir(&self.path)
            .map_err(|err| miette!("Failed to list {}: {err}", self.path.display()))?;
        Ok(entries
            .flatten()
            .filter(|entry| entry.file_type().is_ok_and(|file_type| file_type.is_dir()))
            .filter(|entry| !known.contains(entry.file_name().to_string_lossy().as_ref()))
            .map(|entry| FrameCgroup { path: entry.path() })
            .collect())
    }
}

/// Kills and removes the orphan frame cgroups found by [`FrameCgroups::orphans`], concurrently,
/// logging the outcome for each.
pub async fn reap_orphans(orphans: Vec<FrameCgroup>) {
    join_all(orphans.iter().map(|orphan| async move {
        match orphan.reap().await {
            Ok(count) => info!(
                "Removed orphan frame cgroup {}, killed {count} leftover processes",
                orphan.path.display()
            ),
            Err(err) => warn!("Failed to reap orphan frame cgroup. {err}"),
        }
    }))
    .await;
}

/// The cgroup of a single frame launch (`<service>/frames/<launch_id>`).
#[derive(Debug, Clone)]
pub struct FrameCgroup {
    path: PathBuf,
}

impl FrameCgroup {
    /// Opens `cgroup.procs` so a child can join the cgroup before exec (see [`join`]). The file
    /// is close-on-exec, so it doesn't leak into the frame.
    pub fn open_procs(&self) -> Result<File> {
        let procs = self.path.join("cgroup.procs");
        OpenOptions::new()
            .write(true)
            .open(&procs)
            .map_err(|err| miette!("Failed to open {}: {err}", procs.display()))
    }

    /// Pids of the processes in the cgroup.
    pub fn pids(&self) -> Result<Vec<u32>> {
        let procs = self.path.join("cgroup.procs");
        fs::read_to_string(&procs)
            .map(|content| parse_pids(&content))
            .map_err(|err| miette!("Failed to read {}: {err}", procs.display()))
    }

    /// Whether any process is left in the cgroup.
    pub fn is_populated(&self) -> Result<bool> {
        let events = self.path.join("cgroup.events");
        let content = fs::read_to_string(&events)
            .map_err(|err| miette!("Failed to read {}: {err}", events.display()))?;
        parse_populated(&content)
            .ok_or_else(|| miette!("No populated entry in {}", events.display()))
    }

    /// Sends `signal` to every process in the cgroup and returns how many were signalled.
    /// Processes that exit in the meantime are skipped.
    pub fn signal(&self, signal: Signal) -> Result<usize> {
        let mut signalled = 0;
        let mut failed = Vec::new();
        for pid in self.pids()? {
            match kill(Pid::from_raw(pid as i32), signal) {
                Ok(()) => signalled += 1,
                Err(Errno::ESRCH) => {}
                Err(err) => failed.push((pid, err)),
            }
        }
        if failed.is_empty() {
            Ok(signalled)
        } else {
            Err(miette!(
                "Failed to send {signal} to {:?} in {}",
                failed,
                self.path.display()
            ))
        }
    }

    /// SIGKILLs every process in the cgroup through `cgroup.kill`.
    ///
    /// Kernels older than 5.14 lack `cgroup.kill`. There the cgroup is frozen, when the kernel
    /// supports it, so nothing can fork while its processes are SIGKILLed one by one.
    pub fn kill(&self) -> Result<()> {
        match write_cgroup_file(&self.path.join("cgroup.kill"), "1") {
            Ok(()) => Ok(()),
            Err(err) if err.kind() == io::ErrorKind::NotFound => self.kill_by_signal(),
            Err(err) => Err(miette!("Failed to kill {}: {err}", self.path.display())),
        }
    }

    fn kill_by_signal(&self) -> Result<()> {
        let freeze = self.path.join("cgroup.freeze");
        let frozen = write_cgroup_file(&freeze, "1").is_ok();
        let mut killed = HashSet::new();
        let mut failed = HashMap::new();
        let mut result = Ok(());
        for _ in 0..SIGNAL_KILL_PASSES {
            let pids = match self.pids() {
                Ok(pids) => pids,
                Err(err) => {
                    result = Err(err);
                    break;
                }
            };
            let new_pids: Vec<u32> = pids
                .into_iter()
                .filter(|pid| !killed.contains(pid) && !failed.contains_key(pid))
                .collect();
            if new_pids.is_empty() {
                break;
            }
            for pid in new_pids {
                match kill(Pid::from_raw(pid as i32), Signal::SIGKILL) {
                    Ok(()) | Err(Errno::ESRCH) => {
                        killed.insert(pid);
                    }
                    Err(err) => {
                        failed.insert(pid, err);
                    }
                }
            }
        }
        // A fatal signal gets through the freezer. Thawing only keeps anything that survived
        // from staying frozen.
        if frozen {
            let _ = write_cgroup_file(&freeze, "0");
        }
        result?;
        if failed.is_empty() {
            Ok(())
        } else {
            let mut failed: Vec<(u32, Errno)> = failed.into_iter().collect();
            failed.sort_unstable_by_key(|&(pid, _)| pid);
            Err(miette!(
                "Failed to send {} to {:?} in {}",
                Signal::SIGKILL,
                failed,
                self.path.display()
            ))
        }
    }

    /// Removes the cgroup, which fails while processes are left in it.
    pub fn remove(&self) -> Result<()> {
        match fs::remove_dir(&self.path) {
            Ok(()) => Ok(()),
            Err(err) if err.kind() == io::ErrorKind::NotFound => Ok(()),
            Err(err) => Err(miette!("Failed to remove {}: {err}", self.path.display())),
        }
    }

    /// Waits until the cgroup is confirmed to have no process left, it is gone or `deadline`
    /// passes, whichever comes first. A failed read of `cgroup.events` doesn't end the wait, as
    /// the cgroup may still be populated.
    pub async fn wait_empty(&self, deadline: Instant) {
        let mut warned = false;
        while self.path.exists() && Instant::now() < deadline {
            match self.is_populated() {
                Ok(false) => return,
                Ok(true) => {}
                Err(err) if !warned => {
                    warned = true;
                    warn!(
                        "Waiting on {} to empty until the deadline. {err}",
                        self.path.display()
                    );
                }
                Err(err) => debug!("{err}"),
            }
            tokio::time::sleep(REAP_POLL_INTERVAL).await;
        }
    }

    /// Kills whatever is left in the cgroup, waits for it to empty and removes it. Returns the
    /// number of processes that were left.
    pub async fn reap(&self) -> Result<usize> {
        if !self.path.exists() {
            return Ok(0);
        }
        let leftover = self.pids()?.len();
        if self.is_populated()? {
            self.kill()?;
            let deadline = Instant::now() + REAP_TIMEOUT;
            while self.is_populated()? {
                if Instant::now() >= deadline {
                    return Err(miette!(
                        "{} still has processes {}s after being killed",
                        self.path.display(),
                        REAP_TIMEOUT.as_secs()
                    ));
                }
                tokio::time::sleep(REAP_POLL_INTERVAL).await;
            }
        }
        self.remove()?;
        Ok(leftover)
    }
}

/// Resolves the service cgroup from rqd's own `/proc/self/cgroup` entry.
fn service_cgroup(mount: &Path, own_cgroup: &str) -> Result<PathBuf> {
    let relative = own_cgroup
        .lines()
        .find_map(|line| line.strip_prefix("0::"))
        .ok_or_else(|| miette!("No cgroup v2 entry in {SELF_CGROUP}"))?;
    let service = mount.join(relative.trim().trim_start_matches('/'));
    if service == mount {
        return Err(miette!(
            "rqd runs in the root cgroup, frame cgroups need a delegated service cgroup"
        ));
    }
    Ok(service)
}

fn create_cgroup_dir(path: &Path) -> io::Result<()> {
    match fs::create_dir(path) {
        Err(err) if err.kind() == io::ErrorKind::AlreadyExists => Ok(()),
        result => result,
    }
}

/// Writes to an existing cgroup interface file. Never creates it: a missing interface file means
/// the kernel lacks the feature.
fn write_cgroup_file(path: &Path, value: &str) -> io::Result<()> {
    OpenOptions::new()
        .write(true)
        .open(path)?
        .write_all(value.as_bytes())
}

/// Parses `cgroup.procs`, which may list a pid more than once.
fn parse_pids(procs: &str) -> Vec<u32> {
    let mut pids: Vec<u32> = procs
        .lines()
        .filter_map(|line| line.trim().parse().ok())
        // Signalling pid 0 would hit rqd's own process group.
        .filter(|&pid| pid != 0)
        .collect();
    pids.sort_unstable();
    pids.dedup();
    pids
}

fn parse_populated(events: &str) -> Option<bool> {
    events
        .lines()
        .find_map(|line| line.strip_prefix("populated "))
        .map(|value| value.trim() == "1")
}

#[cfg(test)]
mod tests {
    use std::{
        os::{fd::AsRawFd, unix::process::ExitStatusExt},
        process::{Child, Command},
    };

    use tempfile::TempDir;

    use super::*;

    fn sleeper() -> Child {
        Command::new("sleep")
            .arg("30")
            .spawn()
            .expect("spawn sleep")
    }

    fn write(path: &Path, content: &str) {
        fs::write(path, content).expect("write fake cgroup file");
    }

    fn read(path: &Path) -> String {
        fs::read_to_string(path).expect("read fake cgroup file")
    }

    /// A fake cgroupfs with a delegated service cgroup, as systemd lays it out.
    fn fake_cgroupfs() -> (TempDir, PathBuf) {
        let mount = TempDir::new().expect("temp dir");
        write(
            &mount.path().join("cgroup.controllers"),
            "cpuset cpu io memory pids",
        );
        let service = mount.path().join("system.slice/openrqd.service");
        fs::create_dir_all(&service).expect("create service cgroup");
        write(&service.join("cgroup.controllers"), "cpu io memory pids");
        write(&service.join("cgroup.subtree_control"), "");
        write(&service.join("cgroup.procs"), "");
        (mount, service)
    }

    #[test]
    fn parses_pids_skipping_blank_and_zero_entries() {
        assert_eq!(parse_pids("12\n\n345\n0\n"), vec![12, 345]);
        assert_eq!(parse_pids("345\n12\n345\n"), vec![12, 345]);
        assert!(parse_pids("").is_empty());
    }

    #[test]
    fn parses_populated_from_events() {
        assert_eq!(parse_populated("populated 1\nfrozen 0\n"), Some(true));
        assert_eq!(parse_populated("populated 0\nfrozen 0\n"), Some(false));
        assert_eq!(parse_populated("frozen 0\n"), None);
    }

    #[test]
    fn resolves_service_cgroup_from_own_cgroup() {
        let mount = Path::new("/sys/fs/cgroup");
        assert_eq!(
            service_cgroup(mount, "0::/system.slice/openrqd.service\n").unwrap(),
            mount.join("system.slice/openrqd.service")
        );
        // Hybrid hosts list v1 hierarchies before the v2 entry.
        assert_eq!(
            service_cgroup(
                mount,
                "12:memory:/system.slice/openrqd.service\n0::/system.slice/openrqd.service\n"
            )
            .unwrap(),
            mount.join("system.slice/openrqd.service")
        );
    }

    #[test]
    fn refuses_root_or_v1_only_cgroups() {
        let mount = Path::new("/sys/fs/cgroup");
        assert!(service_cgroup(mount, "0::/\n").is_err());
        assert!(service_cgroup(mount, "4:memory:/system.slice/openrqd.service\n").is_err());
    }

    #[test]
    fn setup_creates_frames_without_enabling_controllers() {
        let (mount, service) = fake_cgroupfs();

        let frame_cgroups =
            FrameCgroups::setup(mount.path(), "0::/system.slice/openrqd.service\n").expect("setup");

        assert_eq!(frame_cgroups.path, service.join(FRAMES_CGROUP));
        assert!(frame_cgroups.path.is_dir());
        // rqd stays in the service cgroup, which must not hand controllers down: that would keep
        // systemd from starting a restarted rqd there.
        assert_eq!(read(&service.join("cgroup.subtree_control")), "");
        assert_eq!(read(&service.join("cgroup.procs")), "");
    }

    #[test]
    fn setup_requires_cgroup_v2() {
        let (mount, _) = fake_cgroupfs();
        fs::remove_file(mount.path().join("cgroup.controllers")).unwrap();

        assert!(FrameCgroups::setup(mount.path(), "0::/system.slice/openrqd.service\n").is_err());
    }

    #[test]
    fn setup_requires_a_writable_service_cgroup() {
        if unsafe { libc::geteuid() } == 0 {
            // Permissions don't stop root.
            return;
        }
        use std::os::unix::fs::PermissionsExt;
        let (mount, service) = fake_cgroupfs();
        fs::set_permissions(&service, fs::Permissions::from_mode(0o555)).unwrap();

        let result = FrameCgroups::setup(mount.path(), "0::/system.slice/openrqd.service\n");

        fs::set_permissions(&service, fs::Permissions::from_mode(0o755)).unwrap();
        assert!(result.is_err());
    }

    #[test]
    fn creates_and_opens_frame_cgroups() {
        let dir = TempDir::new().unwrap();
        let frame_cgroups = FrameCgroups::at(dir.path());
        let launch_id = Uuid::new_v4();

        assert!(frame_cgroups.open(&launch_id).unwrap().is_none());
        let cgroup = frame_cgroups.create(&launch_id).expect("create");

        assert_eq!(cgroup.path, dir.path().join(launch_id.to_string()));
        assert!(frame_cgroups.open(&launch_id).unwrap().is_some());
        assert!(frame_cgroups.open(&Uuid::new_v4()).unwrap().is_none());
    }

    #[test]
    fn open_fails_when_the_cgroup_cant_be_looked_up() {
        // Only a missing cgroup means the launch has none: any other error says nothing about
        // its processes.
        let dir = TempDir::new().unwrap();
        let not_a_dir = dir.path().join("frames");
        write(&not_a_dir, "");
        let launch_id = Uuid::new_v4();

        // ENOTDIR
        assert!(FrameCgroups::at(&not_a_dir).open(&launch_id).is_err());
        // Something other than a cgroup directory at the cgroup's path
        let frame_cgroups = FrameCgroups::at(dir.path());
        write(&dir.path().join(launch_id.to_string()), "");
        assert!(frame_cgroups.open(&launch_id).is_err());
    }

    #[test]
    fn a_retry_never_resolves_to_the_cgroup_of_an_earlier_run() {
        // Kill monitors and stats look a frame's cgroup up again on every tick. A frame killed
        // and retried on this host must not have the earlier run's lookups reach the retry.
        let dir = TempDir::new().unwrap();
        let frame_cgroups = FrameCgroups::at(dir.path());
        let (first_run, retry) = (Uuid::new_v4(), Uuid::new_v4());
        frame_cgroups.create(&first_run).unwrap().remove().unwrap();

        let retry_cgroup = frame_cgroups.create(&retry).expect("create retry cgroup");

        assert!(frame_cgroups.open(&first_run).unwrap().is_none());
        assert_eq!(
            frame_cgroups.open(&retry).unwrap().unwrap().path,
            retry_cgroup.path
        );
    }

    #[test]
    fn create_refuses_an_existing_cgroup() {
        let dir = TempDir::new().unwrap();
        let frame_cgroups = FrameCgroups::at(dir.path());
        let launch_id = Uuid::new_v4();
        frame_cgroups.create(&launch_id).unwrap();

        assert!(frame_cgroups.create(&launch_id).is_err());
    }

    #[test]
    fn finds_the_launch_of_a_process_in_a_frame_cgroup() {
        let dir = TempDir::new().unwrap();
        let frame_cgroups = FrameCgroups::at(dir.path());
        let launch_id = Uuid::new_v4();
        frame_cgroups.create(&launch_id).unwrap();
        let in_frame = format!("0::/system.slice/openrqd.service/frames/{launch_id}\n");
        let removed = format!(
            "0::/system.slice/openrqd.service/frames/{}\n",
            Uuid::new_v4()
        );

        assert_eq!(frame_cgroups.launch_in(&in_frame).unwrap(), Some(launch_id));
        assert_eq!(frame_cgroups.launch_in(&removed).unwrap(), None);
        assert_eq!(
            frame_cgroups
                .launch_in("0::/system.slice/openrqd.service\n")
                .unwrap(),
            None
        );
        assert_eq!(frame_cgroups.launch_in("").unwrap(), None);
    }

    #[test]
    fn launch_lookup_fails_unless_it_can_tell() {
        let dir = TempDir::new().unwrap();
        let not_a_dir = dir.path().join("frames");
        write(&not_a_dir, "");
        let launch_id = Uuid::new_v4();
        let in_frame = format!("0::/system.slice/openrqd.service/frames/{launch_id}\n");

        // The frame cgroup can't be looked up
        assert!(FrameCgroups::at(&not_a_dir).launch_in(&in_frame).is_err());
        // Still parsed as outside any frame cgroup
        assert_eq!(
            FrameCgroups::at(&not_a_dir)
                .launch_in("0::/system.slice/openrqd.service\n")
                .unwrap(),
            None
        );

        let frame_cgroups = FrameCgroups::at(dir.path());
        // The process is gone
        assert_eq!(
            frame_cgroups
                .launch_from(&dir.path().join("missing"))
                .unwrap(),
            None
        );
        // Its cgroup file can't be read (EISDIR)
        assert!(frame_cgroups.launch_from(dir.path()).is_err());
    }

    #[test]
    fn lists_orphans() {
        let dir = TempDir::new().unwrap();
        let frame_cgroups = FrameCgroups::at(dir.path());
        let recovered = Uuid::new_v4();
        let orphan = Uuid::new_v4();
        frame_cgroups.create(&recovered).unwrap();
        frame_cgroups.create(&orphan).unwrap();
        write(&dir.path().join("cgroup.procs"), "");

        let orphans = frame_cgroups.orphans(&[recovered]).unwrap();

        assert_eq!(orphans.len(), 1);
        assert_eq!(orphans[0].path, dir.path().join(orphan.to_string()));
    }

    #[test]
    fn reads_membership() {
        let dir = TempDir::new().unwrap();
        let cgroup = FrameCgroup {
            path: dir.path().to_path_buf(),
        };
        write(&dir.path().join("cgroup.procs"), "10\n20\n");
        write(&dir.path().join("cgroup.events"), "populated 1\nfrozen 0\n");

        assert_eq!(cgroup.pids().unwrap(), vec![10, 20]);
        assert!(cgroup.is_populated().unwrap());
    }

    #[test]
    fn kill_writes_cgroup_kill() {
        let dir = TempDir::new().unwrap();
        let cgroup = FrameCgroup {
            path: dir.path().to_path_buf(),
        };
        write(&dir.path().join("cgroup.kill"), "");

        cgroup.kill().expect("kill");

        assert_eq!(read(&dir.path().join("cgroup.kill")), "1");
    }

    #[test]
    fn kill_falls_back_to_freezing_and_sigkill() {
        let dir = TempDir::new().unwrap();
        let cgroup = FrameCgroup {
            path: dir.path().to_path_buf(),
        };
        let mut children = [sleeper(), sleeper()];
        write(
            &dir.path().join("cgroup.procs"),
            &format!("{}\n{}\n", children[0].id(), children[1].id()),
        );
        write(&dir.path().join("cgroup.freeze"), "");

        cgroup.kill().expect("kill");

        for child in &mut children {
            assert_eq!(child.wait().unwrap().signal(), Some(libc::SIGKILL));
        }
        // Thawed once done
        assert_eq!(read(&dir.path().join("cgroup.freeze")), "0");
    }

    #[test]
    fn signals_every_member() {
        let dir = TempDir::new().unwrap();
        let cgroup = FrameCgroup {
            path: dir.path().to_path_buf(),
        };
        let mut child = sleeper();
        write(
            &dir.path().join("cgroup.procs"),
            &format!("{}\n0\n", child.id()),
        );

        assert_eq!(cgroup.signal(Signal::SIGTERM).unwrap(), 1);
        assert_eq!(child.wait().unwrap().signal(), Some(libc::SIGTERM));
    }

    #[test]
    fn removes_empty_cgroups_and_tolerates_missing_ones() {
        let dir = TempDir::new().unwrap();
        let cgroup = FrameCgroup {
            path: dir.path().join("frame"),
        };
        fs::create_dir(&cgroup.path).unwrap();

        cgroup.remove().expect("remove");
        assert!(!cgroup.path.exists());
        cgroup.remove().expect("remove missing cgroup");
    }

    #[tokio::test]
    async fn reap_of_a_missing_cgroup_is_a_noop() {
        let dir = TempDir::new().unwrap();
        let cgroup = FrameCgroup {
            path: dir.path().join("missing"),
        };

        assert_eq!(cgroup.reap().await.unwrap(), 0);
    }

    #[tokio::test]
    async fn wait_empty_returns_once_the_cgroup_empties() {
        let dir = TempDir::new().unwrap();
        let cgroup = FrameCgroup {
            path: dir.path().to_path_buf(),
        };
        let events = dir.path().join("cgroup.events");
        write(&events, "populated 1\nfrozen 0\n");
        let emptied = tokio::spawn(async move {
            tokio::time::sleep(Duration::from_millis(200)).await;
            // Replaced atomically, so the waiter never reads a half-written file.
            let next = events.with_extension("next");
            write(&next, "populated 0\nfrozen 0\n");
            fs::rename(&next, &events).unwrap();
        });

        let start = Instant::now();
        cgroup.wait_empty(start + Duration::from_secs(30)).await;

        assert!(start.elapsed() >= Duration::from_millis(200));
        assert!(start.elapsed() < Duration::from_secs(5));
        emptied.await.unwrap();
    }

    #[tokio::test]
    async fn wait_empty_gives_up_at_the_deadline() {
        let dir = TempDir::new().unwrap();
        let cgroup = FrameCgroup {
            path: dir.path().to_path_buf(),
        };
        write(&dir.path().join("cgroup.events"), "populated 1\nfrozen 0\n");

        let start = Instant::now();
        cgroup.wait_empty(start + Duration::from_millis(200)).await;

        assert!(start.elapsed() >= Duration::from_millis(200));
        assert!(start.elapsed() < Duration::from_secs(5));
    }

    #[tokio::test]
    async fn wait_empty_keeps_waiting_through_unreadable_events() {
        let dir = TempDir::new().unwrap();
        let missing_events = FrameCgroup {
            path: dir.path().join("missing_events"),
        };
        fs::create_dir(&missing_events.path).unwrap();
        let events_dir = FrameCgroup {
            path: dir.path().join("events_dir"),
        };
        fs::create_dir_all(events_dir.path.join("cgroup.events")).unwrap();

        for cgroup in [missing_events, events_dir] {
            let start = Instant::now();
            cgroup.wait_empty(start + Duration::from_millis(200)).await;

            assert!(start.elapsed() >= Duration::from_millis(200));
            assert!(start.elapsed() < Duration::from_secs(5));
        }
    }

    #[tokio::test]
    async fn wait_empty_returns_at_once_for_empty_or_missing_cgroups() {
        let dir = TempDir::new().unwrap();
        let empty = FrameCgroup {
            path: dir.path().to_path_buf(),
        };
        write(&dir.path().join("cgroup.events"), "populated 0\nfrozen 0\n");
        let missing = FrameCgroup {
            path: dir.path().join("missing"),
        };

        let start = Instant::now();
        let deadline = start + Duration::from_secs(30);
        empty.wait_empty(deadline).await;
        missing.wait_empty(deadline).await;

        assert!(start.elapsed() < Duration::from_secs(5));
    }

    #[test]
    fn child_joins_through_procs_fd_before_exec() {
        use std::os::unix::process::CommandExt;

        let dir = TempDir::new().unwrap();
        let cgroup = FrameCgroup {
            path: dir.path().to_path_buf(),
        };
        write(&dir.path().join("cgroup.procs"), "");
        let procs = cgroup.open_procs().unwrap();
        let procs_fd = procs.as_raw_fd();

        let mut command = Command::new("true");
        unsafe {
            command.pre_exec(move || join(procs_fd));
        }
        assert!(command.status().unwrap().success());

        assert_eq!(read(&dir.path().join("cgroup.procs")), "0");
    }

    /// Frame cgroups under the cgroup this test runs in. `None` unless the host runs cgroup v2
    /// and that cgroup is writable (delegated), in which case the real-kernel tests skip.
    #[cfg(target_os = "linux")]
    fn real_frame_cgroups() -> Option<FrameCgroups> {
        let mount = Path::new(CGROUP_MOUNT);
        if !mount.join("cgroup.controllers").exists() {
            return None;
        }
        let own = fs::read_to_string(SELF_CGROUP).ok()?;
        let relative = own
            .lines()
            .find_map(|line| line.strip_prefix("0::"))?
            .trim();
        if relative == "/" {
            return None;
        }
        let own_cgroup = mount.join(relative.trim_start_matches('/'));
        nix::unistd::access(
            &own_cgroup.join("cgroup.procs"),
            nix::unistd::AccessFlags::W_OK,
        )
        .ok()?;
        let path = own_cgroup.join(format!("rqd-test-{}", Uuid::new_v4()));
        fs::create_dir(&path).ok()?;
        Some(FrameCgroups { path })
    }

    #[cfg(target_os = "linux")]
    async fn wait_for_members(cgroup: &FrameCgroup, count: usize) -> Vec<u32> {
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            let pids = cgroup.pids().unwrap();
            if pids.len() >= count || Instant::now() >= deadline {
                return pids;
            }
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
    }

    /// Session id of `pid`, from field 6 of `/proc/<pid>/stat`.
    #[cfg(target_os = "linux")]
    fn session_of(pid: u32) -> Option<i32> {
        let stat = fs::read_to_string(format!("/proc/{pid}/stat")).ok()?;
        // comm (field 2) may contain spaces and parentheses, so parse after its closing paren.
        let (_, rest) = stat.rsplit_once(')')?;
        // rest starts at field 3 (state), so the session is the 4th field after it.
        rest.split_whitespace().nth(3)?.parse().ok()
    }

    /// Runs on a real kernel: a frame-like process tree, including a child that escapes its
    /// session with setsid, is tracked, signalled and reaped through its cgroup.
    #[cfg(target_os = "linux")]
    #[tokio::test]
    async fn contains_and_reaps_frame_processes_on_a_real_kernel() {
        use std::os::unix::process::CommandExt;

        let Some(frame_cgroups) = real_frame_cgroups() else {
            eprintln!("Skipping: needs cgroup v2 and a writable (delegated) cgroup");
            return;
        };
        let launch_id = Uuid::new_v4();
        let cgroup = frame_cgroups.create(&launch_id).unwrap();
        let procs = cgroup.open_procs().unwrap();
        let procs_fd = procs.as_raw_fd();

        let mut wrapper = Command::new("/bin/sh");
        wrapper.arg("-c").arg("setsid sleep 60 & sleep 60 & wait");
        unsafe {
            wrapper.pre_exec(move || {
                libc::setsid();
                join(procs_fd)
            });
        }
        let mut wrapper = wrapper.spawn().expect("spawn wrapper");
        drop(procs);

        let pids = wait_for_members(&cgroup, 3).await;
        assert!(pids.contains(&wrapper.id()), "{pids:?}");
        assert_eq!(pids.len(), 3, "{pids:?}");
        assert!(cgroup.is_populated().unwrap());
        assert_eq!(
            frame_cgroups.launch_of(wrapper.id()).unwrap(),
            Some(launch_id)
        );
        assert_eq!(frame_cgroups.launch_of(std::process::id()).unwrap(), None);

        // setsid only takes effect once the child execs it, so wait for a member to leave the
        // wrapper's session.
        let wrapper_sid = session_of(wrapper.id()).expect("wrapper sid");
        let deadline = Instant::now() + Duration::from_secs(5);
        let escaped = loop {
            let escaped = cgroup.pids().unwrap().into_iter().any(|pid| {
                pid != wrapper.id() && session_of(pid).is_some_and(|sid| sid != wrapper_sid)
            });
            if escaped || Instant::now() >= deadline {
                break escaped;
            }
            tokio::time::sleep(Duration::from_millis(20)).await;
        };
        assert!(escaped, "no member left the wrapper's session");

        // The wrapper exits, leaving both sleeps behind in the cgroup
        wrapper.kill().unwrap();
        wrapper.wait().unwrap();
        assert_eq!(wait_for_members(&cgroup, 2).await.len(), 2);

        assert_eq!(cgroup.reap().await.expect("reap"), 2);
        assert!(!cgroup.path.exists());
        assert!(frame_cgroups.open(&launch_id).unwrap().is_none());

        fs::remove_dir(&frame_cgroups.path).unwrap();
    }

    #[tokio::test]
    async fn reaps_orphans_concurrently_and_spares_other_cgroups() {
        let dir = TempDir::new().unwrap();
        let frame_cgroups = FrameCgroups::at(dir.path());
        let fake_cgroup = |launch_id: &Uuid| {
            let cgroup = frame_cgroups.create(launch_id).unwrap();
            write(&cgroup.path.join("cgroup.procs"), "");
            // Never empties, so each reap runs into REAP_TIMEOUT
            write(&cgroup.path.join("cgroup.events"), "populated 1\n");
            write(&cgroup.path.join("cgroup.kill"), "");
            cgroup
        };
        let recovered_id = Uuid::new_v4();
        let recovered = fake_cgroup(&recovered_id);
        let orphans: Vec<FrameCgroup> = (0..3).map(|_| fake_cgroup(&Uuid::new_v4())).collect();

        let mut found = frame_cgroups.orphans(&[recovered_id]).unwrap();
        // Launched after the orphans were listed, as once rqd serves
        let launched = fake_cgroup(&Uuid::new_v4());
        found.sort_by(|a, b| a.path.cmp(&b.path));
        let mut expected: Vec<&PathBuf> = orphans.iter().map(|orphan| &orphan.path).collect();
        expected.sort();
        assert_eq!(
            found.iter().map(|orphan| &orphan.path).collect::<Vec<_>>(),
            expected
        );

        let start = Instant::now();
        reap_orphans(found).await;

        assert!(
            start.elapsed() < REAP_TIMEOUT * 2,
            "orphans were reaped one by one"
        );
        for orphan in &orphans {
            assert_eq!(read(&orphan.path.join("cgroup.kill")), "1");
        }
        assert_eq!(read(&recovered.path.join("cgroup.kill")), "");
        assert_eq!(read(&launched.path.join("cgroup.kill")), "");
    }

    #[cfg(target_os = "linux")]
    #[tokio::test]
    async fn reaps_orphans_on_a_real_kernel() {
        let Some(frame_cgroups) = real_frame_cgroups() else {
            eprintln!("Skipping: needs cgroup v2 and a writable (delegated) cgroup");
            return;
        };
        let recovered = Uuid::new_v4();
        let orphans = [Uuid::new_v4(), Uuid::new_v4()];
        frame_cgroups.create(&recovered).unwrap();
        for orphan in &orphans {
            frame_cgroups.create(orphan).unwrap();
        }

        reap_orphans(frame_cgroups.orphans(&[recovered]).unwrap()).await;

        assert!(frame_cgroups.open(&recovered).unwrap().is_some());
        for orphan in &orphans {
            assert!(frame_cgroups.open(orphan).unwrap().is_none());
        }

        frame_cgroups
            .open(&recovered)
            .unwrap()
            .unwrap()
            .remove()
            .unwrap();
        fs::remove_dir(&frame_cgroups.path).unwrap();
    }
}
