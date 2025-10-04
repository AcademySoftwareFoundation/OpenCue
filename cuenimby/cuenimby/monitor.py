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

"""Host state monitoring for CueNIMBY."""

import logging
import socket
import threading
import time
from enum import Enum
from typing import Optional, Callable, List

import opencue
from opencue.wrappers.host import Host
from opencue_proto import host_pb2

logger = logging.getLogger(__name__)


class HostState(Enum):
    """Host state enumeration."""
    AVAILABLE = "available"
    WORKING = "working"
    DISABLED = "disabled"
    NIMBY_LOCKED = "nimby_locked"
    UNKNOWN = "unknown"


class HostMonitor:
    """Monitors OpenCue host state and running frames."""

    def __init__(
        self,
        cuebot_host: str,
        cuebot_port: int,
        hostname: Optional[str] = None,
        poll_interval: int = 5
    ):
        """Initialize host monitor.

        Args:
            cuebot_host: Cuebot server hostname.
            cuebot_port: Cuebot server port.
            hostname: Host to monitor. If None, uses local hostname.
            poll_interval: Polling interval in seconds.
        """
        self.cuebot_host = cuebot_host
        self.cuebot_port = cuebot_port
        self.hostname = hostname or socket.gethostname()
        self.poll_interval = poll_interval

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._host: Optional[Host] = None
        self._current_state = HostState.UNKNOWN
        self._running_frames: List[str] = []

        # Callbacks
        self._state_change_callbacks: List[Callable[[HostState, HostState], None]] = []
        self._frame_started_callbacks: List[Callable[[str, str], None]] = []

        # Initialize Cuebot connection
        self._init_cuebot()

    def _init_cuebot(self) -> None:
        """Initialize connection to Cuebot."""
        try:
            opencue.Cuebot.setHosts([f"{self.cuebot_host}:{self.cuebot_port}"])
            logger.info(f"Connected to Cuebot at {self.cuebot_host}:{self.cuebot_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Cuebot: {e}")
            raise

    def _get_host(self) -> Optional[Host]:
        """Get host object from Cuebot."""
        try:
            return opencue.api.findHost(self.hostname)
        except Exception as e:
            logger.error(f"Failed to find host {self.hostname}: {e}")
            return None

    def _determine_state(self, host: Host) -> HostState:
        """Determine current host state.

        Args:
            host: Host object.

        Returns:
            Current host state.
        """
        try:
            # Check lock state
            lock_state = host.lockState()

            if lock_state == host_pb2.LockState.Value('NIMBY_LOCKED'):
                return HostState.NIMBY_LOCKED
            elif lock_state == host_pb2.LockState.Value('LOCKED'):
                return HostState.DISABLED

            # Check if working
            procs = host.getProcs()
            if procs:
                return HostState.WORKING

            # Check if available
            if lock_state == host_pb2.LockState.Value('OPEN'):
                return HostState.AVAILABLE

            return HostState.UNKNOWN
        except Exception as e:
            logger.error(f"Failed to determine state: {e}")
            return HostState.UNKNOWN

    def _check_new_frames(self, procs) -> None:
        """Check for newly started frames and trigger callbacks.

        Args:
            procs: List of running procs.
        """
        current_frame_ids = [proc.data.name for proc in procs]
        new_frames = set(current_frame_ids) - set(self._running_frames)

        for frame_id in new_frames:
            # Find the proc for this frame
            for proc in procs:
                if proc.data.name == frame_id:
                    try:
                        frame = proc.getFrame()
                        job_name = frame.data.job_name if hasattr(frame.data, 'job_name') else "Unknown"
                        frame_name = frame.data.name if hasattr(frame.data, 'name') else frame_id

                        for callback in self._frame_started_callbacks:
                            callback(job_name, frame_name)
                    except Exception as e:
                        logger.error(f"Failed to get frame info: {e}")
                    break

        self._running_frames = current_frame_ids

    def _monitor_loop(self) -> None:
        """Monitor host state continuously and trigger callbacks on changes."""
        while self._running:
            try:
                host = self._get_host()
                if host:
                    self._host = host
                    new_state = self._determine_state(host)

                    # Check for state changes
                    if new_state != self._current_state:
                        old_state = self._current_state
                        self._current_state = new_state
                        logger.info(f"State changed: {old_state.value} -> {new_state.value}")

                        for callback in self._state_change_callbacks:
                            callback(old_state, new_state)

                    # Check for new frames
                    procs = host.getProcs()
                    self._check_new_frames(procs)

            except Exception as e:
                logger.error(f"Error polling state: {e}")

            time.sleep(self.poll_interval)

    def start(self) -> None:
        """Start monitoring."""
        if self._running:
            logger.warning("Monitor already running")
            return

        # Fetch initial state before starting background thread
        try:
            host = self._get_host()
            if host:
                self._host = host
                self._current_state = self._determine_state(host)
                logger.info(f"Initial state: {self._current_state.value}")
            else:
                logger.warning("Could not fetch initial host state")
        except Exception as e:
            logger.error(f"Error fetching initial state: {e}")

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Monitor started")

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Monitor stopped")

    def get_current_state(self) -> HostState:
        """Get current host state."""
        return self._current_state

    def get_host(self) -> Optional[Host]:
        """Get current host object."""
        return self._host

    def lock_host(self) -> bool:
        """Lock the host (disable rendering).

        Returns:
            True if successful.

        Raises:
            RuntimeError: If host object is not available or lock operation fails.
        """
        if not self._host:
            raise RuntimeError("Host not available. Cannot lock host.")

        try:
            self._host.lock()
            # Update state immediately to reflect the change
            old_state = self._current_state
            self._current_state = HostState.DISABLED
            logger.info("Host locked")

            # Trigger state change callbacks
            if old_state != self._current_state:
                for callback in self._state_change_callbacks:
                    callback(old_state, self._current_state)

            return True
        except Exception as e:
            logger.error(f"Failed to lock host: {e}")
            raise RuntimeError(f"Failed to lock host: {e}") from e

    def unlock_host(self) -> bool:
        """Unlock the host (enable rendering).

        Returns:
            True if successful.

        Raises:
            RuntimeError: If host object is not available or unlock operation fails.
        """
        if not self._host:
            raise RuntimeError("Host not available. Cannot unlock host.")

        try:
            self._host.unlock()
            # Update state immediately to reflect the change
            old_state = self._current_state
            self._current_state = HostState.AVAILABLE
            logger.info("Host unlocked")

            # Trigger state change callbacks
            if old_state != self._current_state:
                for callback in self._state_change_callbacks:
                    callback(old_state, self._current_state)

            return True
        except Exception as e:
            logger.error(f"Failed to unlock host: {e}")
            raise RuntimeError(f"Failed to unlock host: {e}") from e

    def on_state_change(self, callback: Callable[[HostState, HostState], None]) -> None:
        """Register callback for state changes.

        Args:
            callback: Function to call with (old_state, new_state).
        """
        self._state_change_callbacks.append(callback)

    def on_frame_started(self, callback: Callable[[str, str], None]) -> None:
        """Register callback for frame starts.

        Args:
            callback: Function to call with (job_name, frame_name).
        """
        self._frame_started_callbacks.append(callback)
