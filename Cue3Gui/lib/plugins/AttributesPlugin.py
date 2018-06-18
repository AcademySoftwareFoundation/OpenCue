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
import os

import Cue3Gui
import Cue3

logger = Cue3Gui.Logger.getLogger(__file__)

from PyQt4 import QtGui, QtCore

PLUGIN_NAME = "Attributes"
PLUGIN_CATEGORY = "Other"
PLUGIN_DESCRIPTION = "Displays entity attributes"
PLUGIN_PROVIDES = "AttributesPlugin"

class AttributesPlugin(Cue3Gui.AbstractDockWidget):
    def __init__(self, parent):
        Cue3Gui.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME, QtCore.Qt.RightDockWidgetArea)
        self.__attributes = Attributes(self)
        self.layout().addWidget(self.__attributes)

def getDependsForm(depends):
    """This is a temporary method unil a new widget factory can be made
    that creates uber hawt dependency widgets"""
    if not depends:
        return None

    result = { }
    depCount = 0
    for dep in depends:
        depCount = depCount + 1
        name = "%s-%d" % (dep.data.type, depCount)
        result[name] = {
            "__childOrder" :["active","onJob","onLayer","onFrame"],
            "active": str(dep.data.active),
            "onJob":dep.data.dependOnJob,
        }
        if dep.data.dependOnLayer:
            result[name]["onLayer"] = dep.data.dependOnLayer
        if dep.data.dependOnFrame:
            result[name]["onFrame"] = dep.data.dependOnFrame

    return result

class Attributes(QtGui.QWidget):
    """Attributes
        The Attributes widget contains a path or some text
        that indicates what you are looking at and a custom
        widget that is build someplace else and passed in
        via the setForm method.
    """
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.__scrollArea = QtGui.QScrollArea()
        self.__scrollArea.setWidgetResizable(True)
        self.__scrollArea.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__scrollWidget = QtGui.QWidget(None)
        QtGui.QVBoxLayout(self.__scrollWidget)

        self.__path = QtGui.QLineEdit("", self.__scrollWidget)
        self.__path.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__stack = QtGui.QStackedWidget(self.__scrollWidget)
        self.__scrollWidget.layout().addWidget(self.__path)
        self.__scrollWidget.layout().addWidget(self.__stack)
        self.__scrollArea.setWidget(self.__scrollWidget)
        layout.addWidget(self.__scrollArea)

        QtCore.QObject.connect(QtGui.qApp, QtCore.SIGNAL("single_click(PyQt_PyObject)"), self.setWidget);

        self.__load = None

    def setWidget(self, item):
        """If the item is a known object, then it will be displayed.
        @type  item: any known object, otherwise ignored
        @param item: The object to display"""

        # Define the known types here
        # Also define the string that populates the path bar at the top
        if Cue3Gui.Utils.isJob(item):
            function = JobAttributes
            path = item.data.logDir
        elif Cue3Gui.Utils.isLayer(item):
            function = LayerAttributes
            path = ""
        elif Cue3Gui.Utils.isHost(item):
            function = HostAttributes
            path = ""
        else:
            return

        self.__path.setText(path)

        # If the Attributes class has a preload static function, it will be
        # called in a worker thread prior to the creation of the widget.
        # Otherwise the widget will just be created now.
        if hasattr(function, "preload"):
            if hasattr(QtGui.qApp, "threadpool"):
                self.__load = {"item": item, "function": function}
                QtGui.qApp.threadpool.queue(self.__getUpdate,
                                            self.__processResults,
                                            "getting data for %s" % self.__class__)
            else:
                logger.warning("threadpool not found, doing work in gui thread")
                return self.__createItemAttribute(item, function, function.preload(item))
        else:
            return self.__createItemAttribute(item, function, None)

    def __getUpdate(self):
        """Called from the worker thread, gets results from preload"""
        try:
            if self.__load:
                work = self.__load
                self.__load = None
                work["preload"] = work["function"].preload(work["item"])
                return work
        except Exception, e:
            map(logger.warning, Cue3Gui.Utils.exceptionOutput(e))

    def __processResults(self, work, result):
        """Unpacks the worker thread results and calls function to create widget"""
        if result:
            self.__createItemAttribute(result["item"],
                                       result["function"],
                                       result["preload"])

    def __createItemAttribute(self, item, function, preload):
        """Create the new widget, add it, and remove the old one"""
        try:
            self.__stack.addWidget(function(item, preload))

            # Remove the widget
            if self.__stack.count() > 1:
                oldWidget = self.__stack.widget(0)
                self.__stack.removeWidget(oldWidget)
                oldWidget.setParent(QtGui.QWidget())
        except Exception, e:
            map(logger.warning, Cue3Gui.Utils.exceptionOutput(e))


class AbstractAttributes(QtGui.QTreeWidget):
    def __init__(self, iceObject, preload, parent=None):
        QtGui.QWidget.__init__(self, parent)

        def addData(parent, value):
            if isinstance(value, dict):
                if "__childOrder" in value:
                    full_keys = [k for k in value.keys() if k != "__childOrder"]
                    keys = value.get("__childOrder", full_keys)
                    keys = keys + list(set(full_keys).difference(set(keys)))
                else:
                    keys = value.keys()

                for key in keys:
                    child = QtGui.QTreeWidgetItem([str(key)])
                    try:
                        addData(child, value[key])
                        parent.addChild(child)
                    except KeyError:
                        pass
            else:
                parent.setText(1, str(value))

        root = QtGui.QTreeWidgetItem([str(self.NAME)])
        data = self.dataSource(iceObject, preload)
        addData(root, data)

        self.setColumnCount(2)
        self.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.header().hide()
        self.addTopLevelItem(root)
        self.expandAll()


class LayerAttributes(AbstractAttributes):
    NAME = "LayerAttributes"

    @staticmethod
    def preload(iceObject):
        return {"depends": iceObject.proxy.getWhatThisDependsOn()}

    def dataSource(self, layer, preload):
        d = {
                "id": Cue3.id(layer.proxy),
                "layer": layer.data.name,
                "services": layer.data.services,
                "type": str(layer.data.type),
                "range": layer.data.range,
                "tags": layer.data.tags,
                "threadable": str(layer.data.isThreadable),
                "minCores": "%0.2f" % layer.data.minCores,
                "minMemory": "%0.2fMB" % (layer.data.minMemory / 1024.0),
                "outputs": {},
                "frames": {
                       "total": layer.stats.totalFrames,
                       "waiting": layer.stats.waitingFrames,
                       "dead": layer.stats.deadFrames,
                       "eaten": layer.stats.eatenFrames,
                       "depend": layer.stats.dependFrames,
                       "succeeded": layer.stats.succeededFrames,
                       "running": layer.stats.runningFrames
                },
                "stats": {
                      "avgFrameTime":
                          Cue3Gui.Utils.secondsToHHMMSS(layer.stats.avgFrameSec),
                      "Total Core Hours":
                          Cue3Gui.Utils.secondsToHHMMSS(layer.stats.totalCoreSec),
                      "Core Hours Succeeded":
                          Cue3Gui.Utils.secondsToHHMMSS(layer.stats.renderedCoreSec),
                      "Core Hours Failed":
                          Cue3Gui.Utils.secondsToHHMMSS(layer.stats.failedCoreSec),
                      "Remaining Core Hours":
                          Cue3Gui.Utils.secondsToHHMMSS(layer.stats.remainingCoreSec)
                 },
                "resources": {
                          "cores": "%02.f" % layer.stats.reservedCores,
                          "Running frames": layer.stats.runningFrames,
                          "maxRss": int(layer.stats.maxRss)
                },
                "__childOrder":["id","layer","services","type","range","tags",
                                "threadable","minCores","minMemory","outputs",
                                "depends", "frames","resources"],
                "depends": getDependsForm(preload["depends"]),
                }


        for num, output in enumerate(layer.proxy.getOutputPaths()):
            # Try to formulate a unique name the output.
            try:
                # Outline only puts outputs in as filespecs,
                # so we're just going to assume it is.
                rep = output.split("/")[-2]
                if d["outputs"].has_key(rep):
                    rep = "%s #%d" % (rep, num)
            except:
                rep = "output #%d" % num

            d["outputs"][rep] = output

        return d

class JobAttributes(AbstractAttributes):
    NAME = "JobAttributes"

    @staticmethod
    def preload(iceObject):
        return {"depends": iceObject.proxy.getWhatThisDependsOn()}

    def dataSource(self, job, preload):
        d = {
            "job": job.data.name,
            "id": Cue3.id(job),
            "facility": job.data.facility,
            "os": job.data.os,
            "show": job.data.show,
            "shot": job.data.shot,
            "user": job.data.user,
            "state": str(job.data.state),
            "startTime": Cue3Gui.Utils.dateToMMDDHHMM(job.data.startTime),
            "stopTime": Cue3Gui.Utils.dateToMMDDHHMM(job.data.stopTime),
            "priority": {
                         "group": job.data.group,
                         "level": job.data.priority,
                         "minCores": "%.02f" % job.data.minCores,
                         "maxCores": "%.02f" % job.data.maxCores,
                         },
            "outputs": { },
            "frames": {
                       "total": job.stats.totalFrames,
                       "waiting": job.stats.waitingFrames,
                       "dead": job.stats.deadFrames,
                       "eaten": job.stats.eatenFrames,
                       "depend": job.stats.dependFrames,
                       "succeeded": job.stats.succeededFrames,
                       "running": job.stats.runningFrames
                       },
            "stats": {
                  "avgFrameTime":
                      Cue3Gui.Utils.secondsToHHMMSS(job.stats.avgFrameSec),
                  "totalCoreSeconds":
                      Cue3Gui.Utils.secondsToHHMMSS(job.stats.totalCoreSec),
                  "renderedCoreSeconds":
                      Cue3Gui.Utils.secondsToHHMMSS(job.stats.renderedCoreSec),
                  "failedCoreSeconds":
                      Cue3Gui.Utils.secondsToHHMMSS(job.stats.failedCoreSec),
                  "remainingCoreSeconds":
                      Cue3Gui.Utils.secondsToHHMMSS(job.stats.remainingCoreSec)
             },
            "resources": {
                          "cores": "%02.f" % job.stats.reservedCores,
                          "maxRss": int(job.stats.maxRss)
                          },
            "__childOrder":["job","id","facility","os","show","shot","user",
                            "state", "startTime", "stopTime","outputs","depends",
                            "frames","resources"],
            "depends": getDependsForm(preload["depends"])}

        ## In in the layer outputs.
        if job.stats.totalLayers < 20:
            for layer in job.proxy.getLayers():
                outputs = layer.proxy.getOutputPaths()
                if not outputs:
                    continue
                entry = {}
                d["outputs"][layer.data.name] = entry

                for num, output in enumerate(outputs):
                    # Try to formulate a unique name the output.
                    try:
                        # Outline only puts outputs in as filespecs,
                        # so we're just going to assume it is.
                        rep = output.split("/")[-2]
                        if entry.has_key(rep):
                            rep = "%s #%d" % (rep, num)
                    except:
                        rep = "output #%d" % num

                    entry[rep] = output
        return d

class HostAttributes(AbstractAttributes):
    NAME = "Host"

    def dataSource(self, host, preload):
        return {"hostname": host.data.name,
                "id": Cue3.id(host),
                "alloc": host.data.allocName,
                "os": host.data.os,
                "nimby": str(host.data.nimbyEnabled),
                "state": str(host.data.state),
                "lock": str(host.data.lockState),
                "load": "%.2f" % (host.data.load/float(100)),
                "bootTime": Cue3Gui.Utils.dateToMMDDHHMM(host.data.bootTime),
                "pingTime": Cue3Gui.Utils.dateToMMDDHHMM(host.data.pingTime),
                "pingLast": int(time.time() - host.data.pingTime),
                "tags": ",".join(host.data.tags),
                "cores": {
                          "Core Units Total": str(host.data.cores),
                          "Core Units Reserved": str(host.data.cores - host.data.idleCores),
                          "Core Units Idle": str(host.data.idleCores),
                         },
                "memory": {
                           "Pool Total": str(host.data.memory),
                           "Pool Reserved": str(host.data.memory - host.data.idleMemory),
                           "Pool Idle": str(host.data.idleMemory),
                           "Pool Usage": float((host.data.memory - host.data.idleMemory) / float(host.data.memory) * 100.0),
                           "Real Usage": float((host.data.totalMemory - host.data.freeMemory) / float(host.data.totalMemory) * 100.0),
                           "Real Total": str(host.data.totalMemory),
                           "Real Used": str(host.data.totalMemory - host.data.freeMemory),
                           "Real Free": str(host.data.freeMemory),
                           "__childOrder": ["Pool Total","Pool Reserved","Pool Idle",
                                            "Real Total","Real Used","Real Free",
                                            "Pool Usage", "Real Usage"],
                        },
                "swap": {
                         "Swap Total": str(host.data.totalSwap),
                         "Swap Used": str(host.data.totalSwap - host.data.freeSwap),
                         "Swap Free": str(host.data.freeSwap),
                         "__childOrder": ["Swap Total KB","Swap Used KB","Swap Free KB"]
                        },
                "mcp": {
                        "MCP Total" : str(host.data.totalMcp),
                        "MCP Used":  str(host.data.totalMcp - host.data.freeMcp),
                        "MCP Free": str(host.data.freeMcp),
                        "__childOrder": ["MCP Total","MCP Used","MCP Free"]
                       },
                "raw": {
                        "icePacket": str(host),
                },
                "__childOrder":["id","hostname","os","alloc","tags","nimby","state",
                                "lock","load","bootTime","pingTime","pingLast","cores",
                                "memory","swap","mcp","raw"],
            }
