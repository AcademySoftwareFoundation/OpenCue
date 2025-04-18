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


"""A widget for displaying and editing limits."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str

from qtpy import QtWidgets

import cuegui.AbstractDialog


class LimitSelectionWidget(QtWidgets.QWidget):
    """A widget for displaying and editing limits.

    Includes checkboxes for the given list of limit options."""

    def __init__(self, limits=None, parent=None):
        """
        @param limits: The list of limits to include as checkboxes.
        @type limits: list<str>
        @param parent: The parent widget for this LimitSelectionWidget. Default is None
        @type parent: QtWidgets.QWidget
        """
        QtWidgets.QWidget.__init__(self, parent)
        layout = QtWidgets.QGridLayout(self)

        self.limits = cuegui.AbstractDialog.CheckBoxSelectionMatrix(
            'Limits', limits, [], self)
        layout.addWidget(self.limits, 0, 0, 1, 2)
        layout.setContentsMargins(0, 0, 0, 0)

    def enable_limits(self, limits_to_enable=None):
        """Sets the limit value based on the given list of limits.

        @param limits_to_enable: The list of limits to enable
        @type limits_to_enable: iter<str>
        """
        limits_to_enable = limits_to_enable or []
        self.limits.checkBoxes(limits_to_enable)

    def get_selected_limits(self):
        """Returns the list of selected limits.

        @return: The list of selected limits
        @rtype: list<str>
        """
        limit_names = [str(limit.text()) for limit in self.limits.checkedBoxes()]
        return [limit.strip() for limit in limit_names if limit.strip()]
