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
import platform
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class NotifierType(Enum):
    """Notification backend types."""
    PYNC = "pync"
    OSASCRIPT = "osascript"
    WIN10TOAST = "win10toast"
    NOTIFY2 = "notify2"
    NOTIFY_SEND = "notify-send"


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
                import shutil
                if shutil.which("terminal-notifier"):
                    self.notifier = NotifierType.OSASCRIPT  # We'll use terminal-notifier via subprocess
                    self.use_terminal_notifier = True
                else:
                    self.use_terminal_notifier = False
                    try:
                        import pync
                        self.notifier = NotifierType.PYNC
                        self.pync = pync
                    except ImportError:
                        self.notifier = NotifierType.OSASCRIPT
            elif self.system == "Windows":
                # Windows - use win10toast or fallback
                try:
                    from win10toast import ToastNotifier
                    self.notifier = NotifierType.WIN10TOAST
                    self.toaster = ToastNotifier()
                except ImportError:
                    self.notifier = None
            elif self.system == "Linux":
                # Linux - use notify2 or notify-send
                try:
                    import notify2
                    notify2.init(app_name)
                    self.notifier = NotifierType.NOTIFY2
                    self.notify2 = notify2
                except ImportError:
                    self.notifier = NotifierType.NOTIFY_SEND
            else:
                self.notifier = None
        except Exception as e:
            logger.error(f"Failed to initialize notifier: {e}")
            self.notifier = None

    def notify(self, title: str, message: str, duration: int = 5) -> None:
        """Send a desktop notification.

        Args:
            title: Notification title.
            message: Notification message.
            duration: Duration in seconds (may not be supported on all platforms).
        """
        logger.debug(f"Attempting to send notification: title='{title}', notifier={self.notifier}")
        try:
            if self.notifier == NotifierType.PYNC:
                # macOS with pync
                self.pync.notify(message, title=title, appIcon=None)
            elif self.notifier == NotifierType.OSASCRIPT:
                # macOS fallback
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
                        logger.warning(f"terminal-notifier failed: {result.stderr}")
                    else:
                        logger.debug("terminal-notifier notification sent successfully")
                else:
                    # Use osascript
                    # Escape quotes and backslashes for AppleScript
                    escaped_message = message.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                    escaped_title = title.replace('\\', '\\\\').replace('"', '\\"')

                    # Try display notification
                    script = f'display notification "{escaped_message}" with title "{escaped_title}"'
                    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)

                    if result.returncode != 0:
                        logger.warning(f"osascript notification failed: {result.stderr}")
                    else:
                        logger.debug("osascript notification sent successfully")
            elif self.notifier == NotifierType.WIN10TOAST:
                # Windows
                self.toaster.show_toast(title, message, duration=duration, threaded=True)
            elif self.notifier == NotifierType.NOTIFY2:
                # Linux with notify2
                notification = self.notify2.Notification(title, message)
                notification.set_timeout(duration * 1000)  # milliseconds
                notification.show()
            elif self.notifier == NotifierType.NOTIFY_SEND:
                # Linux fallback
                import subprocess
                subprocess.run([
                    "notify-send",
                    "-t", str(duration * 1000),
                    title,
                    message
                ], check=False)
            else:
                logger.warning(f"No notification system available. {title}: {message}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

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
            "OpenCue - NIMBY Locked",
            "Host locked due to user activity. Rendering stopped."
        )

    def notify_nimby_unlocked(self) -> None:
        """Notify when NIMBY unlocks the host."""
        self.notify(
            "OpenCue - NIMBY Unlocked",
            "Host available for rendering."
        )

    def notify_manual_lock(self) -> None:
        """Notify when user manually locks the host."""
        self.notify(
            "OpenCue - Host Disabled",
            "Host manually disabled for rendering."
        )

    def notify_manual_unlock(self) -> None:
        """Notify when user manually unlocks the host."""
        self.notify(
            "OpenCue - Host Enabled",
            "Host enabled for rendering."
        )
