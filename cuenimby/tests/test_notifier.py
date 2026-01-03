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

"""Tests for notifier module."""

from unittest.mock import MagicMock

from cuenimby.notifier import Notifier


def test_notifier_init():
    """Test notifier initialization."""
    notifier = Notifier("TestApp")
    assert notifier.app_name == "TestApp"
    assert notifier.system is not None


def test_notify_job_started():
    """Test job started notification."""
    notifier = Notifier()

    # Mock the notify method
    notifier.notify = MagicMock()

    notifier.notify_job_started("test_job", "frame_001")

    # Verify notify was called with correct parameters
    notifier.notify.assert_called_once()
    args = notifier.notify.call_args[0]
    assert "Frame Started" in args[0]
    assert "test_job" in args[1]
    assert "frame_001" in args[1]


def test_notify_nimby_locked():
    """Test NIMBY locked notification."""
    notifier = Notifier()
    notifier.notify = MagicMock()

    notifier.notify_nimby_locked()

    notifier.notify.assert_called_once()
    args = notifier.notify.call_args[0]
    assert "NIMBY Locked" in args[0]


def test_notify_nimby_unlocked():
    """Test NIMBY unlocked notification."""
    notifier = Notifier()
    notifier.notify = MagicMock()

    notifier.notify_nimby_unlocked()

    notifier.notify.assert_called_once()
    args = notifier.notify.call_args[0]
    assert "NIMBY Unlocked" in args[0]


def test_notify_manual_lock():
    """Test manual lock notification."""
    notifier = Notifier()
    notifier.notify = MagicMock()

    notifier.notify_manual_lock()

    notifier.notify.assert_called_once()
    args = notifier.notify.call_args[0]
    assert "Host Disabled" in args[0]


def test_notify_manual_unlock():
    """Test manual unlock notification."""
    notifier = Notifier()
    notifier.notify = MagicMock()

    notifier.notify_manual_unlock()

    notifier.notify.assert_called_once()
    args = notifier.notify.call_args[0]
    assert "Host Enabled" in args[0]
