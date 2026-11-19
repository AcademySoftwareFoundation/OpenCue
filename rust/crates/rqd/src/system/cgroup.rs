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
//! <service>/daemon             rqd itself
//! <service>/frames/<frame_id>  one cgroup per frame
//! ```
//!
//! Every process a frame starts stays in the frame's cgroup whatever its session or process
//! group, so rqd can account for, signal and kill all of them, and reap what is left behind when
//! the frame's wrapper exits.
//!
//! The module only operates on cgroupfs files, so it builds on every unix target and its logic is
//! tested against a fake cgroupfs in a temp dir. It is only ever enabled on Linux.

#![cfg_attr(not(target_os = "linux"), allow(dead_code))]

use std::{
    collections::HashSet,
    fs::{self, File, OpenOptions},
    io::{self, Write},
    os::fd::RawFd,
    path::{Path, PathBuf},
    sync::OnceLock,
    time::{Duration, Instant},
};

use miette::{miette, Result};
use nix::{
    errno::Errno,
    sys::signal::{kill, Signal},
    unistd::Pid,
};
use tracing::{info, warn};
use uuid::Uuid;

const CGROUP_MOUNT: &str = "/sys/fs/cgroup";
const SELF_CGROUP: &str = "/proc/self/cgroup";
const DAEMON_CGROUP: &str = "daemon";
const FRAMES_CGROUP: &str = "frames";
/// Controllers handed down to frame cgroups when the service cgroup has them available.
const FRAME_CONTROLLERS: [&str; 3] = ["memory", "cpu", "pids"];
/// How long a killed cgroup gets to empty before rqd gives up on removing it.
const REAP_TIMEOUT: Duration = Duration::from_secs(5);
const REAP_POLL_INTERVAL: Duration = Duration::from_millis(50);
/// Passes of the signal-based kill fallback, each one catching processes forked during the
/// previous pass.
const SIGNAL_KILL_PASSES: usize = 10;

static FRAME_CGROUPS: OnceLock<Option<FrameCgroups>> = OnceLock::new();

/// Sets up frame cgroups for this rqd instance when `enabled`: moves rqd into
/// `<service>/daemon` and creates `<service>/frames`.
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
        .and_then(|own_cgroup| {
            FrameCgroups::setup(Path::new(CGROUP_MOUNT), &own_cgroup, std::process::id())
        });
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
    /// Lays out the delegated service cgroup rqd runs in, `own_cgroup` being the content of
    /// rqd's `/proc/self/cgroup` and `mount` the cgroup v2 mount point. Moves `pid` (rqd) into
    /// `<service>/daemon`, as cgroup v2 doesn't let a cgroup hold processes and hand controllers
    /// down to its children at the same time, creates `<service>/frames` and enables the
    /// available [`FRAME_CONTROLLERS`] on the way down. No resource limit is set.
    fn setup(mount: &Path, own_cgroup: &str, pid: u32) -> Result<Self> {
        if !mount.join("cgroup.controllers").exists() {
            return Err(miette!("cgroup v2 is not mounted at {}", mount.display()));
        }
        let service = service_cgroup(mount, own_cgroup)?;

        let daemon = service.join(DAEMON_CGROUP);
        create_cgroup_dir(&daemon).map_err(|err| {
            miette!(
                "Failed to create {}: {err}. Is the service cgroup delegated (Delegate=yes)?",
                daemon.display()
            )
        })?;
        write_cgroup_file(&daemon.join("cgroup.procs"), &pid.to_string())
            .map_err(|err| miette!("Failed to move rqd into {}: {err}", daemon.display()))?;

        let frames = service.join(FRAMES_CGROUP);
        create_cgroup_dir(&frames)
            .map_err(|err| miette!("Failed to create {}: {err}", frames.display()))?;

        enable_controllers(&service);
        enable_controllers(&frames);
        Ok(Self { path: frames })
    }

    #[cfg(test)]
    pub(crate) fn at(path: impl Into<PathBuf>) -> Self {
        Self { path: path.into() }
    }

    fn frame_path(&self, frame_id: &Uuid) -> PathBuf {
        self.path.join(frame_id.to_string())
    }

    /// Creates the cgroup of a frame about to be launched.
    ///
    /// A leftover cgroup with the same frame id, from an earlier run of the frame whose
    /// processes couldn't be reaped, is reused after killing its processes.
    pub fn create(&self, frame_id: &Uuid) -> Result<FrameCgroup> {
        let cgroup = FrameCgroup {
            path: self.frame_path(frame_id),
        };
        match fs::create_dir(&cgroup.path) {
            Ok(()) => Ok(cgroup),
            Err(err) if err.kind() == io::ErrorKind::AlreadyExists => {
                warn!(
                    "Reusing leftover cgroup {}, killing its processes",
                    cgroup.path.display()
                );
                cgroup.kill()?;
                Ok(cgroup)
            }
            Err(err) => Err(miette!(
                "Failed to create cgroup {}: {err}",
                cgroup.path.display()
            )),
        }
    }

    /// Opens the cgroup of a frame, or returns `None` when the frame wasn't launched in one.
    pub fn open(&self, frame_id: &Uuid) -> Option<FrameCgroup> {
        let path = self.frame_path(frame_id);
        path.is_dir().then_some(FrameCgroup { path })
    }

    /// Frame cgroups that don't belong to any of `frame_ids`.
    fn orphans(&self, frame_ids: &[Uuid]) -> Result<Vec<FrameCgroup>> {
        let known: HashSet<String> = frame_ids.iter().map(Uuid::to_string).collect();
        let entries = fs::read_dir(&self.path)
            .map_err(|err| miette!("Failed to list {}: {err}", self.path.display()))?;
        Ok(entries
            .flatten()
            .filter(|entry| entry.file_type().is_ok_and(|file_type| file_type.is_dir()))
            .filter(|entry| !known.contains(entry.file_name().to_string_lossy().as_ref()))
            .map(|entry| FrameCgroup { path: entry.path() })
            .collect())
    }

    /// Kills and removes every frame cgroup that doesn't belong to one of `frame_ids`.
    ///
    /// Meant for startup, after snapshot recovery, with the ids of the recovered frames: any
    /// other frame cgroup holds processes of a frame rqd has lost track of.
    pub async fn reap_orphans(&self, frame_ids: &[Uuid]) {
        let orphans = match self.orphans(frame_ids) {
            Ok(orphans) => orphans,
            Err(err) => {
                warn!("Failed to look for orphan frame cgroups. {err}");
                return;
            }
        };
        for orphan in orphans {
            match orphan.reap().await {
                Ok(count) => info!(
                    "Removed orphan frame cgroup {}, killed {count} leftover processes",
                    orphan.path.display()
                ),
                Err(err) => warn!("Failed to reap orphan frame cgroup. {err}"),
            }
        }
    }
}

/// The cgroup of a single frame (`<service>/frames/<frame_id>`).
#[derive(Debug, Clone)]
pub struct FrameCgroup {
    path: PathBuf,
}

impl FrameCgroup {
    /// Path of the cgroup directory.
    pub fn path(&self) -> &Path {
        &self.path
    }

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
                .filter(|pid| !killed.contains(pid))
                .collect();
            if new_pids.is_empty() {
                break;
            }
            for pid in new_pids {
                let _ = kill(Pid::from_raw(pid as i32), Signal::SIGKILL);
                killed.insert(pid);
            }
        }
        // A fatal signal gets through the freezer. Thawing only keeps anything that survived
        // from staying frozen.
        if frozen {
            let _ = write_cgroup_file(&freeze, "0");
        }
        result
    }

    /// Removes the cgroup, which fails while processes are left in it.
    pub fn remove(&self) -> Result<()> {
        match fs::remove_dir(&self.path) {
            Ok(()) => Ok(()),
            Err(err) if err.kind() == io::ErrorKind::NotFound => Ok(()),
            Err(err) => Err(miette!("Failed to remove {}: {err}", self.path.display())),
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

/// Resolves the service cgroup from rqd's own `/proc/self/cgroup` entry. rqd may already sit in
/// the daemon cgroup, when systemd placed it there through `DelegateSubgroup=`.
fn service_cgroup(mount: &Path, own_cgroup: &str) -> Result<PathBuf> {
    let relative = own_cgroup
        .lines()
        .find_map(|line| line.strip_prefix("0::"))
        .ok_or_else(|| miette!("No cgroup v2 entry in {SELF_CGROUP}"))?;
    let mut service = mount.join(relative.trim().trim_start_matches('/'));
    if service
        .file_name()
        .is_some_and(|name| name == DAEMON_CGROUP)
    {
        service.pop();
    }
    if service == mount {
        return Err(miette!(
            "rqd runs in the root cgroup, frame cgroups need a delegated service cgroup"
        ));
    }
    Ok(service)
}

/// Enables the available [`FRAME_CONTROLLERS`] for the children of `cgroup` and returns the ones
/// enabled. Best effort: a controller the kernel refuses (e.g. `EBUSY` while processes still live
/// in `cgroup` itself) is logged and skipped, frames are contained either way.
fn enable_controllers(cgroup: &Path) -> Vec<&'static str> {
    let available = fs::read_to_string(cgroup.join("cgroup.controllers")).unwrap_or_default();
    let available: HashSet<&str> = available.split_whitespace().collect();
    let subtree_control = cgroup.join("cgroup.subtree_control");
    FRAME_CONTROLLERS
        .into_iter()
        .filter(|controller| available.contains(controller))
        .filter(
            |controller| match write_cgroup_file(&subtree_control, &format!("+{controller}")) {
                Ok(()) => true,
                Err(err) => {
                    warn!(
                        "Failed to enable the {controller} controller in {}: {err}",
                        cgroup.display()
                    );
                    false
                }
            },
        )
        .collect()
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

fn parse_pids(procs: &str) -> Vec<u32> {
    procs
        .lines()
        .filter_map(|line| line.trim().parse().ok())
        // Signalling pid 0 would hit rqd's own process group.
        .filter(|&pid| pid != 0)
        .collect()
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
        fs::create_dir_all(service.join(DAEMON_CGROUP)).expect("create service cgroup");
        write(&service.join("cgroup.controllers"), "cpu io memory pids");
        write(&service.join("cgroup.subtree_control"), "");
        write(&service.join(DAEMON_CGROUP).join("cgroup.procs"), "");
        (mount, service)
    }

    #[test]
    fn parses_pids_skipping_blank_and_zero_entries() {
        assert_eq!(parse_pids("12\n\n345\n0\n"), vec![12, 345]);
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
    fn resolves_service_cgroup_when_already_in_daemon() {
        let mount = Path::new("/sys/fs/cgroup");
        assert_eq!(
            service_cgroup(mount, "0::/system.slice/openrqd.service/daemon\n").unwrap(),
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
    fn setup_moves_rqd_to_daemon_and_creates_frames() {
        let (mount, service) = fake_cgroupfs();

        let frame_cgroups =
            FrameCgroups::setup(mount.path(), "0::/system.slice/openrqd.service\n", 4242)
                .expect("setup");

        assert_eq!(frame_cgroups.path, service.join(FRAMES_CGROUP));
        assert!(frame_cgroups.path.is_dir());
        assert_eq!(read(&service.join("daemon/cgroup.procs")), "4242");
    }

    #[test]
    fn setup_requires_cgroup_v2() {
        let (mount, _) = fake_cgroupfs();
        fs::remove_file(mount.path().join("cgroup.controllers")).unwrap();

        assert!(
            FrameCgroups::setup(mount.path(), "0::/system.slice/openrqd.service\n", 1).is_err()
        );
    }

    #[test]
    fn setup_requires_a_writable_service_cgroup() {
        if unsafe { libc::geteuid() } == 0 {
            // Permissions don't stop root.
            return;
        }
        use std::os::unix::fs::PermissionsExt;
        let (mount, service) = fake_cgroupfs();
        fs::remove_dir_all(service.join(DAEMON_CGROUP)).unwrap();
        fs::set_permissions(&service, fs::Permissions::from_mode(0o555)).unwrap();

        let result = FrameCgroups::setup(mount.path(), "0::/system.slice/openrqd.service\n", 1);

        fs::set_permissions(&service, fs::Permissions::from_mode(0o755)).unwrap();
        assert!(result.is_err());
    }

    #[test]
    fn enables_only_available_controllers() {
        let (_mount, service) = fake_cgroupfs();
        write(&service.join("cgroup.controllers"), "io pids memory");

        assert_eq!(enable_controllers(&service), vec!["memory", "pids"]);
    }

    #[test]
    fn enabling_controllers_is_best_effort() {
        let (_mount, service) = fake_cgroupfs();
        fs::remove_file(service.join("cgroup.subtree_control")).unwrap();

        assert!(enable_controllers(&service).is_empty());
    }

    #[test]
    fn creates_and_opens_frame_cgroups() {
        let dir = TempDir::new().unwrap();
        let frame_cgroups = FrameCgroups::at(dir.path());
        let frame_id = Uuid::new_v4();

        assert!(frame_cgroups.open(&frame_id).is_none());
        let cgroup = frame_cgroups.create(&frame_id).expect("create");

        assert_eq!(cgroup.path(), dir.path().join(frame_id.to_string()));
        assert!(frame_cgroups.open(&frame_id).is_some());
        assert!(frame_cgroups.open(&Uuid::new_v4()).is_none());
    }

    #[test]
    fn create_reuses_a_leftover_cgroup_after_killing_it() {
        let dir = TempDir::new().unwrap();
        let frame_cgroups = FrameCgroups::at(dir.path());
        let frame_id = Uuid::new_v4();
        let cgroup = frame_cgroups.create(&frame_id).unwrap();
        write(&cgroup.path.join("cgroup.kill"), "");

        frame_cgroups.create(&frame_id).expect("reuse leftover");

        assert_eq!(read(&cgroup.path.join("cgroup.kill")), "1");
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
        assert_eq!(orphans[0].path(), dir.path().join(orphan.to_string()));
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
        let frame_id = Uuid::new_v4();
        let cgroup = frame_cgroups.create(&frame_id).unwrap();
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

        // The wrapper exits, leaving both sleeps behind in the cgroup
        wrapper.kill().unwrap();
        wrapper.wait().unwrap();
        assert_eq!(wait_for_members(&cgroup, 2).await.len(), 2);

        assert_eq!(cgroup.reap().await.expect("reap"), 2);
        assert!(!cgroup.path().exists());
        assert!(frame_cgroups.open(&frame_id).is_none());

        fs::remove_dir(&frame_cgroups.path).unwrap();
    }

    #[cfg(target_os = "linux")]
    #[tokio::test]
    async fn reaps_orphans_on_a_real_kernel() {
        let Some(frame_cgroups) = real_frame_cgroups() else {
            eprintln!("Skipping: needs cgroup v2 and a writable (delegated) cgroup");
            return;
        };
        let recovered = Uuid::new_v4();
        let orphan = Uuid::new_v4();
        frame_cgroups.create(&recovered).unwrap();
        frame_cgroups.create(&orphan).unwrap();

        frame_cgroups.reap_orphans(&[recovered]).await;

        assert!(frame_cgroups.open(&recovered).is_some());
        assert!(frame_cgroups.open(&orphan).is_none());

        frame_cgroups.open(&recovered).unwrap().remove().unwrap();
        fs::remove_dir(&frame_cgroups.path).unwrap();
    }
}
