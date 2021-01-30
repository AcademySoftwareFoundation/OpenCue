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


"""Plugin for managing limits."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import cuegui.AbstractDockWidget
import cuegui.LimitsWidget


PLUGIN_NAME = "Limits"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An administrator interface to limits"
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = "LimitsDockWidget"


class LimitsDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """Widget for managing limits."""

    def __init__(self, parent):
        super(LimitsDockWidget, self).__init__(parent, PLUGIN_NAME)

        self.__limitsWidget = cuegui.LimitsWidget.LimitsWidget(self)

        self.layout().addWidget(self.__limitsWidget)

        self.pluginRegisterSettings([("columnVisibility",
                                      self.__limitsWidget.getColumnVisibility,
                                      self.__limitsWidget.setColumnVisibility),
                                      ("columnOrder",
                                      self.__limitsWidget.getColumnOrder,
                                      self.__limitsWidget.setColumnOrder)])
