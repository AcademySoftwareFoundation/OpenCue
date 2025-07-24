//! NIMBY (Not In My BackYard) system for detecting user activity.
//!
//! This module provides functionality to monitor user input (mouse and keyboard)
//! to determine if a user is actively using the system. It's commonly used in
//! distributed computing systems to prevent job scheduling on machines that
//! are currently being used by a human user.

use std::{
    env,
    path::Path,
    sync::{
        Arc,
        atomic::{AtomicU64, Ordering},
    },
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use device_query::{DeviceEvents, DeviceEventsHandler};
use miette::{Context, IntoDiagnostic, Result, miette};
use tokio::sync::broadcast::Receiver;
use tracing::{debug, warn};

/// NIMBY (Not In My BackYard) detector for monitoring user activity.
///
/// This struct tracks user input events (mouse movement and keyboard presses)
/// to determine if a user is actively using the system. It maintains a record
/// of the last interaction time and compares it against a configurable idle
/// threshold to determine user activity status.
///
/// # Examples
///
/// ```rust,no_run
/// use std::time::Duration;
/// use tokio::sync::oneshot;
///
/// # async fn example() -> miette::Result<()> {
/// let nimby = Nimby::init(Duration::from_secs(300)); // 5 minute idle threshold
/// let (tx, rx) = oneshot::channel();
///
/// // Start monitoring in a background task
/// tokio::spawn(async move {
///     nimby.start(rx).await
/// });
///
/// // Check if user is active
/// if nimby.is_user_active() {
///     println!("User is currently active");
/// }
/// # Ok(())
/// # }
/// ```
pub struct Nimby {
    /// Timestamp of the last recorded user interaction.
    /// Using AtomicU64 for lock-free access
    last_interaction_epoch_in_secs: Arc<AtomicU64>,
    /// Duration after which a user is considered idle if no interactions occur.
    idle_threshold: Duration,
    nimby_display_file_path: Option<String>,
    nimby_display_xauthority_path: String,
}

impl Nimby {
    /// Creates a new NIMBY detector with the specified idle threshold.
    ///
    /// # Arguments
    ///
    /// * `idle_threshold` - Duration after which the user is considered idle
    ///   if no mouse or keyboard activity is detected.
    ///
    /// # Returns
    ///
    /// A new `Nimby` instance ready to start monitoring user activity.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use std::time::Duration;
    ///
    /// // Create a NIMBY detector with 5-minute idle threshold
    /// let nimby = Nimby::init(Duration::from_secs(300));
    /// ```
    pub fn init(
        idle_threshold: Duration,
        nimby_display_file_path: Option<String>,
        nimby_display_xauthority_path: String,
    ) -> Self {
        Nimby {
            last_interaction_epoch_in_secs: Arc::new(AtomicU64::new(0)),
            idle_threshold,
            nimby_display_file_path,
            nimby_display_xauthority_path,
        }
    }

    /// Starts monitoring user activity until an interrupt signal is received.
    ///
    /// This method sets up event handlers for mouse movement and keyboard input,
    /// then waits for an interrupt signal. It includes a 5-second initialization
    /// period during which events are ignored to prevent false positives during
    /// system startup.
    ///
    /// # Arguments
    ///
    /// * `interrupt_signal` - A oneshot receiver that will terminate the monitoring
    ///   when a signal is sent.
    ///
    /// # Returns
    ///
    /// * `Ok(())` - When monitoring is successfully stopped via interrupt signal
    /// * `Err(miette::Error)` - If the device event handler cannot be initialized
    ///   (typically because it's already been initialized elsewhere)
    ///
    /// # Behavior
    ///
    /// - Mouse movement and keyboard key-down events update the last interaction time
    /// - Events during the first 5 seconds after startup are ignored
    /// - The method blocks until the interrupt signal is received
    /// - Event handlers are automatically cleaned up when the method returns
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use tokio::sync::oneshot;
    /// use std::time::Duration;
    ///
    /// # async fn example() -> miette::Result<()> {
    /// let nimby = Nimby::init(Duration::from_secs(300));
    /// let (tx, rx) = oneshot::channel();
    ///
    /// // Start monitoring in background
    /// let monitor_handle = tokio::spawn(async move {
    ///     nimby.start(rx).await
    /// });
    ///
    /// // Stop monitoring after some time
    /// tokio::time::sleep(Duration::from_secs(60)).await;
    /// let _ = tx.send(());
    /// monitor_handle.await??;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn start(&self, interrupt_signal: &mut Receiver<()>) -> Result<()> {
        if let Some(nimby_display_file_path) = &self.nimby_display_file_path {
            Self::set_display_from_file(
                nimby_display_file_path,
                &self.nimby_display_xauthority_path,
            )
            .await?;
        }

        let device_state =
            // If starting device_state failed again, return Error.
            DeviceEventsHandler::new(Duration::from_millis(300))
                // None here means the device_handler has alread been initialized
                .ok_or(miette!("Nimby watcher has already been initialized"))?;

        let startup_time = SystemTime::now();
        let init_wait = Duration::from_secs(5);

        let last_interaction = Arc::clone(&self.last_interaction_epoch_in_secs);
        let _mouse_guard = device_state.on_mouse_move(move |_| {
            let now = SystemTime::now();
            if now.duration_since(startup_time).unwrap_or(Duration::ZERO) > init_wait {
                debug!("mouse interaction");
                let now_epoch = now
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or(Duration::ZERO)
                    .as_secs();

                last_interaction.store(now_epoch, Ordering::Relaxed);
            }
        });

        let last_interaction = Arc::clone(&self.last_interaction_epoch_in_secs);
        let _keyboard_guard = device_state.on_key_down(move |_| {
            let now = SystemTime::now();
            if now.duration_since(startup_time).unwrap_or(Duration::ZERO) > init_wait {
                debug!("keyboard interaction");
                let now_epoch = now
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or(Duration::ZERO)
                    .as_secs();

                last_interaction.store(now_epoch, Ordering::Relaxed);
            }
        });

        let _ = interrupt_signal.recv().await;
        warn!("nimby loop interrupted");
        Ok(())
    }

    /// Sets the DISPLAY and XAUTHORITY environment variables from a configuration file.
    ///
    /// This function reads display configuration from a file and sets appropriate
    /// environment variables for X11 display access. This is commonly needed in
    /// headless or multi-user environments where the display information needs to
    /// be determined dynamically.
    ///
    /// # Arguments
    ///
    /// * `nimby_display_file_path` - Path to the file containing display configuration
    /// * `xauthoriry_path` - Template path for XAUTHORITY file with `{username}` placeholder
    ///
    /// # Display File Format
    ///
    /// The display file should contain one or more lines with display information.
    /// The function reads the last line of the file and supports two formats:
    ///
    /// ## Format 1: Username and Display Number
    /// ```text
    /// username:display_number
    /// ```
    /// Example:
    /// ```text
    /// alice:0
    /// bob:1
    /// charlie:2
    /// ```
    ///
    /// ## Format 2: Display Number Only
    /// ```text
    /// display_number
    /// ```
    /// Example:
    /// ```text
    /// 0
    /// 1
    /// 2
    /// ```
    ///
    /// # Behavior
    ///
    /// - Reads the entire file and uses the **last line** for configuration
    /// - If the line contains a colon (`:`) separator:
    ///   - Sets `XAUTHORITY` using the username to replace `{username}` in the template path
    ///   - Sets `DISPLAY` to `:display_number`
    /// - If the line contains no colon:
    ///   - Sets `DISPLAY` to `:line_content`
    ///   - Does not modify `XAUTHORITY`
    ///
    /// # Environment Variables Set
    ///
    /// - `DISPLAY` - Always set to `:display_number` format
    /// - `XAUTHORITY` - Set only when username is provided, using the template path
    ///
    /// # Returns
    ///
    /// * `Ok(())` - Environment variables successfully set
    /// * `Err(miette::Error)` - File could not be read or file is empty
    ///
    /// # Safety
    ///
    /// This function uses `unsafe` blocks to modify environment variables, which
    /// can affect the entire process and any child processes.
    async fn set_display_from_file(
        nimby_display_file_path: &str,
        xauthoriry_path: &str,
    ) -> Result<()> {
        let display_path = Path::new(nimby_display_file_path);
        let display_from_file = tokio::fs::read_to_string(&display_path)
            .await
            .into_diagnostic()
            .wrap_err(format!(
                "Failed to load nimby. DISPLAY variable is not set and {} doesn't exist",
                nimby_display_file_path
            ))?;
        let last_entry = display_from_file.lines().last().ok_or(miette!(
            "Failed to load nimby. {} file is empty",
            nimby_display_file_path
        ))?;
        if let Some((username, display)) = last_entry.split_once(":") {
            if !username.is_empty() {
                unsafe {
                    env::set_var(
                        "XAUTHORITY",
                        xauthoriry_path.replace("{username}", username),
                    )
                };
            }
            unsafe { env::set_var("DISPLAY", format!(":{display}")) };
        } else {
            unsafe { env::set_var("DISPLAY", format!(":{last_entry}")) };
        };
        Ok(())
    }

    /// Checks if the user is currently considered active based on recent interactions.
    ///
    /// A user is considered active if there has been mouse or keyboard activity
    /// within the configured idle threshold duration.
    ///
    /// # Returns
    ///
    /// * `true` - If user activity was detected within the idle threshold
    /// * `false` - If no activity was detected within the idle threshold,
    ///   or if no activity has ever been recorded
    ///
    /// # Thread Safety
    ///
    /// This method is thread-safe and can be called concurrently from multiple
    /// threads. It handles lock poisoning gracefully by recovering the data
    /// from poisoned locks.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use std::time::Duration;
    ///
    /// let nimby = Nimby::init(Duration::from_secs(300)); // 5 minute threshold
    ///
    /// if nimby.is_user_active() {
    ///     println!("User is active - don't start heavy computation");
    /// } else {
    ///     println!("User appears idle - safe to start background tasks");
    /// }
    /// ```
    pub fn is_user_active(&self) -> bool {
        let last_secs = self.last_interaction_epoch_in_secs.load(Ordering::Relaxed);

        if last_secs == 0 {
            return false; // No interaction recorded yet
        }

        let last_time = UNIX_EPOCH + Duration::from_secs(last_secs);
        last_time.elapsed().unwrap_or(Duration::MAX) < self.idle_threshold
    }
}
