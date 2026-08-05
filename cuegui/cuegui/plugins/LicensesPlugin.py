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


"""Plugin for inspecting application licenses (read-only)."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import cuegui.AbstractDockWidget
import cuegui.LicensesWidget


PLUGIN_NAME = "Licenses"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "A read-only view of the application licenses Cuebot polls"
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = "LicensesDockWidget"


class LicensesDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """Plugin for inspecting application licenses (read-only)."""

    def __init__(self, parent):
        super(LicensesDockWidget, self).__init__(parent, PLUGIN_NAME)

        self.__licensesWidget = cuegui.LicensesWidget.LicensesWidget(self)

        self.layout().addWidget(self.__licensesWidget)

        self.pluginRegisterSettings([("columnVisibility",
                                      self.__licensesWidget.getColumnVisibility,
                                      self.__licensesWidget.setColumnVisibility),
                                      ("columnOrder",
                                      self.__licensesWidget.getColumnOrder,
                                      self.__licensesWidget.setColumnOrder)])
