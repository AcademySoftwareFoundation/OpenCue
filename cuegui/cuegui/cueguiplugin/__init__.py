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

"""
Plugin interface definition for CueGUI plugins.

Each plugin must:
- Be placed in a subfolder under `cueguiplugin/`
- Contain a `plugin.py` with a class named `Plugin`
- Optionally include a `config.yaml` for settings
- Implement the required interface defined below

This abstract base class (ABC) enforces the structure and provides
typing hints for better readability, development, and dynamic loading.
"""

from typing import List, Optional
from abc import ABC, abstractmethod
from qtpy import QtWidgets


class CueGuiPlugin(ABC):
    """
    Abstract base class for CueGUI plugins.

    All CueGUI plugins should subclass this and implement `menuAction()`.
    """

    def __init__(
            self,
            job: Optional[object] = None,
            parent: Optional[QtWidgets.QWidget] = None,
            config: Optional[dict] = None,
    ):
        """
        Initialize the plugin with a job, optional parent QtWidgets.QWidget, and optional config.

        Args:
            job (Optional[object]): The Cue job the plugin will interact with.
            parent (Optional[QtWidgets.QWidget]): Parent widget for any UI elements.
            config (Optional[dict]): Plugin-specific configuration loaded from config.yaml.
        """
        self._job = job
        self._parent = parent
        self._config = config or {}

    @abstractmethod
    def menuAction(self) -> List[QtWidgets.QAction]:
        """
        Return a list of QtWidgets.QAction to be inserted into the CueGUI menu.

        Returns:
            List[QtWidgets.QAction]: One or more actions to display in job/layer/frame menus.
        """
