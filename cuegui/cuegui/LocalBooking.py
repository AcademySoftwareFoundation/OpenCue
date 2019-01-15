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


import time
from socket import gethostname

import Utils
from Manifest import QtCore, QtWidgets, opencue, os


class LocalBookingWidget(QtWidgets.QWidget):
    """
    A widget for creating opencue RenderParitions, otherwise know
    as local core booking.
    """

    hosts_changed = QtCore.Signal()

    def __init__(self, target, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        # Can either be a opencue job, layer, or frame.
        self.__target = target
        self.__parent = parent

        self.jobName = self.getTargetJobName()

        QtWidgets.QVBoxLayout(self)

        layout = QtWidgets.QGridLayout()

        self.__select_host = QtWidgets.QComboBox(self)
        self.__lba_group = QtWidgets.QGroupBox("Settings", self)

        try:
            owner = opencue.api.getOwner(os.environ["USER"])
            for host in owner.getHosts():
                if host.data.lockState != opencue.api.host_pb2.OPEN:
                    self.__select_host.addItem(host.data.name)
        except Exception, e:
            pass

        self.__deed_button = None
        self.__msg_widget = None
        if self.__select_host.count() == 0:
            self.__deed_button = QtWidgets.QPushButton("Deed This Machine", self)
            msg = "You have not deeded any hosts or they are not NIMBY locked."
            self.__msg_widget = QtWidgets.QLabel(msg, self)
            self.layout().addWidget(self.__msg_widget)
            self.layout().addWidget(self.__deed_button)
            self.__deed_button.pressed.connect(self.deedLocalhost)
            self.__lba_group.setDisabled(True)

        self.__text_target = QtWidgets.QLabel(self.__target.data.name, self)

        self.__num_threads = QtWidgets.QSpinBox(self)
        self.__num_threads.setValue(1);

        self.__num_cores = QtWidgets.QLineEdit(self)
        self.__num_cores.setText("1");
        self.__num_cores.setReadOnly(True)

        self.__num_frames = QtWidgets.QSpinBox(self)
        self.__num_frames.setValue(1)

        self.__frame_warn = QtWidgets.QLabel(self)

        self.__num_mem = QtWidgets.QSlider(self)
        self.__num_mem.setValue(4);
        self.__num_mem.setOrientation(QtCore.Qt.Horizontal)
        self.__num_mem.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.__num_mem.setTickInterval(1)

        self.__text_num_mem = QtWidgets.QSpinBox(self)
        self.__text_num_mem.setValue(4)
        self.__text_num_mem.setSuffix("GB")

        #
        # Next layout is if the deed is in use.
        #
        layout2 = QtWidgets.QGridLayout()

        self.__run_group = QtWidgets.QGroupBox("Deed Currently in Use", self)

        self.__run_cores = QtWidgets.QSpinBox(self)

        self.__run_mem = QtWidgets.QSlider(self)
        self.__run_mem.setValue(4)
        self.__run_mem.setOrientation(QtCore.Qt.Horizontal)
        self.__run_mem.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.__run_mem.setTickInterval(1)

        self.__text_run_mem = QtWidgets.QSpinBox(self)
        self.__text_run_mem.setValue(4)
        self.__text_run_mem.setSuffix("GB")

        self.__btn_clear = QtWidgets.QPushButton("Clear", self)


        #
        # Setup the signals.
        #
        self.__btn_clear.pressed.connect(self.clearCurrentHost)
        self.__select_host.activated.connect(self.__host_changed)
        self.__num_mem.valueChanged.connect(self.__text_num_mem.setValue)
        self.__text_num_mem.valueChanged.connect(self.__num_mem.setValue)
        self.__num_threads.valueChanged.connect(self.__calculateCores)
        self.__num_frames.valueChanged.connect(self.__calculateCores)
        self.__run_mem.valueChanged.connect(self.__text_run_mem.setValue)
        self.__text_run_mem.valueChanged.connect(self.__run_mem.setValue)

        self.layout().addWidget(QtWidgets.QLabel("Target Host:"))
        self.layout().addWidget(self.__select_host)

        layout.addWidget(QtWidgets.QLabel("Target:"), 1, 0)
        layout.addWidget(self.__text_target, 1, 1, 1, 3)

        layout.addWidget(QtWidgets.QLabel("Parallel Frames:"), 2, 0)
        layout.addWidget(self.__num_frames, 2, 1)

        layout.addWidget(QtWidgets.QLabel("Threads: "), 2, 2)
        layout.addWidget(self.__num_threads, 2, 3)

        layout.addWidget(QtWidgets.QLabel("Cores: "), 3, 0)
        layout.addWidget(self.__num_cores, 3, 1)
        layout.addWidget(self.__frame_warn, 3, 2, 1, 2)

        layout.addWidget(QtWidgets.QLabel("Memory (GB): "), 4, 0)

        layout.addWidget(self.__num_mem, 4, 1, 1, 2)
        layout.addWidget(self.__text_num_mem, 4, 3)

        #
        # Layout 2
        #
        layout2.addWidget(QtWidgets.QLabel("Running Cores:"), 1, 0)
        layout2.addWidget(self.__run_cores, 1, 1)

        layout2.addWidget(QtWidgets.QLabel("Memory (GB): "), 3, 0)
        layout2.addWidget(self.__run_mem, 3, 1, 1, 2)
        layout2.addWidget(self.__text_run_mem, 3, 3)

        layout2.addWidget(self.__btn_clear, 4, 0)

        #
        # Set up overall layouts
        #
        self.__run_group.setLayout(layout2)
        self.__lba_group.setLayout(layout)

        self.__stack = QtWidgets.QStackedLayout()
        self.__stack.addWidget(self.__lba_group)
        self.__stack.addWidget(self.__run_group)

        self.layout().addLayout(self.__stack)

        ## Set initial values.
        self.__host_changed(self.__select_host.currentText())
        self.resize(400, 400)

    def getTargetJobName(self):
        if Utils.isJob(self.__target):
            return self.__target.data.name
        elif Utils.isLayer(self.__target):
            return self.__target.name
        elif Utils.isFrame(self.__target):
            return self.__parent.getJob().data.name
        else:
            return ''

    def hostAvailable(self):
        return self.__select_host.count() > 0

    def __host_changed(self, hostname):
        hostname = str(hostname)
        if not hostname:
            return
        host = opencue.api.findHost(str(hostname))
        try:
            rp = [r for r in host.getRenderPartitions() if r.job == self.jobName]
            
            if rp:
                rp = rp[0]
                self.__stack.setCurrentIndex(1)
                self.__btn_clear.setText("Clear")
                self.__btn_clear.setDisabled(False)
                self.__run_cores.setRange(1, int(host.data.idleCores) + rp.maxCores / 100)
                self.__run_cores.setValue(rp.maxCores / 100)
                self.__run_mem.setRange(1, int(host.data.totalMemory / 1024 / 1024))
                self.__run_mem.setValue(int(rp.maxMemory / 1024 / 1024))

            else:
                self.__stack.setCurrentIndex(0)
                self.__num_frames.setRange(1, host.data.idleCores)
                self.__num_threads.setRange(1, host.data.idleCores)
                self.__num_mem.setRange(1, int(host.data.totalMemory / 1024 / 1024))
                self.__num_threads.setRange(1, host.data.idleCores)
        except Exception, e:
            print "Failed to get RenderParition information, %s" % e

    def deedLocalhost(self):

        show_name = os.environ.get("SHOW", "pipe")
        try:
            _show = opencue.api.findShow(show_name)
        except Exception, e:
            msg = QtWidgets.QMessageBox(self)
            msg.setText("Error %s, please setshot and rerun cuetopia", e)
            msg.exec_()
            return

        user = os.environ["USER"]
        try:
            owner = opencue.api.getOwner(user)
        except opencue.EntityNotFoundException, e:
            # Owner does not exist
            owner = _show.createOwner(user)
 
        hostname = gethostname()
        try:
            host = opencue.api.findHost(hostname.rsplit(".",2)[0])
            owner.takeOwnership(host.data.name)
            self.__select_host.addItem(host.data.name)
            self.__lba_group.setDisabled(False)

            if self.__deed_button:
                self.__deed_button.setVisible(False)
            if self.__msg_widget:
                self.__msg_widget.setVisible(False)
            self.__deed_button = None
            self.__msg_widget = None
            self.hosts_changed.emit()

        except Exception, e:
            msg = QtWidgets.QMessageBox(self)
            msg.setText("Unable to determine your machine's hostname. " +
                        "It is not setup properly for local booking")

            msg.exec_()

    def __calculateCores(self, ignore):
        frames = self.__num_frames.value()
        threads = self.__num_threads.value()

        self.__num_cores.setText(str(frames * threads))

        if self.__hasError():
            self.__frame_warn.setText("Invalid thread ratio")
        else:
            self.__frame_warn.setText("")

    def __hasError(self):
        cores = int(self.__num_cores.text())
        frames = self.__num_frames.value()
        threads = self.__num_threads.value()

        if frames * threads > self.__num_frames.maximum():
            return True
        elif frames == 0:
            return True
        elif cores % threads > 0:
            return True
        elif threads > cores:
            return True

        return False

    def clearCurrentHost(self):
        hostname = str(self.__select_host.currentText())
        if not hostname:
            return
        try:
            self.__btn_clear.setText("Clearing....")
            self.__btn_clear.setDisabled(True)
            host = opencue.api.findHost(str(hostname))

            rp = [r for r in host.getRenderPartitions() if r.job == self.jobName]
            if rp:
                rp = rp[0]
        
                rp.delete()

                ## Wait for hosts to clear out, then switch
                ## back to the booking widget
                for i in range(0, 10):
                    try:
                        rp = [r for r in host.getRenderPartitions() if r.job == self.jobName][0]
                        time.sleep(1)
                    except:
                        break
            self.__host_changed(hostname)

        except Exception,e:
            print "Error clearing host: %s" % e

    def bookCurrentHost(self):
        if self.__hasError():
            return

        host = opencue.api.findHost(str(self.__select_host.currentText()))
        rp = [r for r in host.getRenderPartitions() if r.job == self.jobName]
        if rp:
            # A render partition already exists on this hosts and user is modifying
            rp[0].setMaxResources(int(self.__run_cores.value() * 100),
                                        int(self.__run_mem.value()) * 1024 * 1024,
                                        0)
        else:
            self.__target.addRenderPartition(str(self.__select_host.currentText()),
                                                   int(self.__num_threads.value()),
                                                   int(self.__num_cores.text()),
                                                   int(self.__num_mem.value() * 1048576),
                                                   0)


class LocalBookingDialog(QtWidgets.QDialog):
    """
    A dialog to wrap a LocalBookingWidget.  Provides action buttons.
    """
    def __init__(self, target, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        QtWidgets.QVBoxLayout(self)
        btn_layout = QtWidgets.QHBoxLayout()

        self.setWindowTitle("Assign Local Cores")
        self.__booking = LocalBookingWidget(target, parent)

        self.__btn_ok = QtWidgets.QPushButton("Ok")
        self.__btn_cancel = QtWidgets.QPushButton("Cancel")

        self.__updateOkButtion()

        btn_layout.addStretch()
        btn_layout.addWidget(self.__btn_ok)
        btn_layout.addWidget(self.__btn_cancel)

        self.layout().addWidget(self.__booking)
        self.layout().addLayout(btn_layout)

        self.__booking.hosts_changed.connect(self.__updateOkButtion)
        self.__btn_ok.pressed.connect(self.doLocalBooking)
        self.__btn_cancel.pressed.connect(self.close)

    def __updateOkButtion(self):
        self.__btn_ok.setDisabled(not self.__booking.hostAvailable())

    def doLocalBooking(self):
        try:
            self.__booking.bookCurrentHost()
            self.close()
        except Exception, e:
            msg = QtWidgets.QMessageBox(self)
            msg.setText("Failed to book local cores.  \
There were no pending frames that met your criteria.  Be sure to double check \
if your allocating enough memory and that your job has waiting frames.")
            msg.setDetailedText(str(e))
            msg.exec_()

