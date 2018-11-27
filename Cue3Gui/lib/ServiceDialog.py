#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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


"""Service related widgets."""

import Constants
import Utils
from Manifest import Cue3, QtGui, QtCore
from TagsWidget import TagsWidget


class ServiceForm(QtGui.QWidget):
    """
    An Widget for displaying and editing a service.
    """
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.__service = None

        self.gpu_max_mb = 2 * 1024
        self.gpu_min_mb = 0
        self.gpu_tick_mb = 256

        self.name = QtGui.QLineEdit(self)
        self.threadable = QtGui.QCheckBox(self)
        self.min_cores = QtGui.QSpinBox(self)
        self.min_cores.setRange(50, int(self._cfg().get('max_cores', 16)) * 100)
        self.min_cores.setSingleStep(50)
        self.min_cores.setValue(100)
        self.max_cores = QtGui.QSpinBox(self)
        self.max_cores.setRange(0, int(self._cfg().get('max_cores', 16)) * 100)
        self.max_cores.setSingleStep(100)
        self.max_cores.setValue(100)
        self.min_memory = QtGui.QSpinBox(self)
        self.min_memory.setRange(512, int(self._cfg().get('max_memory', 48)) * 1024)
        self.min_memory.setValue(3276)
        self.min_gpu = QtGui.QSpinBox(self)
        self.min_gpu.setRange(self.gpu_min_mb, self.gpu_max_mb)
        self.min_gpu.setValue(0)
        self.min_gpu.setSingleStep(self.gpu_tick_mb)
        self.min_gpu.setSuffix(" MB")
        layout = QtGui.QGridLayout(self)
        layout.addWidget(QtGui.QLabel("Name:", self), 0, 0)
        layout.addWidget(self.name, 0, 1)
        layout.addWidget(QtGui.QLabel("Threadable:", self), 1, 0)
        layout.addWidget(self.threadable, 1, 1)
        layout.addWidget(QtGui.QLabel("Min Threads (100 = 1 thread):", self), 2, 0)
        layout.addWidget(self.min_cores, 2, 1)
        layout.addWidget(QtGui.QLabel("Max Threads (100 = 1 thread):", self), 3, 0)
        layout.addWidget(self.max_cores, 3, 1)
        layout.addWidget(QtGui.QLabel("Min Memory MB:", self), 4, 0)
        layout.addWidget(self.min_memory, 4, 1)
        layout.addWidget(QtGui.QLabel("Min Gpu Memory MB:", self), 5, 0)
        layout.addWidget(self.min_gpu, 5, 1)

        self.__buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Save,
                                                QtCore.Qt.Horizontal,
                                                self)
        self.__buttons.setDisabled(True)

        layout.addWidget(self.__buttons, 8, 1)

        QtCore.QObject.connect(self.__buttons,
                               QtCore.SIGNAL("accepted()"),
                               self.save)

        self._tags_w = TagsWidget(allowed_tags=Constants.ALLOWED_TAGS)
        layout.addWidget(self._tags_w, 6, 0, 1, 2)

    def _cfg(self):
        """
        Loads (if necessary) and returns the config values.
        Warns and returns an empty dict if there's a problem reading the config

        @return: The keys & values stored in the config file
        @rtype: dict<str:str>
        """
        if not hasattr(self, '__config'):
            self.__config = Utils.getResourceConfig()
        return self.__config

    def setService(self, service):
        """
        Update the form with data from the given service.
        """
        self.__buttons.setDisabled(False)
        self.__service = service

        self.name.setText(service.data.name)
        self.threadable.setChecked(service.data.threadable)
        self.min_cores.setValue(service.data.minCores)
        self.max_cores.setValue(service.data.maxCores)
        self.min_memory.setValue(service.data.minMemory / 1024)
        self.min_gpu.setValue(service.data.minGpu / 1024)

        self._tags_w.set_tags(service.data.tags)

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
        self._tags_w.set_tags(['general'])

    def save(self):
        """
        Create and emit a ServiceData object based
        on the contents of the form.
        """
        if len(str(self.name.text())) < 3:
            QtGui.QMessageBox.critical(self, "Error",
                                       "The service name must be at least 3 characters.")
            return

        if not str(self.name.text()).isalnum():
            QtGui.QMessageBox.critical(self, "Error", "The service name must alphanumeric.")
            return

        data = Cue3.api.service_pb2.Service()
        data.name = str(self.name.text())
        data.threadable = self.threadable.isChecked()
        data.min_cores = self.min_cores.value()
        data.max_cores = self.max_cores.value()
        data.min_memory = self.min_memory.value() * 1024
        data.min_gpu = self.min_gpu.value() * 1024

        data.tags.extend(self._tags_w.get_tags())
        self.emit(QtCore.SIGNAL("saved(PyQt_PyObject)"), data)


class ServiceManager(QtGui.QWidget):
    """
    Wraps the ServiceForm widget with the logic and controls needed
    to add, update, and detete services.
    """
    def __init__(self, show, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.__show = show
        self.__services = []
        self.__selected = None
        self.__new_service = False

        layout = QtGui.QVBoxLayout(self)

        self.__splitter = QtGui.QSplitter(QtCore.Qt.Horizontal, self)
        self.__service_list = QtGui.QListWidget(self)
        self.__form = ServiceForm(self)

        layout.addWidget(self.__splitter)
        self.__splitter.addWidget(self.__service_list)
        self.__splitter.addWidget(self.__form)

        self.__btn_new = QtGui.QPushButton("New", self)
        self.__btn_del = QtGui.QPushButton("Del", self)

        self.__btn_layout = QtGui.QHBoxLayout()
        self.__btn_layout.addWidget(self.__btn_new)
        self.__btn_layout.addWidget(self.__btn_del)
        self.__btn_layout.addStretch()
        layout.addLayout(self.__btn_layout)

        QtCore.QObject.connect(self.__btn_new,
                               QtCore.SIGNAL("clicked()"),
                               self.newService)

        QtCore.QObject.connect(self.__btn_del,
                               QtCore.SIGNAL("clicked()"),
                               self.delService)

        QtCore.QObject.connect(self.__form,
                               QtCore.SIGNAL("saved(PyQt_PyObject)"),
                               self.saved)

        QtCore.QObject.connect(self.__service_list,
                               QtCore.SIGNAL(
                                   "currentItemChanged(QListWidgetItem *,QListWidgetItem *)"),
                               self.selected)

        self.refresh()
        self.__service_list.setCurrentRow(0, QtGui.QItemSelectionModel.Select)

    def selected(self, item, old_item):
        """
        Executes if an item is selected
        """
        self.__new_service = False

        if not item:
            return

        if self.__show:
            self.__selected = self.__show.proxy.getServiceOverride(str(item.text()))
        else:
            self.__selected = Cue3.api.getService(str(item.text()))
        self.__form.setService(self.__selected)

    def saved(self, data):
        """
        Save a service to Cue3.
        """
        if not self.__show:
            msg = QtGui.QMessageBox()
            msg.setText("You are about to modify a facility wide service configuration.  "
                        "Are you in PSR-Resources?")
            msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            msg.setDefaultButton(QtGui.QMessageBox.No)
            if msg.exec_() == QtGui.QMessageBox.No:
                return

        if self.__new_service:
            if self.__show:
                self.__show.proxy.createServiceOverride(data)
            else:
                Cue3.api.createService(data)
        else:
            self.__selected.proxy.update(data)

        self.refresh()
        self.__new_service = False

        for i in range(0, self.__service_list.count()):
            item = self.__service_list.item(i)
            if item:
                if str(item.text()) == data.name:
                    self.__service_list.setCurrentRow(i, QtGui.QItemSelectionModel.Select)
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
        try:
            if not self.__show:
                self.__services = Cue3.api.getDefaultServices()
            else:
                self.__services = self.__show.proxy.getServiceOverrides()
        except Exception, e:
            return

        for service in self.__services:
            item = QtGui.QListWidgetItem(service.data.name)
            self.__service_list.addItem(item)
            if service.data.name in selected:
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
        self.__selected.proxy.delete()
        row = self.currentRow()
        if row >= 1:
            self.__service_list.setCurrentRow(row - 1, QtGui.QItemSelectionModel.Select)
        self.refresh()

    def currentRow(self):
        """
        Return the integer value of the current row.
        """
        for item in self.__service_list.selectedItems():
            return self.__service_list.row(item)
        return -1


class ServiceDialog(QtGui.QDialog):
    """
    Wraps the ServiceManager in a dialog window.
    """
    def __init__(self, show, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.__srv_manager = ServiceManager(show, self)

        self.setWindowTitle("Services")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.resize(620, 420)
