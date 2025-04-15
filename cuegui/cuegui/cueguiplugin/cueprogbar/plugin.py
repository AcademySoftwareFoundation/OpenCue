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
CueProgBar Plugin

This plugin launches a standalone progress bar window for a specific job,
showing a visual representation of its frame statuses (running, done, dead, etc.).

Expected CLI usage:
    python -m cuegui.cueguiplugin.cueprogbar <job_name>
"""

from typing import List
import sys
import subprocess
from qtpy.QtWidgets import QAction

from cuegui.cueguiplugin import CueGuiPlugin


class Plugin(CueGuiPlugin):
    """
    Plugin implementation for CueProgBar.
    """

    def __init__(self, job=None, parent=None, config=None):
        """
        Initialize the plugin with the job, parent, and config.

        Args:
            job: The OpenCue Job instance.
            parent: Parent QWidget (usually CueGUI context).
            config: Plugin-specific configuration from config.yaml.
        """
        super().__init__(job=job, parent=parent, config=config)

    def menuAction(self) -> List[QAction]:
        """
        Create and return a list of QAction to be added to the CueGUI menu.

        Returns:
            List[QAction]: List of actions labeled from config (or default).
        """
        label = self._config.get("menu_label", "Show Progress Bar")
        action = QAction(label, self._parent)
        action.triggered.connect(self.launch_subprocess)
        return [action]

    def launch_subprocess(self) -> None:
        """
        Launch the progress bar plugin in a separate Python process using subprocess.
        """
        if not self._job:
            return

        try:
            # Launch the subprocess with the job name as an argument
            # pylint: disable=consider-using-with
            subprocess.Popen(
                [sys.executable, "-m", "cuegui.cueguiplugin.cueprogbar", self._job.name()],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception as e:
            print(f"[CueProgBar Plugin] Failed to launch subprocess: {e}")
