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


"""Plugin for redirecting procs from one job to another."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import cuegui.AbstractDockWidget
import cuegui.Redirect


PLUGIN_NAME = "Redirect"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "Redirect procs from one job to another."
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = "RedirectWidget"


class RedirectWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """Plugin for redirecting procs from one job to another."""

    def __init__(self, parent):
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)
        self.layout().addWidget(cuegui.Redirect.RedirectWidget(self))
