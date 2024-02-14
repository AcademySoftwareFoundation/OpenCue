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


"""A Widget for displaying and editing tags."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
import re

from qtpy import QtWidgets

import cuegui.AbstractDialog
import cuegui.Constants


class TagsWidget(QtWidgets.QWidget):
    """A Widget for displaying and editing tags.

    Includes checkboxes for the given list of standard tag options, and a textfield for the
    user to enter one or more custom tags."""

    def __init__(self, allowed_tags=None, parent=None):
        """
        A Widget for displaying and editing Tags

        @ivar allowed_tags: The list of tags to include in the Standard
                            tags checkboxes
        @type allowed_tags: list<str>

        @ivar parent: The parent widget for this TagsWidget. Default is None
        @type parent: QtWidgets.QWidget
        """

        QtWidgets.QWidget.__init__(self, parent)
        layout = QtWidgets.QGridLayout(self)

        # Standard Tags
        if not allowed_tags:
            allowed_tags = cuegui.Constants.ALLOWED_TAGS
        self.standard_tags = cuegui.AbstractDialog.CheckBoxSelectionMatrix(
            'Tags', allowed_tags, [], self)
        layout.addWidget(self.standard_tags, 0, 0, 1, 2)

        # Custom Tags
        self.__enable_custom = QtWidgets.QCheckBox('Custom Tags', self)
        self.__custom = QtWidgets.QLineEdit(self)
        self.__custom.setDisabled(True)
        self.__enable_custom.toggled.connect(self.toggleCustom)  # pylint: disable=no-member
        layout.addWidget(self.__enable_custom)
        layout.addWidget(self.__custom)
        layout.setContentsMargins(0, 0, 0, 0)

    def toggleCustom(self, state):
        """
        Toggles the "custom tags" checkBox on and off.

        @param state: The state to set the "custom tags" checkBox to
        @type state: bool
        """

        if state:
            self.__enableCustom()
        else:
            self.__disableCustom()

    def __enableCustom(self):
        """
        Enables the "custom tags" checkBox and disables the standard "tags"
        """

        self.standard_tags.setDisabled(True)
        self.__custom.setDisabled(False)

    def __disableCustom(self):
        """
        Disables the "custom tags" checkBox and enables the standard "tags"
        """

        self.standard_tags.setDisabled(False)
        self.__custom.setDisabled(True)

    def set_tags(self, tags=None):
        """
        Set the tags value based on the given list of tags.

        @param tags: The list of tags to set
        @type tags: iter<str>
        """

        current_tags = tags or []
        if set(current_tags).issubset(cuegui.Constants.ALLOWED_TAGS):
            self.standard_tags.checkBoxes(current_tags)
            self.__enable_custom.setChecked(False)
            self.__disableCustom()
            self.__custom.setText('')
        else:
            self.standard_tags.checkBoxes([])
            self.__enable_custom.setChecked(True)
            self.__enableCustom()
            self.__custom.setText(','.join(current_tags))

    def get_tags(self):
        """
        Returns the list of selected tags or manually entered custom tags

        @return: The list of selected tags or manually entered custom tags
        @rtype: list<str>
        """

        if self.__enable_custom.isChecked():
            tags = str(self.__custom.text())
            tags = re.split(r'[\s,|]+', tags)
        else:
            tags = [str(t.text()) for t in self.standard_tags.checkedBoxes()]
        return [tag.strip() for tag in tags if tag.strip().isalnum()]

    def is_custom_enabled(self):
        """
        Returns whether or not the "custom tags" checkbox is enabled

        @return: Whether or not the "custom tags" checkbox is enabled
        @rtype: bool
        """

        return self.__enable_custom.isChecked()
