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

"""Tests for scheduler module."""

from datetime import datetime
from unittest.mock import MagicMock

from cuenimby.scheduler import NimbyScheduler


def test_parse_time():
    """Test time parsing."""
    scheduler = NimbyScheduler({})

    time1 = scheduler._parse_time("09:00")
    assert time1.hour == 9
    assert time1.minute == 0

    time2 = scheduler._parse_time("18:30")
    assert time2.hour == 18
    assert time2.minute == 30


def test_check_schedule():
    """Test schedule checking."""
    # Get current day
    current_day = datetime.now().strftime("%A").lower()

    # Create schedule for current day
    schedule = {
        current_day: {
            "start": "00:00",
            "end": "23:59",
            "state": "disabled"
        }
    }

    scheduler = NimbyScheduler(schedule)
    result = scheduler._check_schedule()

    # Should return "disabled" since we're within the time range
    assert result == "disabled"


def test_check_schedule_no_config():
    """Test schedule checking with no configuration for current day."""
    scheduler = NimbyScheduler({})
    result = scheduler._check_schedule()

    # Should return None when no schedule configured
    assert result is None


def test_scheduler_start_stop():
    """Test starting and stopping scheduler."""
    schedule = {
        "monday": {"start": "09:00", "end": "18:00", "state": "disabled"}
    }

    scheduler = NimbyScheduler(schedule)
    callback = MagicMock()

    # Start scheduler
    scheduler.start(callback)
    assert scheduler._running is True

    # Stop scheduler
    scheduler.stop()
    assert scheduler._running is False


def test_update_schedule():
    """Test updating schedule."""
    initial_schedule = {
        "monday": {"start": "09:00", "end": "18:00", "state": "disabled"}
    }
    scheduler = NimbyScheduler(initial_schedule)

    new_schedule = {
        "tuesday": {"start": "10:00", "end": "19:00", "state": "disabled"}
    }
    scheduler.update_schedule(new_schedule)

    assert scheduler.schedule == new_schedule
    assert "tuesday" in scheduler.schedule
