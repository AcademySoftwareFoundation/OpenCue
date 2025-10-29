#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Desktop notification system for CueNIMBY."""

import logging
import os
import platform
from enum import Enum

logger = logging.getLogger(__name__)


class NotifierType(Enum):
    """Notification backend types."""
    PYNC = "pync"
    OSASCRIPT = "osascript"
    WIN10TOAST = "win10toast"
    NOTIFY2 = "notify2"
    NOTIFY_SEND = "notify-send"

OPENCUE_ICON = os.path.join(os.path.dirname(__file__), "icons", "opencue-icon.ico")

class Notifier:
    """Cross-platform desktop notification handler."""

    def __init__(self, app_name: str = "CueNIMBY"):
        """Initialize notifier.

        Args:
            app_name: Application name to display in notifications.
        """
        self.app_name = app_name
        self.system = platform.system()
        self.use_terminal_notifier = False

        # Try to import notification library
        try:
            if self.system == "Darwin":
                # macOS - try terminal-notifier first (most reliable), then pync, then osascript
                # pylint: disable=import-outside-toplevel
                import shutil
                if shutil.which("terminal-notifier"):
                    # We'll use terminal-notifier via subprocess
                    self.notifier = NotifierType.OSASCRIPT
                    self.use_terminal_notifier = True
                else:
                    self.use_terminal_notifier = False
                    try:
                        # pylint: disable=import-outside-toplevel
                        import pync
                        self.notifier = NotifierType.PYNC
                        self.pync = pync
                    except ImportError:
                        self.notifier = NotifierType.OSASCRIPT
            elif self.system == "Windows":
                # Windows - use win10toast or fallback
                try:
                    # pylint: disable=import-outside-toplevel
                    from win10toast import ToastNotifier
                    self.notifier = NotifierType.WIN10TOAST
                    self.toaster = ToastNotifier()
                except ImportError:
                    self.notifier = None
            elif self.system == "Linux":
                # Linux - use notify2 or notify-send
                try:
                    # pylint: disable=import-outside-toplevel
                    import notify2
                    notify2.init(app_name)
                    self.notifier = NotifierType.NOTIFY2
                    self.notify2 = notify2
                except ImportError:
                    self.notifier = NotifierType.NOTIFY_SEND
            else:
                self.notifier = None
        except Exception as e:
            logger.error("Failed to initialize notifier: %s", e)
            self.notifier = None

    def notify(self, title: str, message: str, duration: int = 5) -> None:
        """Send a desktop notification.

        Args:
            title: Notification title.
            message: Notification message.
            duration: Duration in seconds (may not be supported on all platforms).
        """
        logger.debug("Attempting to send notification: title='%s', notifier=%s",
                      title, self.notifier)
        try:
            if self.notifier == NotifierType.PYNC:
                # macOS with pync
                self.pync.notify(message, title=title, appIcon=None)
            elif self.notifier == NotifierType.OSASCRIPT:
                # macOS fallback
                # pylint: disable=import-outside-toplevel
                import subprocess

                if self.use_terminal_notifier:
                    # Use terminal-notifier (most reliable on macOS)
                    result = subprocess.run([
                        "terminal-notifier",
                        "-title", title,
                        "-message", message,
                        "-group", self.app_name
                    ], capture_output=True, text=True, check=False)

                    if result.returncode != 0:
                        logger.warning("terminal-notifier failed: %s", result.stderr)
                    else:
                        logger.debug("terminal-notifier notification sent successfully")
                else:
                    # Use osascript
                    # Escape quotes and backslashes for AppleScript
                    esc_message = message.replace('\\', '\\\\')
                    esc_message = esc_message.replace('"', '\\"').replace('\n', '\\n')
                    esc_title = title.replace('\\', '\\\\').replace('"', '\\"')

                    # Try display notification
                    script = f'display notification "{esc_message}" with title "{esc_title}"'
                    result = subprocess.run(["osascript", "-e", script],
                                             capture_output=True, text=True, check=False)

                    if result.returncode != 0:
                        logger.warning("osascript notification failed: %s", result.stderr)
                    else:
                        logger.debug("osascript notification sent successfully")
            elif self.notifier == NotifierType.WIN10TOAST:
                # Windows
                self.toaster.show_toast(title, message, icon_path=OPENCUE_ICON,
                                        duration=duration, threaded=True)
            elif self.notifier == NotifierType.NOTIFY2:
                # Linux with notify2
                notification = self.notify2.Notification(title, message)
                notification.set_timeout(duration * 1000)  # milliseconds
                notification.show()
            elif self.notifier == NotifierType.NOTIFY_SEND:
                # Linux fallback
                # pylint: disable=import-outside-toplevel
                import subprocess
                subprocess.run([
                    "notify-send",
                    "-t", str(duration * 1000),
                    title,
                    message
                ], check=False)
            else:
                logger.warning("No notification system available. %s: %s", title, message)
        except Exception as e:
            logger.error("Failed to send notification: %s", e)

    def notify_job_started(self, job_name: str, frame_name: str) -> None:
        """Notify when a job starts on this host.

        Args:
            job_name: Name of the job.
            frame_name: Name of the frame.
        """
        self.notify(
            "OpenCue - Frame Started",
            f"Rendering: {job_name}/{frame_name}"
        )

    def notify_nimby_locked(self) -> None:
        """Notify when NIMBY locks the host."""
        self.notify(
            "OpenCue - NIMBY Locked 🔒",
            "RQD locked due to user activity. Rendering stopped."
        )

    def notify_nimby_unlocked(self) -> None:
        """Notify when NIMBY unlocks the host."""
        self.notify(
            "OpenCue - NIMBY Unlocked 🔓",
            "RQD available for rendering."
        )

    def notify_manual_lock(self) -> None:
        """Notify when user manually locks the host."""
        self.notify(
            "OpenCue - Host Disabled 🔒",
            "RQD manually disabled for rendering."
        )

    def notify_manual_unlock(self) -> None:
        """Notify when user manually unlocks the host."""
        self.notify(
            "OpenCue - Host Enabled 🔓",
            "RQD enabled for rendering."
        )

    def notify_host_recovered(self) -> None:
        """Notify when host recovers from down state."""
        self.notify(
            "OpenCue - Host Recovered",
            "RQD is back online and available for rendering."
        )

    def notify_host_down(self) -> None:
        """Notify when host goes down."""
        self.notify(
            "OpenCue - Host Down",
            "Host is offline or unreachable by Cuebot, check if RQD is running."
        )

    def notify_host_lagging(self) -> None:
        """Notify when host is lagging."""
        self.notify(
            "OpenCue - Host Lagging",
            "Host is experiencing high latency, RQD might be down."
        )

    def notify_error(self, error_message: str) -> None:
        """Notify when an error occurs.

        Args:
            error_message: The error message to display.
        """
        self.notify(
            "OpenCue - Error",
            error_message
        )

    def notify_cuebot_unreachable(self) -> None:
        """Notify when cuebot is unreachable."""
        self.notify(
            "OpenCue - Cuebot Unreachable",
            "Unable to contact Cuebot, please check your network connection."
        )

    def notify_host_repairing(self) -> None:
        """Notify when host is under repair."""
        self.notify(
            "OpenCue - Host Under Repair",
            "Host is under repair and not available for rendering."
        )
