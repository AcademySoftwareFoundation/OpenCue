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


import Constants
import Utils
from Manifest import QtCore, QtGui, QtWidgets, opencue
from TagsWidget import TagsWidget


def warning(msg, parent=None):
    """
    Utility method for poping up a warning.
    """
    box = QtWidgets.QMessageBox(parent)
    box.setText(msg)
    box.exec_()


class EnableableItem(QtWidgets.QWidget):
    def __init__(self, widget, enable, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.__widget = widget
        self.__checkbox = QtWidgets.QCheckBox()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(0)
        if enable:
            self.__widget.setDisabled(True)
            layout.addWidget(self.__checkbox)
            self.__checkbox.toggled.connect(self.enable)
        layout.addWidget(self.__widget)

    def getWidget(self):
        return self.__widget

    def isEnabled(self):
        return self.__checkbox.isChecked()

    def enable(self, b):
        self.__checkbox.setChecked(b)
        self.__widget.setDisabled(b == False)


class LayerPropertiesItem(QtWidgets.QWidget):
    """
    An key/value widget for populating a dialog box.
    """
    def __init__(self, label, widget, stretch=True, help=None, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.__label = label
        self.__widget = widget

        layout = QtWidgets.QHBoxLayout(self)
        if label:
            layout.addWidget(QtWidgets.QLabel(label, self))
        if stretch:
            layout.addStretch()
        layout.addWidget(self.__widget)
        if help:
            layout.addWidget(help)


class SlideSpinner(QtWidgets.QWidget):
    """
    A QSlider and QSpinBox
    """
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.slider = QtWidgets.QSlider(self)
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.slider.setTickPosition(QtWidgets.QSlider.TicksBelow)

        self.spinner = QtWidgets.QDoubleSpinBox(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.slider)
        layout.addWidget(self.spinner)


class LayerPropertiesDialog(QtWidgets.QDialog):
    """
    A dialog box for editing a layer.
    """
    def __init__(self, layers, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.__layers = [opencue.getLayer(opencue.id(l)) for l in layers]

        self.setWindowTitle("Layer Properties")

        multiSelect = len(self.__layers) > 1

        self.mem_max_gb = float(self._cfg().get('max_memory', 80.0))
        self.mem_min_gb = 0.25
        self.mem_max_kb = int(self.mem_max_gb * 1024 * 1024)
        self.mem_min_kb = int(self.mem_min_gb * 1024 * 1024)

        self.gpu_max_kb = 2 * 1024 * 1024
        self.gpu_min_kb = 0
        self.gpu_tick_kb = 256 * 1024
        self.gpu_max_gb = 2.0
        self.gpu_min_gb = 0.0
        self.gpu_tick_gb = .25

        self.__group = QtWidgets.QGroupBox("Resource Options", self)

        ## Memory
        self.__mem = SlideSpinner(self)
        self.__mem.slider.setMinimumWidth(200)
        self.__mem.slider.setRange(self.mem_min_kb, self.mem_max_kb)
        self.__mem.slider.setTickInterval(self.mem_min_kb)
        self.__mem.slider.setSingleStep(self.mem_min_kb)
        self.__mem.spinner.setSuffix(" GB")
        self.__mem.spinner.setRange(self.mem_min_gb, self.mem_max_gb)

        ## Cores
        self.__core = QtWidgets.QDoubleSpinBox(self)
        self.__core.setDecimals(1)
        self.__core.setRange(0, int(self._cfg().get('max_cores', 16)))
        self.__core.setSingleStep(1)

        ## Max cores
        self.__max_cores = QtWidgets.QSpinBox(self)
        self.__max_cores.setRange(0, int(self._cfg().get('max_cores', 16)))
        self.__max_cores.setSingleStep(1)

        ## Disable this for everything except commander.
        if QtGui.qApp.applicationName() != "CueCommander":
            self.__core.setDisabled(True)

        # Threads
        self.__thread = QtWidgets.QCheckBox(self)
        self.__thread.setChecked(self.getThreading())

        # Memory Optimizer
        self.__mem_opt = QtWidgets.QCheckBox()
        self.__mem_opt.setChecked(self.getMemoryOptSetting())

        # Tags
        self.__tags = LayerTagsWidget(self.__layers, self)

        ## GPU Memory
        self.__gpu = SlideSpinner(self)
        self.__gpu.slider.setMinimumWidth(200)
        self.__gpu.slider.setRange(self.gpu_min_kb, self.gpu_max_kb / self.gpu_tick_kb)
        self.__gpu.slider.setTickInterval(1)
        self.__gpu.slider.setSingleStep(1)
        self.__gpu.slider.setPageStep(1)
        self.__gpu.spinner.setSuffix(' GB')
        self.__gpu.spinner.setRange(self.gpu_min_gb, self.gpu_max_gb)
        self.__gpu.spinner.setSingleStep(self.gpu_tick_gb)

        # Our dialog buttons.
        self.__buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save |
                                                    QtWidgets.QDialogButtonBox.Cancel,
                                                    QtCore.Qt.Horizontal,
                                                    self)

        # Setup signals
        self.__mem.slider.valueChanged.connect(self.__translateToMemSpinbox)
        self.__mem.spinner.valueChanged.connect(self.__translateToMemSlider)
        self.__gpu.slisder.valueChanged.connect(self.__translateToGpuSpinbox)
        self.__gpu.spinner.valueChanged.connect(self.__translateToGpuSlider)
        self.__buttons.accepted.connect(self.verify)
        self.__buttons.rejected.connect(self.reject)

        # Set actual values once signals are setup
        self.__mem.slider.setValue(self.getMaxMemory())
        self.__gpu.slider.setValue(self.getMaxGpu())
        self.__core.setValue(self.getMinCores())
        self.__max_cores.setValue(self.getMaxCores())

        QtWidgets.QVBoxLayout(self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(EnableableItem(LayerPropertiesItem("Minimum Memory:",
                                                             self.__mem,
                                                             False),
                                                             multiSelect))
        layout.addWidget(EnableableItem(LayerPropertiesItem("Memory Optimizer:",
                                                            self.__mem_opt,
                                                            True),
                                                            multiSelect))
        layout.addWidget(EnableableItem(LayerPropertiesItem("Min Threads:",
                                                            self.__core,
                                                            False),
                                                            multiSelect))
        layout.addWidget(EnableableItem(LayerPropertiesItem("Max Threads:",
                                                            self.__max_cores,
                                                            False),
                                                            multiSelect))
        layout.addWidget(EnableableItem(LayerPropertiesItem("Multi-Threadable:",
                                                            self.__thread,
                                                            True),
                                                            multiSelect))
        layout.addWidget(EnableableItem(LayerPropertiesItem("Minimum Gpu Memory:",
                                                            self.__gpu,
                                                            False),
                                                            multiSelect))
        layout.addStretch()
        self.__group.setLayout(layout)

        self.layout().addWidget(EnableableItem(self.__tags, multiSelect))
        self.layout().addWidget(self.__group)
        self.layout().addWidget(self.__buttons)

    def _cfg(self):
        '''
        Loads (if necessary) and returns the config values.
        Warns and returns an empty dict if there's a problem reading the config

        @return: The keys & values stored in the config file
        @rtype: dict<str:str>
        '''
        if not hasattr(self, '__config'):
            self.__config = Utils.getResourceConfig()
        return self.__config

    def verify(self):
        """
        Verify the contents of all widgets.
        """
        if not self.__tags.verify():
            return
        # Verify our own values.
        mem_value = self.__mem.slider.value()
        if mem_value < self.mem_min_kb or mem_value > self.mem_max_kb:
            warning("The memory setting is too high.")
            return False
        gpu_value = self.__gpu.slider.value()
        if gpu_value < self.gpu_min_kb or gpu_value > self.gpu_max_kb:
            warning("The gpu memory setting is too high.")
            return False

        self.apply()

    def apply(self):
        """
        Apply the settings to all selected layers.
        """
        for layer in self.__layers:
            if self.__mem.isEnabled():
                layer.setMinMemory(self.__mem.slider.value())
            if self.__mem_opt.isEnabled():
                layer.enableMemoryOptimizer(self.__mem_opt.isChecked())
            if self.__core.isEnabled():
                layer.setMinCores(float(self.__core.value()))
            if self.__max_cores.isEnabled():
                layer.setMaxCores(float(self.__max_cores.value()))
            if self.__thread.isEnabled():
                layer.setThreadable(self.__thread.isChecked())
            if self.__gpu.isEnabled():
                layer.setMinGpu(self.__gpu.slider.value() * self.gpu_tick_kb)

        if self.__tags.isEnabled():
            self.__tags.apply()
        self.close()

    def getMaxMemory(self):
        result = 0
        for layer in self.__layers:
            if layer.data.minMemory > result:
                result = layer.data.minMemory
        return result

    def getMaxGpu(self):
        return max([layer.data.minGpu / self.gpu_tick_kb for layer in self.__layers])

    def getMinCores(self):
        result = 0
        for layer in self.__layers:
            if layer.data.minCores > result:
                result = layer.data.minCores
        return result

    def getMaxCores(self):
        result = 0
        for layer in self.__layers:
            if layer.data.maxCores > result:
                result = layer.data.maxCores
        return result

    def getThreading(self):
        result = False
        for layer in self.__layers:
            if layer.data.isThreadable:
                result = True
                break
        return result

    def getMemoryOptSetting(self):
        result = False
        for layer in self.__layers:
            if layer.data.memoryOptimzerEnabled:
                result = True
                break
        return result

    def __translateToMemSpinbox(self, value):
        self.__mem.spinner.setValue(float(value) / 1048576.0)

    def __translateToMemSlider(self, value):
        self.__mem.slider.setValue(int(value * 1048576.0))

    def __translateToGpuSpinbox(self, value):
        self.__gpu.spinner.setValue(float(value * self.gpu_tick_kb) / 1024.0 / 1024.0)

    def __translateToGpuSlider(self, value):
        self.__gpu.slider.setValue(int(value * 1024.0 * 1024.0) / self.gpu_tick_kb)


class LayerTagsWidget(QtWidgets.QWidget):
    """
    A widget for editing tags.
    """
    def __init__(self, layers, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.__layers = layers

        currentTags = set()
        for layer in self.__layers:
            for tag in layer.data.tags:
                currentTags.add(tag)
        layout = QtWidgets.QVBoxLayout(self)
        custom_layout = QtWidgets.QHBoxLayout()
        self._tags_widget = TagsWidget(allowed_tags=Constants.ALLOWED_TAGS)
        self._tags_widget.set_tags(currentTags)
        custom_layout.addWidget(self._tags_widget)
        layout.addLayout(custom_layout)

    def apply(self):
        """
        Apply values to layers.
        """
        tags = self._tags_widget.get_tags()
        if not tags:
            return

        try:
            for layer in self.__layers:
                layer.setTags(tags)
        except opencue.CueException, e:
            warning = QtWidgets.QMessageBox(self)
            warning.setText("Error applying layer tags.")
            warning.setDetailedText("%s" % e)
            warning.exec_()

    def verify(self):
        """
        Verify values.
        """
        if not self._tags_widget.get_tags():
            warning("You must have at least 1 tag selected.")
            return False
        return True


class LayerTagsDialog(QtWidgets.QDialog):
    def __init__(self, layers, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self._tags_widget = LayerTagsWidget(layers=layers,
                                            parent=parent)
        self.__warning = QtWidgets.QLabel("Warning: Changing these tags may cause "
                                      "your job to not run any frames")
        self.__buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self)

        self.__buttons.accepted.connect(self.accept)
        self.__buttons.rejected.connect(self.reject)

    def accept(self):
        self._tags_widget.apply()
        self.close()

