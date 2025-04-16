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
Standalone launcher for the CueProgBar plugin.

Provides a way to launch the progress bar UI directly from the command line without
requiring the full CueGUI interface. Useful for debugging purposes or running as a
lightweight standalone visualizer.

Usage:
    python -m cuegui.cueguiplugin.cueprogbar <job_name>

Example:
    python -m cuegui.cueguiplugin.cueprogbar testing-test_shot-my_render_job
"""

import sys
from . import main as CueProgBarMain

def main():
    """Entry point for running the cueprogbar plugin in standalone mode."""
    if len(sys.argv) < 2:
        print("Usage: python -m cuegui.cueguiplugin.cueprogbar <job_name>")
        sys.exit(1)

    CueProgBarMain.run(sys.argv)

if __name__ == "__main__":
    main()
