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

use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime};

use crate::{
    config::CONFIG,
    frame::manager,
    report::report_client,
    system::oom::{self, OOM_REASON_MSG},
};
use async_trait::async_trait;
use bytesize::KIB;
use dashmap::DashMap;
use itertools::Either;
use miette::Result;
use opencue_proto::{
    host::{HardwareState, LockState},
    report::{HostReport, RenderHost},
};
use tokio::{
    select,
    sync::{
        broadcast::{self, Receiver},
        oneshot, Mutex, Notify, OnceCell, RwLock,
    },
    time,
};
use tracing::{debug, error, info, warn};
use uuid::Uuid;

#[cfg(target_os = "macos")]
use crate::system::macos::MacOsSystem;
#[cfg(target_os = "windows")]
use crate::system::windows::WindowsSystem;
use crate::{
    config::MachineConfig,
    frame::{
        cache::RunningFrameCache,
        running_frame::{FrameState, RunningFrame, RunningState},
    },
    report::report_client::{ReportClient, ReportInterface},
    system::{manager::ReservationError, reservation::CoreStateManager},
};

#[cfg(any(target_os = "linux", all(target_os = "macos", debug_assertions)))]
use super::linux::LinuxSystem;
use super::manager::{HostMemSnapshot, PeerMem, SystemManagerType};
#[cfg(feature = "nimby")]
use crate::system::nimby::Nimby;

/// Constantly monitor the state of this machine and report back to Cuebot
///
/// Example:
/// ```
/// #[tokio::main]
/// async fn main() -> miette::Result<()> {
///   let running_frame_cache = RunningFrameCache::init();
///   // Inicialize cuebot client
///   let report_client = Arc::new(ReportClient::build(&config).await?);
///   // Initialize rqd machine monitor
///   let machine_monitor =
///      MachineMonitor::init(
///         &config,
///         report_client,
///         Arc::clone(&running_frame_cache))?;
///   tokio::spawn(async move { machine_monitor.start().await });
/// }
/// ```
pub struct MachineMonitor {
    maching_config: MachineConfig,
    report_client: Arc<ReportClient>,
    pub system_manager: Mutex<SystemManagerType>,
    pub core_manager: Arc<RwLock<CoreStateManager>>,
    pub running_frames_cache: Arc<RunningFrameCache>,
    /// Frames that have finished locally but whose completion has not yet been acknowledged by
    /// Cuebot. Entries are retried by the dedicated delivery task (see [`MachineMonitor::start`])
    /// and only removed once Cuebot accepts the FrameCompleteReport, guaranteeing at-least-once
    /// delivery. Without this, a transient delivery failure (network blip, Cuebot GC pause, or an
    /// explicit RqdRetryReportException) would silently drop the completion and let Cuebot rebook
    /// an already-finished frame (double booking). Keyed by frame_id.
    pending_completions: Arc<DashMap<Uuid, PendingCompletion>>,
    /// Wakes the delivery task as soon as a frame enters [`Self::pending_completions`], so a
    /// freshly finished frame is reported immediately instead of waiting for the next retry
    /// interval. `Notify` retains a permit when no waiter is parked, so a signal raised while a
    /// delivery pass is in flight wakes the following iteration — no lost wakeups.
    completion_notify: Arc<Notify>,
    last_host_state: Arc<RwLock<Option<RenderHost>>>,
    interrupt: Mutex<Option<broadcast::Sender<()>>>,
    reboot_when_idle: Mutex<bool>,
    #[cfg(feature = "nimby")]
    nimby: Arc<Option<Nimby>>,
    #[cfg(feature = "nimby")]
    nimby_state: RwLock<LockState>,
}

/// A locally-finished frame awaiting completion acknowledgement from Cuebot, tagged with the instant
/// it entered the pending store. `enqueued_at` gives every entry a uniform delivery age regardless of
/// its terminal state — a `FailedBeforeStart` frame carries no `end_time` — which the backlog warning
/// uses to tell a genuine, cycle-surviving backlog apart from frames enqueued in the current cycle.
struct PendingCompletion {
    frame: Arc<RunningFrame>,
    enqueued_at: Instant,
}

/// Outcome counters of one delivery pass over the pending-completion store, consumed by the
/// per-pass summary log in [`MachineMonitor::start_completion_delivery_task`].
#[derive(Debug, Default, PartialEq, Eq)]
struct DeliveryPassStats {
    /// Reports acknowledged by Cuebot and removed from the store.
    delivered: usize,
    /// Sends that returned an error; entries retained for retry.
    failed: usize,
    /// Sends abandoned after `frame_complete_send_timeout`; entries retained for retry.
    timed_out: usize,
    /// Entries discarded without a report because they were not in a terminal state.
    dropped: usize,
    /// Entries still pending after the pass.
    remaining: usize,
}

static MACHINE_MONITOR: OnceCell<Arc<MachineMonitor>> = OnceCell::const_new();

pub async fn instance() -> Result<Arc<MachineMonitor>> {
    MACHINE_MONITOR
        .get_or_try_init(|| async {
            let machine_monitor = MachineMonitor::init(report_client::instance().await?)?;
            Ok(Arc::new(machine_monitor))
        })
        .await
        .map(Arc::clone)
}

impl MachineMonitor {
    #[cfg(feature = "nimby")]
    fn initial_nimby_state(config: &MachineConfig) -> LockState {
        if config.nimby_mode && config.nimby_lock_by_default {
            LockState::NimbyLocked
        } else {
            LockState::Open
        }
    }

    /// Initializes the object without starting the monitor loop
    /// Will gather the initial state of this machine
    fn init(report_client: Arc<ReportClient>) -> Result<Self> {
        #[cfg(target_os = "macos")]
        #[allow(unused_variables)]
        let (system_manager, core_manager): (
            SystemManagerType,
            Arc<RwLock<CoreStateManager>>,
        ) = {
            let processor_info_data = MacOsSystem::read_cpuinfo(&CONFIG.machine.cpuinfo_path)?;
            let core_manager = Arc::new(RwLock::new(CoreStateManager::new(
                processor_info_data.processor_structure.clone(),
            )));

            (Box::new(MacOsSystem::init(&CONFIG.machine)?), core_manager)
        };

        // Use debug_assertions to allow linux logic compilation from mac development environments
        #[cfg(any(target_os = "linux", all(target_os = "macos", debug_assertions)))]
        let (system_manager, core_manager): (
            SystemManagerType,
            Arc<RwLock<CoreStateManager>>,
        ) = {
            let processor_info_data = LinuxSystem::read_cpuinfo(&CONFIG.machine.cpuinfo_path)?;
            let core_manager = Arc::new(RwLock::new(CoreStateManager::new(
                processor_info_data.processor_structure.clone(),
            )));

            (
                Box::new(LinuxSystem::init(&CONFIG.machine, processor_info_data)?),
                core_manager,
            )
        };

        #[cfg(target_os = "windows")]
        let (system_manager, core_manager): (
            SystemManagerType,
            Arc<RwLock<CoreStateManager>>,
        ) = {
            let processor_info_data = WindowsSystem::read_cpuinfo(&CONFIG.machine.cpuinfo_path)?;
            let core_manager = Arc::new(RwLock::new(CoreStateManager::new(
                processor_info_data.processor_structure.clone(),
            )));

            (
                Box::new(WindowsSystem::init(&CONFIG.machine, processor_info_data)?),
                core_manager,
            )
        };

        // Init nimby
        #[cfg(feature = "nimby")]
        let nimby = if CONFIG.machine.nimby_mode {
            let nimby = Nimby::init(
                CONFIG.machine.nimby_idle_threshold,
                CONFIG.machine.nimby_display_file_path.clone(),
                CONFIG.machine.nimby_display_xauthority_path.clone(),
            );
            info!("NIMBY mode enabled and initialized");
            Arc::new(Some(nimby))
        } else {
            Arc::new(None)
        };

        #[cfg(feature = "nimby")]
        let initial_nimby_state = Self::initial_nimby_state(&CONFIG.machine);

        Ok(Self {
            maching_config: CONFIG.machine.clone(),
            report_client,
            system_manager: Mutex::new(system_manager),
            running_frames_cache: RunningFrameCache::init(),
            pending_completions: Arc::new(DashMap::new()),
            completion_notify: Arc::new(Notify::new()),
            last_host_state: Arc::new(RwLock::new(None)),
            interrupt: Mutex::new(None),
            reboot_when_idle: Mutex::new(false),
            #[cfg(feature = "nimby")]
            nimby,
            #[cfg(feature = "nimby")]
            nimby_state: RwLock::new(initial_nimby_state),
            core_manager,
        })
    }

    /// Starts an async loop that will update the machine state every `monitor_interval_seconds`.
    pub async fn start(&self, startup_flag: oneshot::Sender<()>) -> Result<()> {
        let report_client = self.report_client.clone();

        #[cfg(feature = "nimby")]
        let nimby_locked = *self.nimby_state.read().await == LockState::NimbyLocked;
        #[cfg(not(feature = "nimby"))]
        let nimby_locked = false;

        let host_state = {
            let system_lock = self.system_manager.lock().await;
            Self::inspect_host_state(&self.maching_config, &system_lock, nimby_locked)?
        };

        let core_info = {
            let core_manager = self.core_manager.read().await;
            core_manager.get_core_info_report(self.maching_config.core_multiplier)
        };

        self.last_host_state
            .write()
            .await
            .replace(host_state.clone());

        debug!("Sending start report: {:?}", host_state);
        report_client
            .send_start_up_report(host_state, core_info)
            .await?;

        // Notify caller that the machine state is ready
        let _ = startup_flag.send(());

        let (term_sender, mut term_receiver) = broadcast::channel::<()>(5);

        // Start the dedicated frame-completion delivery task. Delivery is deliberately decoupled
        // from the monitor loop: the /proc + log sweep and the inline host report both take
        // unbounded time, and tying delivery cadence to them is what let the pending backlog grow.
        self.start_completion_delivery_task(term_receiver.resubscribe());

        // Start nimby monitor
        #[cfg(feature = "nimby")]
        self.start_nimby(term_receiver.resubscribe()).await;

        // When the host starts in NIMBY-locked state (via nimby_lock_by_default),
        // apply the same side effects as a normal lock transition so that cores
        // are actually reserved and no new frames can be scheduled.
        #[cfg(feature = "nimby")]
        if nimby_locked {
            info!("Host starting in nimby-locked state, locking all cores");
            self.lock_all_cores().await;
        }

        let mut interval = time::interval(self.maching_config.monitor_interval);

        let mut interrupt_lock = self.interrupt.lock().await;
        interrupt_lock.replace(term_sender);
        drop(interrupt_lock);

        #[cfg(feature = "nimby")]
        let mut last_lock_state = *self.nimby_state.read().await;
        #[cfg(not(feature = "nimby"))]
        let mut last_lock_state = LockState::Open;
        loop {
            select! {
                    message = term_receiver.recv() => {
                        match message {
                            Ok(_) => {
                                info!("Loop interrupted");
                                break;
                            },
                            Err(_) => info!("Sender dropped"),
                        }
                    }
                    _ = interval.tick() => {
                        self.collect_and_send_host_report().await?;
                        self.check_reboot_flag().await;

                        #[cfg(feature = "nimby")]
                        if let Some(nimby) = &*self.nimby {
                            last_lock_state = self.handle_nimby_state_change(nimby, last_lock_state).await?;
                        }
                }

            }
        }
        Ok(())
    }

    /// Handles NIMBY state changes and performs necessary actions when the host
    /// becomes locked or unlocked based on user activity.
    ///
    /// Returns the new lock state after handling any transitions.
    #[cfg(feature = "nimby")]
    async fn handle_nimby_state_change(
        &self,
        nimby: &Nimby,
        current_state: LockState,
    ) -> Result<LockState> {
        match (nimby.is_user_active(), current_state) {
            // Became locked
            (true, LockState::Open) => {
                let new_state = LockState::NimbyLocked;

                // Update registered state
                let mut nimby_state = self.nimby_state.write().await;
                *nimby_state = new_state;
                drop(nimby_state);

                info!("Host became nimby locked");
                self.lock_all_cores().await;
                let count = manager::instance()
                    .await?
                    .kill_all_running_frames("Host has been Nimby-Locked")
                    .await?;
                info!("{count} frames killed after the machine became locked");
                Ok(new_state)
            }
            // Continues locked
            (true, LockState::NimbyLocked) => Ok(current_state),
            // Continues open
            (false, LockState::Open) => Ok(current_state),
            // Became unlocked — only transition when the nimby system has
            // actually observed user activity before.  Without this guard a
            // host that starts NIMBY-locked via `nimby_lock_by_default` would
            // immediately auto-unlock because `is_user_active()` returns
            // `false` when no interaction has ever been recorded.
            (false, LockState::NimbyLocked) if nimby.has_activity_been_recorded() => {
                let new_state = LockState::Open;

                // Update registered state
                let mut nimby_state = self.nimby_state.write().await;
                *nimby_state = new_state;
                drop(nimby_state);

                info!("Host became nimby unlocked");
                self.unlock_all_cores().await;
                Ok(new_state)
            }
            // Continues locked (includes the case where no activity has been
            // recorded yet, so a default-locked host stays locked until the
            // user has been active and then becomes idle)
            (false, LockState::NimbyLocked) => Ok(current_state),
            // NoOp
            _ => Ok(current_state),
        }
    }

    #[cfg(feature = "nimby")]
    async fn start_nimby(&self, term_receiver: Receiver<()>) {
        // Start nimby monitor
        let nimby_clone = Arc::clone(&self.nimby);
        let nimby_start_retry_interval = self.maching_config.nimby_start_retry_interval;
        if nimby_clone.as_ref().is_some() {
            tokio::spawn(async move {
                let mut interval = time::interval(nimby_start_retry_interval);
                loop {
                    let mut term_listener = term_receiver.resubscribe();
                    // Await for another chance to start nimby
                    interval.tick().await;
                    if let Some(nimby) = nimby_clone.as_ref() {
                        match nimby.start(&mut term_listener).await {
                            Ok(_) => break,
                            Err(err) => {
                                info!(
                                    "Nimby startup failed, retrying in {}s. {err}",
                                    nimby_start_retry_interval.as_secs()
                                );
                            }
                        }
                    }
                }
            });
        }
    }

    pub async fn interrupt(&self) {
        let mut lock = self.interrupt.lock().await;
        match lock.take() {
            Some(sender) => {
                if sender.send(()).is_err() {
                    warn!("Failed to request a monitor interruption")
                }
            }
            None => warn!("Interrupt channel has already been used"),
        }
    }

    async fn collect_and_send_host_report(&self) -> Result<()> {
        let report_client = self.report_client.clone();
        let host_report = self.collect_host_report().await?;

        debug!("Sending host report: {:?}", host_report.host);
        report_client.send_host_report(host_report).await?;
        Ok(())
    }

    async fn check_reboot_flag(&self) {
        if *self.reboot_when_idle.lock().await {
            warn!("Machine became idle. Rebooting..");
            if let Err(err) = self.system_manager.lock().await.reboot() {
                error!("Failed to reboot when became idle. {err}");
            };
        }
    }

    async fn monitor_running_frames(&self) -> Result<()> {
        let mut finished_frames: Vec<Arc<RunningFrame>> = Vec::new();
        let mut running_frames: Vec<(Arc<RunningFrame>, RunningState)> = Vec::new();
        let mut memory_aggressors: Vec<(Arc<RunningFrame>, u64)> = Vec::new();

        // Only keep running frames on the cache and store a copy of their state
        // to avoid having to deal with the state lock
        self.running_frames_cache
            .retain(|_, running_frame| match running_frame.get_state_copy() {
                FrameState::Created(_) => true,
                FrameState::Running(running_state) => {
                    running_frames.push((Arc::clone(running_frame), running_state));
                    true
                }
                FrameState::Finished(_) => {
                    finished_frames.push(Arc::clone(running_frame));
                    false
                }
                FrameState::FailedBeforeStart => {
                    finished_frames.push(Arc::clone(running_frame));
                    false
                }
            });

        // Handle Running frames separately to avoid deadlocks when trying to get a frame state
        for (running_frame, running_state) in &running_frames {
            // Collect stats about the procs related to this frame
            let proc_stats_opt = {
                let system_monitor = self.system_manager.lock().await;
                system_monitor
                    .collect_proc_stats(running_state.pid, running_frame.log_path.clone())
                    .unwrap_or_else(|err| {
                        warn!("Failed to collect proc_stats. {}", err);
                        None
                    })
            };

            if let Some(proc_stats) = proc_stats_opt {
                // Mark memory aggressor frames
                if running_frame.request.soft_memory_limit > 0
                    && proc_stats.rss as i64 > running_frame.request.soft_memory_limit
                {
                    memory_aggressors.push((Arc::clone(running_frame), proc_stats.max_rss));
                }

                // Update stats for running frames
                running_frame.update_frame_stats(proc_stats);
            } else if running_frame.is_dangling_expired() {
                // Frama proc was not found to be running even after a grace period
                warn!(
                    "Removing {} from the cache. Could not find proc {} for frame that was supposed to be running.",
                    running_frame.to_string(),
                    running_state.pid
                );
                // Attempt to finish the process
                let _ = running_frame.finish(
                    1,
                    Some(19),
                    Some("Failed to find PID associated to this frame".to_string()),
                );
                finished_frames.push(Arc::clone(running_frame));
                self.running_frames_cache.remove(&running_frame.frame_id);
            } else {
                // Proc finished but frame is waiting for the lock on `is_finished` to update the status
                // keep frame around for another round
                running_frame.mark_dangling();
            }
        }

        // Move newly finished frames into the pending-completion store (releasing their cores
        // exactly once) and wake the delivery task. Entries survive delivery failures and are
        // retried until acknowledged, so a finished frame's completion is not lost while this RQD
        // stays up (the store is in-memory, so it does not survive an RQD restart).
        self.enqueue_and_release_finished_frames_cores(finished_frames)
            .await;
        self.warn_if_completion_backlog();

        // Build a host-wide memory snapshot from the freshly-updated running frames and
        // share it (same Arc) into each of them. A frame that later fails renders this in
        // its footer to expose whether a co-tenant may have starved it of memory.
        {
            let (total_memory, available_memory) = {
                let host_state = self.last_host_state.read().await;
                host_state
                    .as_ref()
                    .map(|hs| ((hs.total_mem as u64) * KIB, (hs.free_mem as u64) * KIB))
                    .unwrap_or((0, 0))
            };
            let mut peers: Vec<PeerMem> = running_frames
                .iter()
                .map(|(running_frame, _)| running_frame.to_peer_mem())
                .collect();
            peers.sort_by(|a, b| b.current_rss.cmp(&a.current_rss));
            let snapshot = Arc::new(HostMemSnapshot {
                captured_at: SystemTime::now(),
                total_memory,
                available_memory,
                peers,
            });
            for (running_frame, _) in &running_frames {
                running_frame.set_host_mem_snapshot(Arc::clone(&snapshot));
            }
        }

        match self.memory_usage().await {
            Some((memory_usage, total_memory))
                if memory_usage > CONFIG.machine.memory_oom_margin_percentage =>
            {
                warn!(
                    "Machine memory usage is above allowed threshold ({}). \
                    Triggering OOM protection",
                    CONFIG.machine.memory_oom_margin_percentage
                );
                let frames_to_kill =
                    oom::choose_frames_to_kill(memory_usage, total_memory, memory_aggressors);

                // Attempt to kill selected frames.
                // Logic will ignore kill errors and try again on the next iteration
                for frame in frames_to_kill {
                    // Freeze stats before killing to capture accurate memory measurement.
                    // This prevents corruption from reading zombie/dying processes after kill signal.
                    frame.freeze_stats();

                    if let Ok(manager) = manager::instance().await {
                        info!("Requesting a kill for {}", &frame);
                        let kill_result = manager
                            .kill_running_frame(&frame.frame_id, OOM_REASON_MSG.to_string())
                            .await;
                        if let Err(err) = kill_result {
                            warn!(
                                "Failed to kill frame {} when under OOM pressure. {}",
                                frame, err
                            )
                        }
                    }
                }
            }
            _ => (),
        }

        // Sanitize dangling reservations
        // This mechanism is redundant as enqueue_and_release_finished_frames_cores releases
        // resources reserved to finished frames. But leaking core reservations would lead to
        // waste of resoures, so having a safety check sounds reasonable even when reduntant.
        {
            let running_resources: Vec<Uuid> = running_frames
                .iter()
                .map(|(running_frame, _)| running_frame.request.resource_id())
                .collect();
            self.core_manager
                .write()
                .await
                .sanitize_reservations(&running_resources);
        }

        Ok(())
    }

    /// Release the cores held by newly finished frames and move them into the in-memory
    /// pending-completion store (entries are retried until acknowledged, but do not survive an RQD
    /// restart). Cores are released here, exactly once per frame, because the frame
    /// is done locally regardless of whether Cuebot has acknowledged the completion yet. The actual
    /// delivery (and its retries) is handled by the task spawned in
    /// [`Self::start_completion_delivery_task`], which is woken here so freshly finished frames are
    /// reported immediately instead of waiting for the next retry interval.
    async fn enqueue_and_release_finished_frames_cores(
        &self,
        finished_frames: Vec<Arc<RunningFrame>>,
    ) {
        if finished_frames.is_empty() {
            return;
        }
        for frame in finished_frames {
            if let Err(err) = self.release_cores(&frame.request.resource_id()).await {
                warn!(
                    "Failed to release cores reserved by {}: {}",
                    frame.request.resource_id(),
                    err
                );
            };
            self.pending_completions.insert(
                frame.frame_id,
                PendingCompletion {
                    frame,
                    enqueued_at: Instant::now(),
                },
            );
        }
        self.completion_notify.notify_one();
    }

    /// Surface a genuine delivery backlog from the monitor loop, synchronously every cycle. The
    /// delivery task only logs between passes, so while one pass grinds through a large backlog
    /// (worst case ~`frame_complete_send_timeout` per hung entry) — or if that task ever exits —
    /// this is the signal that keeps firing precisely when the condition matters most. Cheap by
    /// construction: a `len()` and a `max()` over `enqueued_at`, no awaits. Age is measured from
    /// the instant each entry was enqueued, so only entries that have already survived at least
    /// one delivery pass warn; freshly enqueued frames have ~zero age and stay quiet.
    fn warn_if_completion_backlog(&self) {
        let oldest_age = self
            .pending_completions
            .iter()
            .map(|entry| entry.value().enqueued_at.elapsed())
            .max();
        if let Some(age) = oldest_age {
            if age >= self.maching_config.frame_complete_delivery_interval {
                warn!(
                    "{} pending frame completion(s) still awaiting delivery to Cuebot after \
                     retries; oldest is {}s old",
                    self.pending_completions.len(),
                    age.as_secs()
                );
            }
        }
    }

    /// Spawn the dedicated frame-completion delivery task.
    ///
    /// Delivery gets its own task, decoupled from the monitor loop, for two reasons. First, a
    /// single `send_frame_complete_report` against an unreachable Cuebot can spin through the gRPC
    /// retry ladder (up to `grpc.backoff_retry_attempts` × `grpc.backoff_delay_max`, i.e. minutes),
    /// and an inline flush would stall the host-mem snapshot, OOM protection and the host report
    /// itself for that long. Second, coupling delivery cadence to the monitor tick meant a pass had
    /// to be cut off at the tick period; cancelling an in-flight send that Cuebot had in fact
    /// processed manufactured duplicate reports and kept the backlog alive. Here a pass always runs
    /// until the backlog is drained — only an individual send that exceeds
    /// `frame_complete_send_timeout` is abandoned (and retried on a later pass).
    ///
    /// A single task cannot overlap itself, so no guard against concurrent passes is needed. Each
    /// iteration waits for whichever comes first: the retry interval (pending entries left over
    /// from a failed/timed-out send) or a [`Self::completion_notify`] signal (a freshly finished
    /// frame, delivered with no added latency).
    fn start_completion_delivery_task(&self, mut term_receiver: Receiver<()>) {
        let pending_completions = Arc::clone(&self.pending_completions);
        let report_client = Arc::clone(&self.report_client);
        let last_host_state = Arc::clone(&self.last_host_state);
        let notify = Arc::clone(&self.completion_notify);
        let delivery_interval = self.maching_config.frame_complete_delivery_interval;
        let send_timeout = self.maching_config.frame_complete_send_timeout;

        tokio::spawn(async move {
            let mut interval = time::interval(delivery_interval);
            // A pass can legitimately outlast the interval (sends are serial and never cancelled).
            // Delay, rather than burst, the ticks missed while it ran: retries stay paced at
            // `delivery_interval` between passes instead of running back-to-back while the
            // schedule catches up.
            interval.set_missed_tick_behavior(time::MissedTickBehavior::Delay);
            loop {
                select! {
                    _ = term_receiver.recv() => break,
                    _ = interval.tick() => {}
                    _ = notify.notified() => {}
                }

                if pending_completions.is_empty() {
                    continue;
                }

                let started = Instant::now();
                let stats = Self::deliver_pending_completions(
                    Arc::clone(&pending_completions),
                    Arc::clone(&report_client),
                    Arc::clone(&last_host_state),
                    send_timeout,
                )
                .await;
                info!(
                    "Completion delivery pass: {} delivered, {} failed, {} timed out, \
                     {} dropped, {} remaining, took {:.1}s",
                    stats.delivered,
                    stats.failed,
                    stats.timed_out,
                    stats.dropped,
                    stats.remaining,
                    started.elapsed().as_secs_f64()
                );
            }
        });
    }

    /// Deliver every pending frame-complete report to Cuebot. An entry is only removed from the
    /// pending store once Cuebot acknowledges it (Ok response). Any failure, transport error,
    /// exhausted 5xx retries, or a gRPC application error such as RqdRetryReportException (which
    /// surfaces here as an `Err`) leaves the entry in place to be retried on the next delivery pass.
    /// This guarantees at-least-once delivery so a completed (including successfully rendered) frame
    /// is never silently dropped, which would otherwise let Cuebot rebook it onto a second host.
    ///
    /// Note: delivery is at-least-once, not exactly-once. A report whose response is lost in transit
    /// is resent and Cuebot receives a duplicate. Cuebot tolerates duplicates rather than treating
    /// them as a strict no-op: the frame stop is version-fenced, so a resent report whose frame is no
    /// longer RUNNING at the reported version does not re-stop it, and if the proc has since been
    /// rebooked onto its next frame the duplicate is dropped instead of unbooking that proc. A
    /// duplicate therefore cannot re-complete a frame or orphan a running one.
    ///
    /// Undelivered entries are deliberately retained rather than dropped after some cap or max age:
    /// dropping a completion is exactly what reintroduces double booking, so this store fails closed.
    /// A pass runs until the snapshot is exhausted; only an individual send that exceeds
    /// `send_timeout` is abandoned, so a slow-but-progressing Cuebot is never cut off mid-drain.
    async fn deliver_pending_completions<T: ReportInterface + Send + Sync + 'static>(
        pending_completions: Arc<DashMap<Uuid, PendingCompletion>>,
        report_client: Arc<T>,
        last_host_state: Arc<RwLock<Option<RenderHost>>>,
        send_timeout: Duration,
    ) -> DeliveryPassStats {
        let mut stats = DeliveryPassStats::default();

        // Avoid holding a lock while reporting back to cuebot
        let host_state = match last_host_state.read().await.clone() {
            Some(state) => state,
            None => {
                stats.remaining = pending_completions.len();
                warn!(
                    "Invalid state. Could not find host state, deferring {} pending frame \
                     completion(s) to the next cycle",
                    stats.remaining
                );
                return stats;
            }
        };

        // Snapshot the pending entries so we don't hold a DashMap iterator across awaits. Deliver
        // oldest-first so no entry is starved by newer arrivals, regardless of map iteration order.
        let pending: Vec<(Arc<RunningFrame>, Instant)> = {
            let mut pending: Vec<_> = pending_completions
                .iter()
                .map(|entry| (Arc::clone(&entry.value().frame), entry.value().enqueued_at))
                .collect();
            pending.sort_by_key(|(_, enqueued_at)| *enqueued_at);
            pending
        };

        for (frame, _) in pending {
            // (exit_code, exit_signal, run_time_seconds)
            let exit_report: Option<(u32, u32, u32)> = match frame.get_state_copy() {
                FrameState::Finished(finished_state) => {
                    let exit_signal = match finished_state.exit_signal {
                        Some(signal) => signal as u32,
                        None => 0,
                    };
                    // Wall-clock runtime of the frame in seconds. Cuebot relies on run_time
                    // to enforce layer runtime timeouts and the 12h no-retry cap
                    // (see Dispatcher.FRAME_TIME_NO_RETRY / determineFrameState). Sending 0
                    // disables those timeout-based DEAD decisions and skews usage counters.
                    let run_time = finished_state
                        .end_time
                        .duration_since(finished_state.start_time)
                        .map(|d| d.as_secs() as u32)
                        .unwrap_or(0);
                    Some((finished_state.exit_code as u32, exit_signal, run_time))
                }
                FrameState::FailedBeforeStart => {
                    Some((
                        1,  // Mark frame as failed
                        10, // Use signal to indicate it failed before starting
                        0,  // Never ran, so no runtime
                    ))
                }
                _ => None,
            };

            let (exit_code, exit_signal, run_time) = match exit_report {
                Some(values) => values,
                None => {
                    // A pending entry should always be in a terminal state. If it isn't, drop it to
                    // avoid retaining it (and retrying it) forever.
                    error!(
                        "Pending completion for {} is not in a terminal state, dropping",
                        frame
                    );
                    pending_completions.remove(&frame.frame_id);
                    stats.dropped += 1;
                    continue;
                }
            };

            let frame_report = frame.clone_into_running_frame_info();
            debug!("Sending frame complete report: {}", frame);

            match tokio::time::timeout(
                send_timeout,
                report_client.send_frame_complete_report(
                    host_state.clone(),
                    frame_report,
                    exit_code,
                    exit_signal,
                    run_time,
                ),
            )
            .await
            {
                Ok(Ok(())) => {
                    pending_completions.remove(&frame.frame_id);
                    stats.delivered += 1;
                }
                Ok(Err(err)) => {
                    stats.failed += 1;
                    // One warn per pass carries a concrete error; the rest go to debug. The pass
                    // summary already reports the failed count, and during a Cuebot outage every
                    // entry fails, which would otherwise emit O(backlog) warning lines per pass.
                    if stats.failed == 1 {
                        warn!(
                            "Failed to send frame_complete_report for {}, will retry on the next \
                             delivery pass. {}",
                            frame, err
                        );
                    } else {
                        debug!(
                            "Failed to send frame_complete_report for {}, will retry on the next \
                             delivery pass. {}",
                            frame, err
                        );
                    }
                }
                Err(_) => {
                    stats.timed_out += 1;
                    // Same first-per-pass capping as the failure arm above.
                    if stats.timed_out == 1 {
                        warn!(
                            "Timed out after {}s sending frame_complete_report for {}, will retry \
                             on the next delivery pass",
                            send_timeout.as_secs(),
                            frame
                        );
                    } else {
                        debug!(
                            "Timed out after {}s sending frame_complete_report for {}, will retry \
                             on the next delivery pass",
                            send_timeout.as_secs(),
                            frame
                        );
                    }
                }
            }
        }

        stats.remaining = pending_completions.len();
        stats
    }

    fn inspect_host_state(
        config: &MachineConfig,
        system: &SystemManagerType,
        nimby_locked: bool,
    ) -> Result<RenderHost> {
        let stats = system.collect_stats()?;
        let gpu_stats = system.collect_gpu_stats();

        Ok(RenderHost {
            name: stats.hostname,
            nimby_enabled: config.nimby_mode,
            nimby_locked,
            facility: config.facility.clone(),
            num_procs: stats.num_sockets as i32,
            cores_per_proc: (stats.cores_per_socket * config.core_multiplier) as i32,
            total_swap: (stats.total_swap / KIB) as i64,
            total_mem: (stats.total_memory / KIB) as i64,
            total_mcp: (stats.total_temp_storage / KIB) as i64,
            free_swap: (stats.free_swap / KIB) as i64,
            free_mem: (stats.available_memory / KIB) as i64,
            free_mcp: (stats.free_temp_storage / KIB) as i64,
            load: stats.load as i32,
            boot_time: stats.boot_time as i32,
            tags: stats.tags,
            state: *system.hardware_state() as i32,
            attributes: system.attributes().clone(),
            num_gpus: gpu_stats.count as i32,
            free_gpu_mem: gpu_stats.free_memory as i64,
            total_gpu_mem: gpu_stats.total_memory as i64,
        })
    }
}

#[cfg(all(test, feature = "nimby"))]
mod tests {
    use opencue_proto::host::LockState;

    use super::MachineMonitor;
    use crate::config::MachineConfig;

    #[test]
    fn initial_nimby_state_is_open_by_default() {
        assert_eq!(
            MachineMonitor::initial_nimby_state(&MachineConfig::default()),
            LockState::Open
        );
    }

    #[test]
    fn initial_nimby_state_is_locked_when_nimby_lock_by_default_is_enabled() {
        let config = MachineConfig {
            nimby_mode: true,
            nimby_lock_by_default: true,
            ..MachineConfig::default()
        };

        assert_eq!(
            MachineMonitor::initial_nimby_state(&config),
            LockState::NimbyLocked
        );
    }

    #[test]
    fn initial_nimby_state_stays_open_when_nimby_mode_is_disabled() {
        let config = MachineConfig {
            nimby_mode: false,
            nimby_lock_by_default: true,
            ..MachineConfig::default()
        };

        assert_eq!(
            MachineMonitor::initial_nimby_state(&config),
            LockState::Open
        );
    }
}

#[cfg(test)]
mod delivery_tests {
    use std::collections::HashSet;
    use std::sync::Mutex as StdMutex;
    use std::time::{Duration, Instant};

    use async_trait::async_trait;
    use dashmap::DashMap;
    use miette::{miette, Result};
    use opencue_proto::report::{CoreDetail, HostReport, RenderHost, RunningFrameInfo};
    use opencue_proto::rqd::RunFrame;
    use std::sync::Arc;
    use tokio::sync::RwLock;
    use uuid::Uuid;

    use super::{MachineMonitor, PendingCompletion};
    use crate::config::Config;
    use crate::frame::running_frame::RunningFrame;
    use crate::report::report_client::ReportInterface;

    /// Scripted ReportInterface: records every frame-complete call, fails delivery for the frame
    /// ids it was told to fail, and never returns for the frame ids it was told to hang.
    struct MockReportClient {
        fail_ids: HashSet<String>,
        hang_ids: HashSet<String>,
        calls: StdMutex<Vec<(String, u32, u32, u32)>>,
    }

    impl MockReportClient {
        fn new(fail_ids: Vec<String>) -> Self {
            Self::with_hangs(fail_ids, vec![])
        }

        fn with_hangs(fail_ids: Vec<String>, hang_ids: Vec<String>) -> Self {
            Self {
                fail_ids: fail_ids.into_iter().collect(),
                hang_ids: hang_ids.into_iter().collect(),
                calls: StdMutex::new(Vec::new()),
            }
        }
    }

    #[async_trait]
    impl ReportInterface for MockReportClient {
        async fn send_start_up_report(
            &self,
            _render_host: RenderHost,
            _core_detail: CoreDetail,
        ) -> Result<()> {
            Ok(())
        }

        async fn send_frame_complete_report(
            &self,
            _host: RenderHost,
            frame: RunningFrameInfo,
            exit_status: u32,
            exit_signal: u32,
            run_time: u32,
        ) -> Result<()> {
            self.calls.lock().unwrap().push((
                frame.frame_id.clone(),
                exit_status,
                exit_signal,
                run_time,
            ));
            if self.hang_ids.contains(&frame.frame_id) {
                // Simulate a wedged Cuebot handler: the send never completes and can only be
                // abandoned by the caller's per-entry timeout.
                std::future::pending::<()>().await;
            }
            if self.fail_ids.contains(&frame.frame_id) {
                Err(miette!("scripted delivery failure"))
            } else {
                Ok(())
            }
        }

        async fn send_host_report(&self, _host_report: HostReport) -> Result<()> {
            Ok(())
        }
    }

    fn frame_request_and_config() -> (RunFrame, crate::config::RunnerConfig) {
        let general_config = Config::default();
        general_config.setup().unwrap();
        let mut config = general_config.runner;
        config.run_as_user = false;

        let request = RunFrame {
            resource_id: Uuid::new_v4().to_string(),
            job_id: Uuid::new_v4().to_string(),
            job_name: "job_name".to_string(),
            frame_id: Uuid::new_v4().to_string(),
            frame_name: "frame_name".to_string(),
            layer_id: Uuid::new_v4().to_string(),
            command: "true".to_string(),
            user_name: "username".to_string(),
            log_dir: "/tmp".to_string(),
            show: "show".to_string(),
            shot: "shot".to_string(),
            num_cores: 1,
            gid: 10,
            ..Default::default()
        };
        (request, config)
    }

    /// Builds a frame still in the Created state (never started).
    fn make_frame() -> RunningFrame {
        let (request, config) = frame_request_and_config();
        RunningFrame::init(request, 1, config, None, None, "localhost".to_string(), 1)
    }

    /// Builds a frame in the Finished state (exit 0), as if its process just exited.
    fn finished_frame() -> RunningFrame {
        let (request, config) = frame_request_and_config();
        let frame = RunningFrame::init_started_for_test(
            request,
            1,
            config,
            None,
            None,
            "localhost".to_string(),
            Duration::from_secs(10),
        );
        frame.finish(0, None, None).unwrap();
        frame
    }

    fn pending_map(frames: Vec<Arc<RunningFrame>>) -> Arc<DashMap<Uuid, PendingCompletion>> {
        let now = Instant::now();
        pending_map_with_ages(frames.into_iter().map(|frame| (frame, now)).collect())
    }

    /// Builds the pending store with explicit `enqueued_at` instants, for tests that assert on
    /// delivery order.
    fn pending_map_with_ages(
        frames: Vec<(Arc<RunningFrame>, Instant)>,
    ) -> Arc<DashMap<Uuid, PendingCompletion>> {
        let map = DashMap::new();
        for (frame, enqueued_at) in frames {
            map.insert(frame.frame_id, PendingCompletion { frame, enqueued_at });
        }
        Arc::new(map)
    }

    const TEST_SEND_TIMEOUT: Duration = Duration::from_secs(30);

    async fn deliver(
        map: Arc<DashMap<Uuid, PendingCompletion>>,
        client: Arc<MockReportClient>,
    ) -> super::DeliveryPassStats {
        let host_state = Arc::new(RwLock::new(Some(RenderHost::default())));
        MachineMonitor::deliver_pending_completions(map, client, host_state, TEST_SEND_TIMEOUT)
            .await
    }

    #[tokio::test]
    async fn acknowledged_completion_is_removed() {
        let frame = Arc::new(finished_frame());
        let map = pending_map(vec![Arc::clone(&frame)]);
        let client = Arc::new(MockReportClient::new(vec![]));

        deliver(Arc::clone(&map), Arc::clone(&client)).await;

        assert!(map.is_empty(), "acknowledged entry must be removed");
        let calls = client.calls.lock().unwrap();
        assert_eq!(calls.len(), 1);
        assert_eq!(calls[0].1, 0, "exit_status");
    }

    #[tokio::test]
    async fn failed_delivery_retains_entry() {
        let frame = Arc::new(finished_frame());
        let frame_id_str = frame.request.frame_id.clone();
        let map = pending_map(vec![Arc::clone(&frame)]);
        let client = Arc::new(MockReportClient::new(vec![frame_id_str]));

        deliver(Arc::clone(&map), Arc::clone(&client)).await;

        assert_eq!(map.len(), 1, "failed entry must be retained for retry");
        assert_eq!(client.calls.lock().unwrap().len(), 1);
    }

    #[tokio::test]
    async fn non_terminal_entry_is_dropped_without_report() {
        // A frame still in the Created state should never be in the pending store; delivery
        // drops it instead of retrying it forever.
        let frame = Arc::new(make_frame());
        let map = pending_map(vec![Arc::clone(&frame)]);
        let client = Arc::new(MockReportClient::new(vec![]));

        deliver(Arc::clone(&map), Arc::clone(&client)).await;

        assert!(map.is_empty(), "non-terminal entry must be dropped");
        assert!(client.calls.lock().unwrap().is_empty(), "no report sent");
    }

    #[tokio::test]
    async fn failed_before_start_reports_synthetic_exit() {
        let frame = make_frame();
        frame.fail_before_start().unwrap();
        let frame = Arc::new(frame);
        let map = pending_map(vec![Arc::clone(&frame)]);
        let client = Arc::new(MockReportClient::new(vec![]));

        deliver(Arc::clone(&map), Arc::clone(&client)).await;

        assert!(map.is_empty());
        let calls = client.calls.lock().unwrap();
        assert_eq!(calls.len(), 1);
        let (_, exit_status, exit_signal, run_time) = calls[0].clone();
        assert_eq!(exit_status, 1);
        assert_eq!(exit_signal, 10);
        assert_eq!(run_time, 0);
    }

    /// Regression test for the production backlog: one hung send must not prevent the rest of the
    /// pass from delivering (the old per-pass budget cancelled the whole drain instead).
    #[tokio::test(start_paused = true)]
    async fn hung_send_does_not_block_other_entries() {
        let hung = Arc::new(finished_frame());
        let ok_b = Arc::new(finished_frame());
        let ok_c = Arc::new(finished_frame());
        let now = Instant::now();
        // The hung frame is oldest, so it is attempted first; B and C must still deliver.
        let map = pending_map_with_ages(vec![
            (Arc::clone(&hung), now - Duration::from_secs(3)),
            (Arc::clone(&ok_b), now - Duration::from_secs(2)),
            (Arc::clone(&ok_c), now - Duration::from_secs(1)),
        ]);
        let client = Arc::new(MockReportClient::with_hangs(
            vec![],
            vec![hung.request.frame_id.clone()],
        ));

        let stats = deliver(Arc::clone(&map), Arc::clone(&client)).await;

        assert_eq!(stats.delivered, 2);
        assert_eq!(stats.timed_out, 1);
        assert_eq!(stats.remaining, 1);
        assert_eq!(
            client.calls.lock().unwrap().len(),
            3,
            "all entries attempted"
        );
        assert_eq!(map.len(), 1);
        assert!(
            map.contains_key(&hung.frame_id),
            "hung entry must be retained for retry"
        );
    }

    #[tokio::test(start_paused = true)]
    async fn timed_out_send_retains_entry() {
        let frame = Arc::new(finished_frame());
        let map = pending_map(vec![Arc::clone(&frame)]);
        let client = Arc::new(MockReportClient::with_hangs(
            vec![],
            vec![frame.request.frame_id.clone()],
        ));

        let started = tokio::time::Instant::now();
        let stats = deliver(Arc::clone(&map), Arc::clone(&client)).await;
        let elapsed = started.elapsed();

        assert_eq!(map.len(), 1, "timed-out entry must be retained for retry");
        assert_eq!(stats.timed_out, 1);
        assert_eq!(stats.delivered, 0);
        assert!(
            elapsed >= TEST_SEND_TIMEOUT,
            "pass must wait the full per-entry deadline, waited {:?}",
            elapsed
        );
        assert!(
            elapsed < TEST_SEND_TIMEOUT * 2,
            "pass must abandon the hung send at the deadline, waited {:?}",
            elapsed
        );
    }

    #[tokio::test]
    async fn delivery_is_oldest_first() {
        let now = Instant::now();
        // frames[i] is enqueued (80 - 10*i)s ago, so the expected delivery order is frames[0..8]
        // in index order. Insert into the map in a scrambled order; 8 entries make an accidental
        // pass without the sort (map iteration order matching by luck) a 1-in-40320 event.
        let frames: Vec<Arc<RunningFrame>> = (0..8).map(|_| Arc::new(finished_frame())).collect();
        let staggered: Vec<(Arc<RunningFrame>, Instant)> = [5, 2, 7, 0, 3, 6, 1, 4]
            .into_iter()
            .map(|i: usize| {
                (
                    Arc::clone(&frames[i]),
                    now - Duration::from_secs(80 - 10 * i as u64),
                )
            })
            .collect();
        let expected: Vec<String> = frames
            .iter()
            .map(|frame| frame.request.frame_id.clone())
            .collect();
        let map = pending_map_with_ages(staggered);
        let client = Arc::new(MockReportClient::new(vec![]));

        deliver(Arc::clone(&map), Arc::clone(&client)).await;

        let calls: Vec<String> = client
            .calls
            .lock()
            .unwrap()
            .iter()
            .map(|(frame_id, ..)| frame_id.clone())
            .collect();
        assert_eq!(calls, expected, "delivery must be oldest-first");
        assert!(map.is_empty());
    }
}

/// Performe actions on a machine with an async lock
#[async_trait]
pub trait Machine {
    async fn hardware_state(&self) -> Option<HardwareState>;
    async fn memory_usage(&self) -> Option<(u32, u64)>;
    async fn nimby_locked(&self) -> bool;

    /// Reserve CPU cores for a resource
    ///
    /// # Arguments
    ///
    /// * `request` - Either the number of cores to reserve (Left) or specific thread IDs to reserve (Right)
    /// * `resource_id` - Unique identifier for the resource requesting the cores
    ///
    /// # Returns
    ///
    /// A vector of core/thread IDs that were successfully reserved
    ///
    /// # Errors
    ///
    /// Returns `ReservationError` if the cores cannot be reserved (e.g., insufficient available cores)
    async fn reserve_cores(
        &self,
        request: Either<usize, Vec<u32>>,
        resource_id: Uuid,
    ) -> Result<Vec<u32>, ReservationError>;

    /// Release CPU cores previously reserved by a resource
    ///
    /// # Arguments
    ///
    /// * `resource_id` - Unique identifier for the resource that previously reserved the cores
    ///
    /// # Returns
    ///
    /// Returns `Ok(())` if the cores were successfully released
    ///
    /// # Errors
    ///
    /// Returns `ReservationError` if the resource_id is not found or cores cannot be released
    async fn release_cores(&self, resource_id: &Uuid) -> Result<(), ReservationError>;

    /// Reserve GPU units
    ///
    /// # Argument
    ///
    /// * `num_gpus` - Number of gpu units to be reserved
    ///
    /// # Returns
    ///
    /// List of gpu units
    async fn reserve_gpus(&self, num_gpus: u32) -> Result<Vec<u32>>;

    /// Creates a user account if it doesn't already exist in the system
    ///
    /// # Arguments
    ///
    /// * `username` - The name of the user to create
    /// * `uid` - The user ID to assign to the new user
    /// * `gid` - The group ID to assign to the new user
    ///
    /// # Returns
    ///
    /// The user ID (uid) of the created or existing user
    async fn create_user_if_unexisting(&self, username: &str, uid: u32, gid: u32) -> Result<u32>;

    async fn get_host_name(&self) -> String;

    /// Returns the hyperthreading multiplier (threads per physical core).
    /// A value > 1 indicates hyperthreading is enabled.
    async fn get_hyperthreading_multiplier(&self) -> u32;

    /// Send a signal to kill a process
    ///
    /// # Returns Errors:
    ///  * [EINVAL] The value of the sig argument is an invalid or unsupported signal number.
    ///  * [EPERM] The process does not have permission to send the signal to any receiving process.
    ///  * [ESRCH] No process or process group can be found corresponding to that specified by pid.
    async fn kill_session(&self, pid: u32, force: bool) -> Result<()>;

    async fn force_kill(&self, pids: &[u32]) -> Result<()>;

    /// Check if this pid and any of its children are still active
    /// Returns the list of active children, and none if the pid itself is not active
    async fn get_active_proc_lineage(&self, pid: u32) -> Option<Vec<u32>>;

    async fn lock_cores(&self, count: u32) -> u32;

    async fn lock_all_cores(&self);

    async fn unlock_cores(&self, count: u32) -> u32;

    async fn unlock_all_cores(&self);

    async fn reboot_if_idle(&self) -> Result<()>;

    async fn collect_host_report(&self) -> Result<HostReport>;

    async fn quit(&self);

    fn add_running_frame(&self, running_frame: Arc<RunningFrame>);

    fn is_frame_running(&self, frame_id: &Uuid) -> bool;

    fn get_running_frame(&self, frame_id: &Uuid) -> Option<Arc<RunningFrame>>;

    fn all_running_frame_ids(&self) -> Vec<Uuid>;
}

#[async_trait]
impl Machine for MachineMonitor {
    async fn hardware_state(&self) -> Option<HardwareState> {
        self.last_host_state
            .read()
            .await
            .as_ref()
            .map(|hs| hs.state())
    }

    async fn memory_usage(&self) -> Option<(u32, u64)> {
        self.last_host_state.read().await.as_ref().map(|hs| {
            let memory_percentage =
                (((hs.total_mem - hs.free_mem) as f64 / hs.total_mem as f64) * 100.0) as u32;
            (memory_percentage, hs.total_mem as u64)
        })
    }

    async fn nimby_locked(&self) -> bool {
        self.last_host_state
            .read()
            .await
            .as_ref()
            .map(|hs| hs.nimby_locked)
            .unwrap_or(false)
    }

    async fn reserve_cores(
        &self,
        request: Either<usize, Vec<u32>>,
        resource_id: Uuid,
    ) -> Result<Vec<u32>, ReservationError> {
        let mut core_manager = self.core_manager.write().await;
        match request {
            Either::Left(num_cores) => core_manager.reserve_cores(num_cores, resource_id),
            #[allow(deprecated)]
            Either::Right(thread_ids) => core_manager.reserve_cores_by_id(thread_ids, resource_id),
        }
    }

    async fn release_cores(&self, resource_id: &Uuid) -> Result<(), ReservationError> {
        let mut core_manager = self.core_manager.write().await;
        core_manager.release_cores(resource_id).map(|_| ())
    }

    async fn reserve_gpus(&self, _num_gpus: u32) -> Result<Vec<u32>> {
        todo!()
    }

    async fn create_user_if_unexisting(&self, username: &str, uid: u32, gid: u32) -> Result<u32> {
        let system = self.system_manager.lock().await;
        system.create_user_if_unexisting(username, uid, gid)
    }

    async fn get_host_name(&self) -> String {
        let lock = self.last_host_state.read().await;

        lock.as_ref()
            .map(|h| h.name.clone())
            .unwrap_or("noname".to_string())
    }

    async fn get_hyperthreading_multiplier(&self) -> u32 {
        let system = self.system_manager.lock().await;
        system.hyperthreading_multiplier()
    }

    async fn kill_session(&self, pid: u32, force: bool) -> Result<()> {
        let system = self.system_manager.lock().await;
        if force {
            system.force_kill_session(pid)
        } else {
            system.kill_session(pid)
        }
    }

    async fn force_kill(&self, pids: &[u32]) -> Result<()> {
        let system = self.system_manager.lock().await;
        system.force_kill(pids)
    }

    async fn get_active_proc_lineage(&self, pid: u32) -> Option<Vec<u32>> {
        let system = self.system_manager.lock().await;
        system.get_proc_lineage(pid)
    }

    async fn lock_cores(&self, count: u32) -> u32 {
        let mut core_manager = self.core_manager.write().await;
        core_manager.lock_cores(count)
    }

    async fn lock_all_cores(&self) {
        let mut core_manager = self.core_manager.write().await;
        core_manager.lock_all_cores();
    }

    async fn unlock_cores(&self, count: u32) -> u32 {
        let mut core_manager = self.core_manager.write().await;
        core_manager.unlock_cores(count)
    }

    async fn unlock_all_cores(&self) {
        let mut core_manager = self.core_manager.write().await;
        core_manager.unlock_all_cores();
    }

    async fn reboot_if_idle(&self) -> Result<()> {
        // Prevent new frames from booking
        self.lock_all_cores().await;

        if !self.running_frames_cache.is_empty() {
            // Schedule reboot if the machine is not idle
            let mut reboot_when_idle = self.reboot_when_idle.lock().await;

            warn!("Machine set to reboot when idle");
            *reboot_when_idle = true;
        } else {
            // Reboot now
            let system = self.system_manager.lock().await;

            warn!("Rebooting machine on request");
            system.reboot()?;
        }
        Ok(())
    }

    async fn collect_host_report(&self) -> Result<HostReport> {
        let render_host = {
            let system_manager = self.system_manager.lock().await;
            // If there are frames running update the list of procs on the machine
            if !self.running_frames_cache.is_empty() {
                system_manager.refresh_procs();
            }

            #[cfg(feature = "nimby")]
            let nimby_locked = *self.nimby_state.read().await == LockState::NimbyLocked;
            #[cfg(not(feature = "nimby"))]
            let nimby_locked = false;

            Self::inspect_host_state(&self.maching_config, &system_manager, nimby_locked)?
        }; // Scope ensures all mutex are released

        let core_state = {
            let core_manager = self.core_manager.read().await;
            core_manager.get_core_info_report(self.maching_config.core_multiplier)
        };

        // Store the last host_state on self
        let mut self_host_state_lock = self.last_host_state.write().await;
        self_host_state_lock.replace(render_host.clone());
        drop(self_host_state_lock);

        // Refresh list of running frames
        self.monitor_running_frames().await?;

        Ok(HostReport {
            host: Some(render_host),
            frames: Arc::clone(&self.running_frames_cache).clone_to_running_frame_vec(),
            core_info: Some(core_state),
        })
    }

    async fn quit(&self) {
        self.interrupt().await;
        std::process::exit(0);
    }

    fn add_running_frame(&self, running_frame: Arc<RunningFrame>) {
        self.running_frames_cache
            .insert_running_frame(running_frame);
    }

    fn is_frame_running(&self, frame_id: &Uuid) -> bool {
        self.running_frames_cache.contains(frame_id)
    }

    fn get_running_frame(&self, frame_id: &Uuid) -> Option<Arc<RunningFrame>> {
        self.running_frames_cache
            .get(frame_id)
            .as_ref()
            .map(|f| Arc::clone(f))
    }

    fn all_running_frame_ids(&self) -> Vec<Uuid> {
        self.running_frames_cache.all_running_frame_ids()
    }
}
