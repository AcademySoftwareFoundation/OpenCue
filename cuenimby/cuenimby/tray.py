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

"""System tray application for CueNIMBY."""

import logging
import os
import subprocess
import sys
from typing import Optional

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as Item

from .config import Config
from .monitor import HostMonitor, HostState
from .notifier import Notifier
from .scheduler import NimbyScheduler

logger = logging.getLogger(__name__)


class CueNIMBYTray:
    """System tray application for NIMBY control."""

    # Icon colors for different states
    ICON_COLORS = {
        HostState.AVAILABLE: "#00AA00",  # Green
        HostState.WORKING: "#0066CC",    # Blue
        HostState.DISABLED: "#CC0000",   # Red
        HostState.NIMBY_LOCKED: "#FF9900", # Orange
        HostState.UNKNOWN: "#888888",    # Gray
    }

    def __init__(self, config: Optional[Config] = None):
        """Initialize tray application.

        Args:
            config: Configuration object. If None, uses default.
        """
        self.config = config or Config()
        self.monitor: Optional[HostMonitor] = None
        self.notifier: Optional[Notifier] = None
        self.scheduler: Optional[NimbyScheduler] = None
        self.icon: Optional[pystray.Icon] = None

        self._init_components()

    def _init_components(self) -> None:
        """Initialize application components."""
        # Initialize notifier
        if self.config.show_notifications:
            self.notifier = Notifier()

        # Initialize monitor
        self.monitor = HostMonitor(
            cuebot_host=self.config.cuebot_host,
            cuebot_port=self.config.cuebot_port,
            hostname=self.config.hostname,
            poll_interval=self.config.poll_interval
        )

        # Register callbacks
        self.monitor.on_state_change(self._on_state_change)
        self.monitor.on_frame_started(self._on_frame_started)

        # Initialize scheduler if enabled
        if self.config.scheduler_enabled and self.config.schedule:
            self.scheduler = NimbyScheduler(self.config.schedule)

    def _create_icon_image(self, state: HostState) -> Image.Image:
        """Create icon image for given state.

        Args:
            state: Host state.

        Returns:
            PIL Image object.
        """
        # Create a simple circular icon
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)

        # Draw circle with state color
        color = self.ICON_COLORS.get(state, self.ICON_COLORS[HostState.UNKNOWN])
        draw.ellipse([8, 8, 56, 56], fill=color, outline='black', width=2)

        return image

    def _update_icon(self) -> None:
        """Update tray icon to reflect current state."""
        if self.icon:
            state = self.monitor.get_current_state()
            self.icon.icon = self._create_icon_image(state)
            self.icon.title = f"CueNIMBY - {state.value.title()}"

    def _on_state_change(self, old_state: HostState, new_state: HostState) -> None:
        """Handle state change.

        Args:
            old_state: Previous state.
            new_state: New state.
        """
        logger.info(f"State changed: {old_state.value} -> {new_state.value}")
        self._update_icon()

        # Send notifications
        if self.notifier:
            if new_state == HostState.NIMBY_LOCKED:
                self.notifier.notify_nimby_locked()
            elif old_state == HostState.NIMBY_LOCKED and new_state == HostState.AVAILABLE:
                self.notifier.notify_nimby_unlocked()
            elif new_state == HostState.DISABLED and old_state != HostState.NIMBY_LOCKED:
                self.notifier.notify_manual_lock()
            elif new_state == HostState.AVAILABLE and old_state == HostState.DISABLED:
                self.notifier.notify_manual_unlock()

    def _on_frame_started(self, job_name: str, frame_name: str) -> None:
        """Handle frame start.

        Args:
            job_name: Job name.
            frame_name: Frame name.
        """
        logger.info(f"Frame started: {job_name}/{frame_name}")
        if self.notifier:
            self.notifier.notify_job_started(job_name, frame_name)

    def _on_scheduler_state_change(self, desired_state: str) -> None:
        """Handle scheduler state change.

        Args:
            desired_state: Desired state ("available" or "disabled").
        """
        try:
            if desired_state == "disabled":
                self.monitor.lock_host()
            elif desired_state == "available":
                self.monitor.unlock_host()
        except RuntimeError as e:
            logger.error(f"Scheduler failed to change host state: {e}")
            if self.notifier:
                self.notifier.notify("Scheduler Error", str(e))

    def _toggle_available(self, icon, item) -> None:
        """Toggle host availability."""
        current_state = self.monitor.get_current_state()

        try:
            if current_state in (HostState.DISABLED, HostState.NIMBY_LOCKED):
                # Enable host
                if self.monitor.unlock_host():
                    logger.info("Host enabled by user")
            else:
                # Disable host
                if self.monitor.lock_host():
                    logger.info("Host disabled by user")
        except RuntimeError as e:
            logger.error(f"Failed to toggle host state: {e}")
            if self.notifier:
                self.notifier.notify("Error", str(e))

    def _is_available(self, item) -> bool:
        """Check if host is available (for menu checkbox)."""
        state = self.monitor.get_current_state()
        return state in (HostState.AVAILABLE, HostState.WORKING)

    def _toggle_notifications(self, icon, item) -> None:
        """Toggle notifications on/off."""
        enabled = not self.config.show_notifications
        self.config.set("show_notifications", enabled)

        if enabled:
            self.notifier = Notifier()
        else:
            self.notifier = None

        logger.info(f"Notifications {'enabled' if enabled else 'disabled'}")

    def _notifications_enabled(self, item) -> bool:
        """Check if notifications are enabled (for menu checkbox)."""
        return self.config.show_notifications

    def _toggle_scheduler(self, icon, item) -> None:
        """Toggle scheduler on/off."""
        enabled = not self.config.scheduler_enabled
        self.config.set("scheduler_enabled", enabled)

        if enabled and self.config.schedule:
            self.scheduler = NimbyScheduler(self.config.schedule)
            self.scheduler.start(self._on_scheduler_state_change)
        elif self.scheduler:
            self.scheduler.stop()
            self.scheduler = None

        logger.info(f"Scheduler {'enabled' if enabled else 'disabled'}")

    def _scheduler_enabled(self, item) -> bool:
        """Check if scheduler is enabled (for menu checkbox)."""
        return self.config.scheduler_enabled

    def _show_about(self, icon, item) -> None:
        """Show about dialog using native platform dialogs."""
        from . import __version__

        # Always use native dialogs for About (more reliable than notifications)
        try:
            if sys.platform == "darwin":  # macOS
                # For AppleScript, use return for newlines
                about_message = f"CueNIMBY v{__version__}\n\nOpenCue NIMBY Control\n\nHost: {self.monitor.hostname}"
                # Escape quotes and replace newlines with 'return' for AppleScript
                escaped_message = about_message.replace('"', '\\"').replace('\n', '" & return & "')
                script = f'display dialog "{escaped_message}" with title "About CueNIMBY" buttons {{"OK"}} default button "OK"'
                subprocess.run(["osascript", "-e", script], check=False)
                logger.info(f"About CueNIMBY: {about_message}")
            elif sys.platform == "win32":  # Windows
                about_message = f"CueNIMBY v{__version__}\n\nOpenCue NIMBY Control\n\nHost: {self.monitor.hostname}"
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, about_message, "About CueNIMBY", 0)
                logger.info(f"About CueNIMBY: {about_message}")
            else:  # Linux
                about_message = f"CueNIMBY v{__version__}\n\nOpenCue NIMBY Control\n\nHost: {self.monitor.hostname}"
                # Try zenity or kdialog
                try:
                    subprocess.run(["zenity", "--info", "--title=About CueNIMBY", f"--text={about_message}"], check=False)
                    logger.info(f"About CueNIMBY: {about_message}")
                except FileNotFoundError:
                    try:
                        subprocess.run(["kdialog", "--msgbox", about_message, "--title", "About CueNIMBY"], check=False)
                        logger.info(f"About CueNIMBY: {about_message}")
                    except FileNotFoundError:
                        # Fallback: use notification if available, otherwise log
                        if self.notifier:
                            self.notifier.notify("About CueNIMBY", about_message)
                        else:
                            logger.warning(f"No dialog system available. About CueNIMBY: {about_message}")
        except Exception as e:
            logger.error(f"Failed to show about dialog: {e}")
            # Fallback to console output
            from . import __version__
            about_message = f"CueNIMBY v{__version__}\n\nOpenCue NIMBY Control\n\nHost: {self.monitor.hostname}"
            print(f"\nAbout CueNIMBY\n{about_message}\n")

    def _open_config(self, icon, item) -> None:
        """Open config file in default editor."""
        config_path = str(self.config.config_path)
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", config_path], check=True)
            elif sys.platform == "win32":  # Windows
                os.startfile(config_path)
            else:  # Linux and others
                subprocess.run(["xdg-open", config_path], check=True)
            logger.info(f"Opened config file: {config_path}")
        except Exception as e:
            logger.error(f"Failed to open config file: {e}")
            if self.notifier:
                self.notifier.notify(
                    "Error",
                    f"Failed to open config file: {e}"
                )

    def _quit(self, icon, item) -> None:
        """Quit application."""
        logger.info("Shutting down CueNIMBY")
        self.stop()
        icon.stop()

    def _create_menu(self) -> pystray.Menu:
        """Create tray menu.

        Returns:
            pystray.Menu object.
        """
        return pystray.Menu(
            Item(
                "Available",
                self._toggle_available,
                checked=self._is_available
            ),
            Item(
                "Notifications",
                self._toggle_notifications,
                checked=self._notifications_enabled
            ),
            Item(
                "Scheduler",
                self._toggle_scheduler,
                checked=self._scheduler_enabled
            ),
            pystray.Menu.SEPARATOR,
            Item("Open Config File", self._open_config),
            Item("About", self._show_about),
            Item("Quit", self._quit)
        )

    def start(self) -> None:
        """Start the tray application."""
        # Start monitor
        self.monitor.start()

        # Start scheduler if enabled
        if self.scheduler:
            self.scheduler.start(self._on_scheduler_state_change)

        # Create and run tray icon
        state = self.monitor.get_current_state()
        self.icon = pystray.Icon(
            "cuenimby",
            self._create_icon_image(state),
            f"CueNIMBY - {state.value.title()}",
            self._create_menu()
        )

        logger.info("CueNIMBY tray started")
        self.icon.run()

    def stop(self) -> None:
        """Stop the tray application."""
        if self.monitor:
            self.monitor.stop()
        if self.scheduler:
            self.scheduler.stop()
        logger.info("CueNIMBY tray stopped")
