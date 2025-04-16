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


"""Plugin that lists attributes of the selected object."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import map
from builtins import str
import time

from qtpy import QtCore
from qtpy import QtWidgets

import opencue_proto.depend_pb2
import opencue
import opencue.wrappers.job

import cuegui.AbstractDockWidget
import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)

PLUGIN_NAME = "Attributes"
PLUGIN_CATEGORY = "Other"
PLUGIN_DESCRIPTION = "Displays entity attributes"
PLUGIN_PROVIDES = "AttributesPlugin"


class AttributesPlugin(cuegui.AbstractDockWidget.AbstractDockWidget):
    """Plugin that lists attributes of the selected object."""

    def __init__(self, parent):
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(
            self, parent, PLUGIN_NAME, QtCore.Qt.RightDockWidgetArea)
        self.__attributes = Attributes(self)
        self.layout().addWidget(self.__attributes)


def getDependsForm(depends):
    """This is a temporary method until a new widget factory can be made
    that creates uber hawt dependency widgets."""
    if not depends:
        return None

    result = { }
    depCount = 0
    for dep in depends:
        depCount = depCount + 1
        depType = opencue_proto.depend_pb2.DependType.Name(dep.data.type)
        name = "%s-%d" % (depType, depCount)
        result[name] = {
            "__childOrder" :["active","onJob","onLayer","onFrame"],
            "active": str(dep.data.active),
            "onJob":dep.data.depend_on_job,
        }
        if dep.data.depend_on_layer:
            result[name]["onLayer"] = dep.data.depend_on_layer
        if dep.data.depend_on_frame:
            result[name]["onFrame"] = dep.data.depend_on_frame

    return result


class Attributes(QtWidgets.QWidget):
    """Attributes
        The Attributes widget contains a path or some text
        that indicates what you are looking at and a custom
        widget that is build someplace else and passed in
        via the setForm method.
    """
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.app = cuegui.app()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.__scrollArea = QtWidgets.QScrollArea()
        self.__scrollArea.setWidgetResizable(True)
        self.__scrollArea.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__scrollWidget = QtWidgets.QWidget(None)
        QtWidgets.QVBoxLayout(self.__scrollWidget)

        self.__path = QtWidgets.QLineEdit("", self.__scrollWidget)
        self.__path.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__stack = QtWidgets.QStackedWidget(self.__scrollWidget)
        self.__scrollWidget.layout().addWidget(self.__path)
        self.__scrollWidget.layout().addWidget(self.__stack)
        self.__scrollArea.setWidget(self.__scrollWidget)
        layout.addWidget(self.__scrollArea)
        self.app.single_click.connect(self.setWidget)

        self.__load = None

    # pylint: disable=inconsistent-return-statements
    def setWidget(self, item):
        """If the item is a known object, then it will be displayed.
        @type  item: any known object, otherwise ignored
        @param item: The object to display"""

        # Define the known types here
        # Also define the string that populates the path bar at the top
        if cuegui.Utils.isJob(item):
            function = JobAttributes
            path = item.data.log_dir
        elif cuegui.Utils.isLayer(item):
            function = LayerAttributes
            path = ""
        elif cuegui.Utils.isHost(item):
            function = HostAttributes
            path = ""
        else:
            return

        self.__path.setText(path)

        # If the Attributes class has a preload static function, it will be
        # called in a worker thread prior to the creation of the widget.
        # Otherwise the widget will just be created now.
        if hasattr(function, "preload"):
            if self.app.threadpool is not None:
                self.__load = {"item": item, "function": function}
                self.app.threadpool.queue(
                    self.__getUpdate, self.__processResults, "getting data for %s" % self.__class__)
            else:
                logger.warning("threadpool not found, doing work in gui thread")
                return self.__createItemAttribute(item, function, function.preload(item))
        else:
            return self.__createItemAttribute(item, function, None)

    # pylint: disable=broad-except,inconsistent-return-statements
    def __getUpdate(self):
        """Called from the worker thread, gets results from preload"""
        try:
            if self.__load:
                work = self.__load
                self.__load = None
                work["preload"] = work["function"].preload(work["item"])
                return work
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

    def __processResults(self, work, result):
        """Unpacks the worker thread results and calls function to create widget"""
        del work
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
                oldWidget.setParent(QtWidgets.QWidget())
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))


class AbstractAttributes(QtWidgets.QTreeWidget):
    """Abstract class for listing object attributes.

    Inheriting classes build on this, adding additional logic depending on the type of the
    selected object.
    """

    def __init__(self, rpcObject, preload, parent=None):
        QtWidgets.QTreeWidget.__init__(self, parent)

        def addData(parent, value):
            if isinstance(value, dict):
                if "__childOrder" in value:
                    full_keys = [k for k in list(value.keys()) if k != "__childOrder"]
                    keys = value.get("__childOrder", full_keys)
                    keys = keys + list(set(full_keys).difference(set(keys)))
                else:
                    keys = list(value.keys())

                for key in keys:
                    child = QtWidgets.QTreeWidgetItem([str(key)])
                    try:
                        addData(child, value[key])
                        parent.addChild(child)
                    except KeyError:
                        pass
            else:
                parent.setText(1, str(value))

        root = QtWidgets.QTreeWidgetItem([str(self.NAME)])
        data = self.dataSource(rpcObject, preload)
        addData(root, data)

        self.setColumnCount(2)
        self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.header().hide()
        self.addTopLevelItem(root)
        self.expandAll()

        self.itemSelectionChanged.connect(self.itemSingleClickedCopy)  # pylint: disable=no-member

    def itemSingleClickedCopy(self):
        """Event handler that copies the text of the selected line to the clipboard on click."""
        selected = self.selectedItems()

        if selected:
            QtWidgets.QApplication.clipboard().setText(str(selected[0].text(1)))


class LayerAttributes(AbstractAttributes):
    """Class for listing attributes of a layer."""

    NAME = "LayerAttributes"

    @staticmethod
    def preload(layer):
        """Prepopulates needed layer information."""
        return {"depends": layer.getWhatThisDependsOn()}

    def dataSource(self, layer, preload):
        """Returns layer information structured as needed for the attributes list."""
        d = {
                "id": opencue.util.id(layer),
                "layer": layer.data.name,
                "services": layer.data.services,
                "type": str(layer.data.type),
                "command": str(layer.data.command),
                "range": layer.data.range,
                "tags": layer.data.tags,
                "threadable": str(layer.data.is_threadable),
                "minCores": "%0.2f" % layer.data.min_cores,
                "maxCores": "%0.2f" % layer.data.max_cores,
                "memory optimizer enabled": str(layer.data.memory_optimizer_enabled),
                "minMemory": "%0.2fMB" % (layer.data.min_memory / 1024.0),
                "outputs": {},
                "frames": {
                       "total": layer.data.layer_stats.total_frames,
                       "waiting": layer.data.layer_stats.waiting_frames,
                       "dead": layer.data.layer_stats.dead_frames,
                       "eaten": layer.data.layer_stats.eaten_frames,
                       "depend": layer.data.layer_stats.depend_frames,
                       "succeeded": layer.data.layer_stats.succeeded_frames,
                       "running": layer.data.layer_stats.running_frames
                },
                "stats": {
                      "avgFrameTime":
                          cuegui.Utils.secondsToHHMMSS(layer.data.layer_stats.avg_frame_sec),
                      "Total Core Hours":
                          cuegui.Utils.secondsToHHMMSS(layer.data.layer_stats.total_core_sec),
                      "Core Hours Succeeded":
                          cuegui.Utils.secondsToHHMMSS(layer.data.layer_stats.rendered_core_sec),
                      "Core Hours Failed":
                          cuegui.Utils.secondsToHHMMSS(layer.data.layer_stats.failed_core_sec),
                      "Remaining Core Hours":
                          cuegui.Utils.secondsToHHMMSS(layer.data.layer_stats.remaining_core_sec)
                 },
                "resources": {
                          "cores": "%02.f" % layer.data.layer_stats.reserved_cores,
                          "Running frames": layer.data.layer_stats.running_frames,
                          "maxRss": int(layer.data.layer_stats.max_rss)
                },
                "__childOrder":["id","layer","services","type","command","range","tags",
                                "threadable","minCores","maxCores","memory optimizer enabled",
                                "minMemory","outputs", "depends", "frames","resources"],
                "depends": getDependsForm(preload["depends"]),
                }

        for num, output in enumerate(layer.getOutputPaths()):
            # Try to formulate a unique name the output.
            # pylint: disable=bare-except
            try:
                # Outline only puts outputs in as filespecs,
                # so we're just going to assume it is.
                rep = output.split("/")[-2]
                if rep in d["outputs"]:
                    rep = "%s #%d" % (rep, num)
            except:
                rep = "output #%d" % num
            # pylint: enable=bare-except

            d["outputs"][rep] = output

        return d


class JobAttributes(AbstractAttributes):
    """Class for listing attributes of a job."""

    NAME = "JobAttributes"

    @staticmethod
    def preload(jobObject):
        """Prepopulates needed job information."""
        return {"depends": jobObject.getWhatThisDependsOn()}

    def dataSource(self, job, preload):
        """Returns job information structured as needed for the attributes list."""
        if isinstance(job, opencue.wrappers.job.NestedJob):
            job = job.asJob()
        d = {
            "job": job.data.name,
            "id": opencue.util.id(job),
            "facility": job.data.facility,
            "os": job.data.os,
            "show": job.data.show,
            "shot": job.data.shot,
            "user": job.data.user,
            "state": str(job.data.state),
            "startTime": cuegui.Utils.dateToMMDDHHMM(job.data.start_time),
            "stopTime": cuegui.Utils.dateToMMDDHHMM(job.data.stop_time),
            "priority": {
                         "group": job.data.group,
                         "level": job.data.priority,
                         "minCores": "%.02f" % job.data.min_cores,
                         "maxCores": "%.02f" % job.data.max_cores,
                         },
            "outputs": { },
            "frames": {
                       "total": job.data.job_stats.total_frames,
                       "waiting": job.data.job_stats.waiting_frames,
                       "dead": job.data.job_stats.dead_frames,
                       "eaten": job.data.job_stats.eaten_frames,
                       "depend": job.data.job_stats.depend_frames,
                       "succeeded": job.data.job_stats.succeeded_frames,
                       "running": job.data.job_stats.running_frames
                       },
            "stats": {
                  "avgFrameTime":
                      cuegui.Utils.secondsToHHMMSS(job.data.job_stats.avg_frame_sec),
                  "totalCoreSeconds":
                      cuegui.Utils.secondsToHHMMSS(job.data.job_stats.total_core_sec),
                  "renderedCoreSeconds":
                      cuegui.Utils.secondsToHHMMSS(job.data.job_stats.rendered_core_sec),
                  "failedCoreSeconds":
                      cuegui.Utils.secondsToHHMMSS(job.data.job_stats.failed_core_sec),
                  "remainingCoreSeconds":
                      cuegui.Utils.secondsToHHMMSS(job.data.job_stats.remaining_core_sec)
             },
            "resources": {
                          "cores": "%02.f" % job.data.job_stats.reserved_cores,
                          "maxRss": int(job.data.job_stats.max_rss)
                          },
            "__childOrder":["job","id","facility","os","show","shot","user",
                            "state", "startTime", "stopTime","outputs","depends",
                            "frames","resources"],
            "depends": getDependsForm(preload["depends"])}

        ## In the layer outputs.
        if job.data.job_stats.total_layers < 20:
            for layer in job.getLayers():
                outputs = layer.getOutputPaths()
                if not outputs:
                    continue
                entry = {}
                d["outputs"][layer.data.name] = entry

                for num, output in enumerate(outputs):
                    # Try to formulate a unique name the output.
                    # pylint: disable=bare-except
                    try:
                        # Outline only puts outputs in as filespecs,
                        # so we're just going to assume it is.
                        rep = output.split("/")[-2]
                        if rep in entry:
                            rep = "%s #%d" % (rep, num)
                    except:
                        rep = "output #%d" % num
                    # pylint: enable=bare-except

                    entry[rep] = output
        return d


class HostAttributes(AbstractAttributes):
    """Class for listing attributes of a host."""

    NAME = "Host"

    def dataSource(self, host, preload):
        """Returns host information structured as needed for the attributes list."""
        del preload
        return {"hostname": host.data.name,
                "id": opencue.util.id(host),
                "alloc": host.data.alloc_name,
                "os": host.data.os,
                "nimby": str(host.data.nimby_enabled),
                "state": str(host.data.state),
                "lock": str(host.data.lock_state),
                "load": "%.2f" % (host.data.load/float(100)),
                "bootTime": cuegui.Utils.dateToMMDDYYYYHHMM(host.data.boot_time),
                "pingTime": cuegui.Utils.dateToMMDDHHMM(host.data.ping_time),
                "pingLast": int(time.time() - host.data.ping_time),
                "tags": ",".join(host.data.tags),
                "cores": {
                          "Core Units Total": str(host.data.cores),
                          "Core Units Reserved": str(host.data.cores - host.data.idle_cores),
                          "Core Units Idle": str(host.data.idle_cores),
                         },
                "memory": {
                           "Pool Total": str(host.data.memory),
                           "Pool Reserved": str(host.data.memory - host.data.idle_memory),
                           "Pool Idle": str(host.data.idle_memory),
                           "Pool Usage": float((host.data.memory - host.data.idle_memory) /
                                               float(host.data.memory) * 100.0),
                           "Real Usage": float((host.data.total_memory - host.data.free_memory) /
                                               float(host.data.total_memory) * 100.0),
                           "Real Total": str(host.data.total_memory),
                           "Real Used": str(host.data.total_memory - host.data.free_memory),
                           "Real Free": str(host.data.free_memory),
                           "__childOrder": ["Pool Total","Pool Reserved","Pool Idle",
                                            "Real Total","Real Used","Real Free",
                                            "Pool Usage", "Real Usage"],
                        },
                "swap": {
                         "Swap Total": str(host.data.total_swap),
                         "Swap Used": str(host.data.total_swap - host.data.free_swap),
                         "Swap Free": str(host.data.free_swap),
                         "__childOrder": ["Swap Total KB","Swap Used KB","Swap Free KB"]
                        },
                "mcp": {
                        "MCP Total" : str(host.data.total_mcp),
                        "MCP Used":  str(host.data.total_mcp - host.data.free_mcp),
                        "MCP Free": str(host.data.free_mcp),
                        "__childOrder": ["MCP Total","MCP Used","MCP Free"]
                       },
                "raw": {
                        "icePacket": str(host),
                },
                "__childOrder":["id","hostname","os","alloc","tags","nimby","state",
                                "lock","load","bootTime","pingTime","pingLast","cores",
                                "memory","swap","mcp","raw"],
            }
