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

"""Scheduler for time-based NIMBY control."""

import logging
import threading
import time
from datetime import datetime, time as dt_time
from typing import Dict, Optional, Callable

logger = logging.getLogger(__name__)


class NimbyScheduler:
    """Manages time-based NIMBY scheduling."""

    def __init__(self, schedule: Dict[str, Dict[str, str]]):
        """Initialize scheduler.

        Args:
            schedule: Schedule configuration dict.
                Format: {
                    "monday": {"start": "09:00", "end": "18:00", "state": "disabled"},
                    "tuesday": {"start": "09:00", "end": "18:00", "state": "disabled"},
                    ...
                }
        """
        self.schedule = schedule
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_state: Optional[str] = None
        self._state_change_callback: Optional[Callable[[str], None]] = None

    def _parse_time(self, time_str: str) -> dt_time:
        """Parse time string to time object.

        Args:
            time_str: Time string in HH:MM format.

        Returns:
            datetime.time object.
        """
        hour, minute = map(int, time_str.split(':'))
        return dt_time(hour, minute)

    def _get_current_schedule(self) -> Optional[Dict[str, str]]:
        """Get schedule for current day.

        Returns:
            Schedule dict for current day, or None if not configured.
        """
        current_day = datetime.now().strftime("%A").lower()
        return self.schedule.get(current_day)

    def _check_schedule(self) -> Optional[str]:
        """Check if current time is within scheduled period.

        Returns:
            Desired state ("disabled" or "available"), or None if not scheduled.
        """
        day_schedule = self._get_current_schedule()
        if not day_schedule:
            return None

        current_time = datetime.now().time()
        start_time = self._parse_time(day_schedule["start"])
        end_time = self._parse_time(day_schedule["end"])
        desired_state = day_schedule["state"]

        # Check if current time is within scheduled period
        if start_time <= current_time <= end_time:
            return desired_state

        # Outside scheduled period - return opposite state
        return "available" if desired_state == "disabled" else "disabled"

    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                desired_state = self._check_schedule()

                if desired_state and desired_state != self._last_state:
                    logger.info(f"Scheduler changing state to: {desired_state}")
                    if self._state_change_callback:
                        self._state_change_callback(desired_state)
                    self._last_state = desired_state

            except Exception as e:
                logger.error(f"Scheduler error: {e}")

            # Check every minute
            time.sleep(60)

    def start(self, state_change_callback: Callable[[str], None]) -> None:
        """Start the scheduler.

        Args:
            state_change_callback: Function to call when state should change.
        """
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._state_change_callback = state_change_callback
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")

    def update_schedule(self, schedule: Dict[str, Dict[str, str]]) -> None:
        """Update schedule configuration.

        Args:
            schedule: New schedule configuration.
        """
        self.schedule = schedule
        logger.info("Schedule updated")
