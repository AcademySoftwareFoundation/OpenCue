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



import sys
from Manifest import QtCore, QtGui, Cue3
import Constants
from TagsWidget import TagsWidget
from AbstractDialog import CheckBoxSelectionMatrix
import Utils


def warning(msg, parent=None):
    """
    Utility method for poping up a warning.
    """
    box = QtGui.QMessageBox(parent)
    box.setText(msg)
    box.exec_()


class EnableableItem(QtGui.QWidget):
    def __init__(self, widget, enable, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.__widget = widget
        self.__checkbox = QtGui.QCheckBox()

        layout = QtGui.QHBoxLayout(self)
        layout.setSpacing(0)
        if enable:
            self.__widget.setDisabled(True)
            layout.addWidget(self.__checkbox)
            QtCore.QObject.connect(self.__checkbox,
                                   QtCore.SIGNAL("toggled(bool)"),
                                   self.enable)
        layout.addWidget(self.__widget)

    def getWidget(self):
        return self.__widget

    def isEnabled(self):
        return self.__checkbox.isChecked()

    def enable(self, b):
        self.__checkbox.setChecked(b)
        self.__widget.setDisabled(b == False)


class LayerPropertiesItem(QtGui.QWidget):
    """
    An key/value widget for populating a dialog box.
    """
    def __init__(self, label, widget, stretch=True, help=None, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.__label = label
        self.__widget = widget

        layout = QtGui.QHBoxLayout(self)
        if label:
            layout.addWidget(QtGui.QLabel(label, self))
        if stretch:
            layout.addStretch()
        layout.addWidget(self.__widget)
        if help:
            layout.addWidget(help)


class SlideSpinner(QtGui.QWidget):
    """
    A QSlider and QSpinBox
    """
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.slider = QtGui.QSlider(self)
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.slider.setTickPosition(QtGui.QSlider.TicksBelow)

        self.spinner = QtGui.QDoubleSpinBox(self)

        layout = QtGui.QHBoxLayout(self)
        layout.addWidget(self.slider)
        layout.addWidget(self.spinner)


class LayerPropertiesDialog(QtGui.QDialog):
    """
    A dialog box for editing a layer.
    """
    def __init__(self, layers, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.__layers = [Cue3.getLayer(Cue3.id(l)) for l in layers]

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

        self.__group = QtGui.QGroupBox("Resource Options", self)

        ## Memory
        self.__mem = SlideSpinner(self)
        self.__mem.slider.setMinimumWidth(200)
        self.__mem.slider.setRange(self.mem_min_kb, self.mem_max_kb)
        self.__mem.slider.setTickInterval(self.mem_min_kb)
        self.__mem.slider.setSingleStep(self.mem_min_kb)
        self.__mem.spinner.setSuffix(" GB")
        self.__mem.spinner.setRange(self.mem_min_gb, self.mem_max_gb)

        ## Cores
        self.__core = QtGui.QDoubleSpinBox(self)
        self.__core.setDecimals(1)
        self.__core.setRange(0, int(self._cfg().get('max_cores', 16)))
        self.__core.setSingleStep(1)

        ## Max cores
        self.__max_cores = QtGui.QSpinBox(self)
        self.__max_cores.setRange(0, int(self._cfg().get('max_cores', 16)))
        self.__max_cores.setSingleStep(1)

        ## Disable this for everything except commander.
        if QtGui.qApp.applicationName() != "CueCommander3":
            self.__core.setDisabled(True)

        # Threads
        self.__thread = QtGui.QCheckBox(self)
        self.__thread.setChecked(self.getThreading())

        # Memory Optimizer
        self.__mem_opt = QtGui.QCheckBox()
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
        self.__buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Save |
                                                QtGui.QDialogButtonBox.Cancel,
                                                QtCore.Qt.Horizontal,
                                                self)

        # Setup signals
        QtCore.QObject.connect(self.__mem.slider,
                               QtCore.SIGNAL("valueChanged(int)"),
                               self.__translateToMemSpinbox)

        QtCore.QObject.connect(self.__mem.spinner,
                               QtCore.SIGNAL("valueChanged(double)"),
                               self.__translateToMemSlider)

        QtCore.QObject.connect(self.__gpu.slider,
                               QtCore.SIGNAL("valueChanged(int)"),
                               self.__translateToGpuSpinbox)

        QtCore.QObject.connect(self.__gpu.spinner,
                               QtCore.SIGNAL("valueChanged(double)"),
                               self.__translateToGpuSlider)

        QtCore.QObject.connect(self.__buttons, QtCore.SIGNAL("accepted()"),
                               self.verify)

        QtCore.QObject.connect(self.__buttons, QtCore.SIGNAL("rejected()"),
                               self, QtCore.SLOT("reject()"))

        # Set actual values once signals are setup
        self.__mem.slider.setValue(self.getMaxMemory())
        self.__gpu.slider.setValue(self.getMaxGpu())
        self.__core.setValue(self.getMinCores())
        self.__max_cores.setValue(self.getMaxCores())

        QtGui.QVBoxLayout(self)

        layout = QtGui.QVBoxLayout()
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
                layer.proxy.setMinMemory(self.__mem.slider.value())
            if self.__mem_opt.isEnabled():
                layer.proxy.enableMemoryOptimizer(self.__mem_opt.isChecked())
            if self.__core.isEnabled():
                layer.proxy.setMinCores(float(self.__core.value()))
            if self.__max_cores.isEnabled():
                layer.proxy.setMaxCores(float(self.__max_cores.value()))
            if self.__thread.isEnabled():
                layer.proxy.setThreadable(self.__thread.isChecked())
            if self.__gpu.isEnabled():
                layer.proxy.setMinGpu(self.__gpu.slider.value() * self.gpu_tick_kb)

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


class LayerTagsWidget(QtGui.QWidget):
    """
    A widget for editing tags.
    """
    def __init__(self, layers, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.__layers = layers

        currentTags = set()
        for layer in self.__layers:
            for tag in layer.data.tags:
                currentTags.add(tag)
        layout = QtGui.QVBoxLayout(self)
        custom_layout = QtGui.QHBoxLayout()
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
                layer.proxy.setTags(tags)
        except Cue3.CueIceException, e:
            warning = QtGui.QMessageBox(self)
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


class LayerTagsDialog(QtGui.QDialog):
    def __init__(self, layers, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self._tags_widget = LayerTagsWidget(layers=layers,
                                            parent=parent)
        self.__warning = QtGui.QLabel("Warning: Changing these tags may cause "
                                      "your job to not run any frames")
        self.__buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Save | QtGui.QDialogButtonBox.Cancel,
                                                QtCore.Qt.Horizontal,
                                                self)

        QtCore.QObject.connect(self.__buttons, QtCore.SIGNAL("accepted()"),
                               self, QtCore.SLOT("accept()"))
        QtCore.QObject.connect(self.__buttons, QtCore.SIGNAL("rejected()"),
                               self, QtCore.SLOT("reject()"))

    def accept(self):
        self._tags_widget.apply()
        self.close()

