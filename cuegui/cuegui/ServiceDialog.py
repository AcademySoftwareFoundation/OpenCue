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


"""Dialog for displaying and editing services."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from builtins import str
from builtins import range

from PySide2 import QtCore
from PySide2 import QtWidgets

import opencue

import cuegui.Constants
import cuegui.TagsWidget
import cuegui.Utils


class ServiceForm(QtWidgets.QWidget):
    """Widget for displaying and editing a service."""

    saved = QtCore.Signal(object)

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.__service = None

        self.gpu_max_mb = 2 * 1024
        self.gpu_min_mb = 0
        self.gpu_tick_mb = 256

        self.name = QtWidgets.QLineEdit(self)
        self.threadable = QtWidgets.QCheckBox(self)
        self.min_cores = QtWidgets.QSpinBox(self)
        self.min_cores.setRange(50, int(self._cfg().get('max_cores', 16)) * 100)
        self.min_cores.setSingleStep(50)
        self.min_cores.setValue(100)
        self.max_cores = QtWidgets.QSpinBox(self)
        self.max_cores.setRange(0, int(self._cfg().get('max_cores', 16)) * 100)
        self.max_cores.setSingleStep(100)
        self.max_cores.setValue(100)
        self.min_memory = QtWidgets.QSpinBox(self)
        self.min_memory.setRange(512, int(self._cfg().get('max_memory', 48)) * 1024)
        self.min_memory.setValue(3276)
        self.min_gpu = QtWidgets.QSpinBox(self)
        self.min_gpu.setRange(self.gpu_min_mb, self.gpu_max_mb)
        self.min_gpu.setValue(0)
        self.min_gpu.setSingleStep(self.gpu_tick_mb)
        self.min_gpu.setSuffix(" MB")
        self.timeout = QtWidgets.QSpinBox(self)
        self.timeout.setRange(0, 4320)
        self.timeout.setValue(0)
        self.timeout_llu = QtWidgets.QSpinBox(self)
        self.timeout_llu.setRange(0, 4320)
        self.timeout_llu.setValue(0)
        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(QtWidgets.QLabel("Name:", self), 0, 0)
        layout.addWidget(self.name, 0, 1)
        layout.addWidget(QtWidgets.QLabel("Threadable:", self), 1, 0)
        layout.addWidget(self.threadable, 1, 1)
        layout.addWidget(QtWidgets.QLabel("Min Threads (100 = 1 thread):", self), 2, 0)
        layout.addWidget(self.min_cores, 2, 1)
        layout.addWidget(QtWidgets.QLabel("Max Threads (100 = 1 thread):", self), 3, 0)
        layout.addWidget(self.max_cores, 3, 1)
        layout.addWidget(QtWidgets.QLabel("Min Memory MB:", self), 4, 0)
        layout.addWidget(self.min_memory, 4, 1)
        layout.addWidget(QtWidgets.QLabel("Min Gpu Memory MB:", self), 5, 0)
        layout.addWidget(self.min_gpu, 5, 1)
        layout.addWidget(QtWidgets.QLabel("Timeout (in minutes):", self), 6, 0)
        layout.addWidget(self.timeout, 6, 1)
        layout.addWidget(QtWidgets.QLabel("Timeout LLU (in minutes):", self), 7, 0)
        layout.addWidget(self.timeout_llu, 7, 1)
        self._tags_w = cuegui.TagsWidget.TagsWidget(allowed_tags=cuegui.Constants.ALLOWED_TAGS)
        layout.addWidget(self._tags_w, 8, 0, 1, 2)

        self.__buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save,
                                                QtCore.Qt.Horizontal,
                                                self)
        self.__buttons.setDisabled(True)

        layout.addWidget(self.__buttons, 9, 1)

        self.__buttons.accepted.connect(self.save)

    def _cfg(self):
        """
        Loads (if necessary) and returns the config values.
        Warns and returns an empty dict if there's a problem reading the config

        @return: The keys & values stored in the config file
        @rtype: dict<str:str>
        """
        if not hasattr(self, '__config'):
            self.__config = cuegui.Utils.getResourceConfig()
        return self.__config

    def setService(self, service):
        """
        Update the form with data from the given service.
        """
        self.__buttons.setDisabled(False)
        self.name.setText(service.data.name)
        self.threadable.setChecked(service.data.threadable)
        self.min_cores.setValue(service.data.min_cores)
        self.max_cores.setValue(service.data.max_cores)
        self.min_memory.setValue(service.data.min_memory // 1024)
        self.min_gpu.setValue(service.data.min_gpu // 1024)
        self._tags_w.set_tags(service.data.tags)
        self.timeout.setValue(service.data.timeout)
        self.timeout_llu.setValue(service.data.timeout_llu)

    def new(self):
        """
        Clear the form for a new service.
        """
        self.__buttons.setDisabled(False)
        self.__service = None
        self.name.setFocus()
        self.name.setText("")
        self.threadable.setChecked(False)
        self.min_cores.setValue(100)
        self.max_cores.setValue(100)
        self.min_memory.setValue(3276)
        self.min_gpu.setValue(0)
        self.timeout.setValue(0)
        self.timeout_llu.setValue(0)
        self._tags_w.set_tags(['general'])

    def save(self):
        """
        Create and emit a ServiceData object based
        on the contents of the form.
        """
        if len(str(self.name.text())) < 3:
            QtWidgets.QMessageBox.critical(self, "Error",
                                           "The service name must be at least 3 characters.")
            return

        if not str(self.name.text()).isalnum():
            QtWidgets.QMessageBox.critical(self, "Error", "The service name must alphanumeric.")
            return

        service = opencue.wrappers.service.Service()
        if self.__service:
            service.data.id = self.__service.id
        service.setName(str(self.name.text()))
        service.setThreadable(self.threadable.isChecked())
        service.setMinCores(self.min_cores.value())
        service.setMaxCores(self.max_cores.value())
        service.setMinMemory(self.min_memory.value() * 1024)
        service.setMinGpu(self.min_gpu.value() * 1024)
        service.setTimeout(self.timeout.value())
        service.setTimeoutLLU(self.timeout_llu.value())
        service.setTags(self._tags_w.get_tags())

        self.saved.emit(service)


class ServiceManager(QtWidgets.QWidget):
    """
    Wraps the ServiceForm widget with the logic and controls needed
    to add, update, and delete services.
    """
    def __init__(self, show, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.__show = show
        self.__services = []
        self.__selected = None
        self.__new_service = False

        layout = QtWidgets.QVBoxLayout(self)

        self.__splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        self.__service_list = QtWidgets.QListWidget(self)
        self.__form = ServiceForm(self)

        layout.addWidget(self.__splitter)
        self.__splitter.addWidget(self.__service_list)
        self.__splitter.addWidget(self.__form)

        self.__btn_new = QtWidgets.QPushButton("New", self)
        self.__btn_del = QtWidgets.QPushButton("Del", self)

        self.__btn_layout = QtWidgets.QHBoxLayout()
        self.__btn_layout.addWidget(self.__btn_new)
        self.__btn_layout.addWidget(self.__btn_del)
        self.__btn_layout.addStretch()
        layout.addLayout(self.__btn_layout)

        self.__btn_new.clicked.connect(self.newService)
        self.__btn_del.clicked.connect(self.delService)
        self.__form.saved.connect(self.saved)
        self.__service_list.currentItemChanged.connect(self.selected)

        self.refresh()
        self.__service_list.setCurrentRow(0, QtCore.QItemSelectionModel.Select)

    def selected(self, item, old_item):
        """
        Executes if an item is selected
        """
        del old_item

        self.__new_service = False

        if not item:
            return

        if self.__show:
            self.__selected = self.__show.getServiceOverride(str(item.text()))
        else:
            self.__selected = opencue.api.getService(str(item.text()))
        self.__form.setService(self.__selected)

    def saved(self, service):
        """
        Save a service to opencue.
        """
        if not self.__show:
            msg = QtWidgets.QMessageBox()
            msg.setText("You are about to modify a facility wide service configuration.  "
                        "Are you in PSR-Resources?")
            msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msg.setDefaultButton(QtWidgets.QMessageBox.No)
            if msg.exec_() == QtWidgets.QMessageBox.No:
                return

        if self.__new_service:
            if self.__show:
                self.__show.createServiceOverride(service.data)
            else:
                opencue.api.createService(service.data)
        else:
            service.update()

        self.refresh()
        self.__new_service = False

        for i in range(0, self.__service_list.count()):
            item = self.__service_list.item(i)
            if item:
                if str(item.text()) == service.name():
                    self.__service_list.setCurrentRow(i, QtCore.QItemSelectionModel.Select)
                    break

    def refresh(self):
        """
        Refresh the service list.
        """
        selected = []
        if not self.__new_service:
            selected = [str(t.text()) for t in
                        self.__service_list.selectedItems()]

        self.__service_list.clear()
        if not self.__show:
            self.__services = opencue.api.getDefaultServices()
        else:
            self.__services = self.__show.getServiceOverrides()

        for service in self.__services:
            item = QtWidgets.QListWidgetItem(service.name())
            self.__service_list.addItem(item)

            if service.name() in selected:
                item.setSelected(True)

        self.__service_list.sortItems()

    def newService(self):
        """
        Setup the interface for creating a new service.
        """
        for item in self.__service_list.selectedItems():
            item.setSelected(False)

        self.__form.new()
        self.__new_service = True

    def delService(self):
        """
        Delete the selected service.
        """
        self.__selected.delete()
        row = self.currentRow()
        if row >= 1:
            self.__service_list.setCurrentRow(row - 1, QtCore.QItemSelectionModel.Select)
        self.refresh()

    def currentRow(self):
        """
        Return the integer value of the current row.
        """
        for item in self.__service_list.selectedItems():
            return self.__service_list.row(item)
        return -1


class ServiceDialog(QtWidgets.QDialog):
    """
    Wraps the ServiceManager in a dialog window.
    """
    def __init__(self, show, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.__srv_manager = ServiceManager(show, self)

        self.setWindowTitle("Services")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.resize(620, 420)
