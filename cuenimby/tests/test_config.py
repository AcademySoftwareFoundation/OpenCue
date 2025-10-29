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

"""Tests for config module."""

import tempfile
from pathlib import Path

from cuenimby.config import Config


def test_default_config():
    """Test default configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.json"
        config = Config(str(config_path))

        assert config.cuebot_host is not None
        assert config.cuebot_port > 0
        assert config.poll_interval > 0
        assert isinstance(config.show_notifications, bool)


def test_config_save_and_load():
    """Test saving and loading configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.json"

        # Create and save config
        config1 = Config(str(config_path))
        config1.set("cuebot_host", "test.example.com")
        config1.set("cuebot_port", 9999)

        # Load config in new instance
        config2 = Config(str(config_path))
        assert config2.cuebot_host == "test.example.com"
        assert config2.cuebot_port == 9999


def test_config_get_set():
    """Test get and set methods."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.json"
        config = Config(str(config_path))

        # Test set and get
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value"

        # Test get with default
        assert config.get("nonexistent", "default") == "default"


def test_config_schedule():
    """Test schedule configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.json"
        config = Config(str(config_path))

        schedule = {
            "monday": {"start": "09:00", "end": "18:00", "state": "disabled"}
        }
        config.set("schedule", schedule)

        assert config.schedule == schedule
        assert "monday" in config.schedule
