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

"""Configuration management for CueNIMBY."""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class Config:
    """Manages CueNIMBY configuration."""

    DEFAULT_CONFIG = {
        "cuebot_host": os.getenv("CUEBOT_HOST", "localhost"),
        "cuebot_port": int(os.getenv("CUEBOT_PORT", "8443")),
        "hostname": None,  # Auto-detect if None
        "poll_interval": 5,  # seconds
        "show_notifications": True,
        "notification_duration": 5,  # seconds
        "scheduler_enabled": False,
        "schedule": {
            # Example: "monday": {"start": "09:00", "end": "18:00", "state": "disabled"}
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Path to config file. If None, uses default location.
        """
        if config_path is None:
            config_dir = Path.home() / ".opencue"
            config_dir.mkdir(exist_ok=True)
            config_path = config_dir / "cuenimby.json"

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults for any missing keys
                merged_config = self.DEFAULT_CONFIG.copy()
                merged_config.update(config)
                return merged_config
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            self.save()
            return self.DEFAULT_CONFIG.copy()

    def save(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value and save."""
        self.config[key] = value
        self.save()

    @property
    def cuebot_host(self) -> str:
        """Get Cuebot host."""
        return self.config["cuebot_host"]

    @property
    def cuebot_port(self) -> int:
        """Get Cuebot port."""
        return self.config["cuebot_port"]

    @property
    def hostname(self) -> Optional[str]:
        """Get hostname."""
        return self.config["hostname"]

    @property
    def poll_interval(self) -> int:
        """Get poll interval in seconds."""
        return self.config["poll_interval"]

    @property
    def show_notifications(self) -> bool:
        """Check if notifications are enabled."""
        return self.config["show_notifications"]

    @property
    def scheduler_enabled(self) -> bool:
        """Check if scheduler is enabled."""
        return self.config["scheduler_enabled"]

    @property
    def schedule(self) -> Dict[str, Any]:
        """Get schedule configuration."""
        return self.config.get("schedule", {})
