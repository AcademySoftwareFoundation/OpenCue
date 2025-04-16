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


"""Utility functions."""


from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from builtins import str
from builtins import map
import getpass
import os
import platform
import re
import subprocess
import sys
import time
import traceback
import webbrowser
import yaml

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

import FileSequence

import opencue
import opencue.wrappers.group

import cuegui.ConfirmationDialog
import cuegui.Constants
import cuegui.Logger


logger = cuegui.Logger.getLogger(__file__)

__USERNAME = None


# pylint: disable=dangerous-default-value
def questionBoxYesNo(parent, title, text, items=[]):
    """A simple yes/no alert box.

    @type  parent: QObject
    @param parent: The parent for this object
    @type  title: string
    @param title: The title for the confirmation dialog
    @type  text: string
    @param text: The text to display
    @type  items: list<string>
    @param items: Optional, a list of items, such as job names that will be
                  acted on"""
    return cuegui.ConfirmationDialog.ConfirmationDialog(title, text, items, parent).exec_() == 1


def countObjectTypes(objects):
    """Given a list of objects, returns a count of how many of each type there are."""
    results = {"rootgroup": 0, "group": 0, "job": 0}
    for obj in objects:
        if isJob(obj):
            results["job"] += 1
        elif isGroup(obj):
            results["group"] += 1
        elif isRootGroup(obj):
            results["rootgroup"] += 1
    results["total"] = len(objects)
    return results


def countJobTypes(objects):
    """Given a list of jobs, returns a count of how many jobs have each status."""
    results = {"paused": False, "unpaused": False, "hasDead": False,
               "autoEating": False, "notEating": False}

    for obj in objects:
        if isJob(obj):
            if isinstance(obj, opencue.wrappers.job.NestedJob):
                obj = obj.asJob()
            if obj.data.is_paused:
                results["paused"] = True
            else:
                results["unpaused"] = True
            if obj.data.job_stats.dead_frames:
                results["hasDead"] = True
            if obj.data.auto_eat:
                results["autoEating"] = True
            else:
                results["notEating"] = True
    return results


def qvarToString(qv):
    """converts a QVariant to a python string."""
    return str(qv)


def qvarToFloat(qv):
    """converts a Qvariant to a python float."""
    return float(qv)


def isJob(obj):
    """Returns true of the object is a job, false if not
    @return: If the object is a job
    @rtype:  bool"""
    return obj.__class__.__name__ in ["Job", "NestedJob"]


def isLayer(obj):
    """Returns true if the object is a layer, false if not
    @return: If the object is a layer
    @rtype:  bool"""
    return obj.__class__.__name__ == "Layer"


def isFrame(obj):
    """Returns true if the object is frame, false if not
    @return: If the object is a frame
    @rtype:  bool"""
    return obj.__class__.__name__ == "Frame"


def isShow(obj):
    """Returns true if the object is a show, false if not
    @return: If the object is a show
    @rtype:  bool"""
    return obj.__class__.__name__ == "Show"


def isRootGroup(obj):
    """Returns true if the object is a root, false if not
    @return: If the object is a root group
    @rtype:  bool"""
    return isinstance(obj, opencue.wrappers.group.NestedGroup) and not obj.hasParent()


def isGroup(obj):
    """Returns true if the object is a group, false if not
    @return: If the object is a group
    @rtype:  bool"""
    # isinstance is needed here due to NestedGroup's inheritance
    # pylint: disable=unidiomatic-typecheck
    return (
        type(obj) == opencue.wrappers.group.Group or
        (isinstance(obj, opencue.wrappers.group.NestedGroup) and obj.hasParent()))


def isHost(obj):
    """Returns true of the object is a host, false if not
    @return: If the object is a host
    @rtype:  bool"""
    return obj.__class__.__name__ in ["NestedHost", "Host"]


def isProc(obj):
    """Returns true if the object is a proc, false if not
    @return: If the object is a proc
    @rtype:  bool"""
    return obj.__class__.__name__ in ["Proc", "NestedProc"]


def isTask(obj):
    """Returns true if the object is a task, false if not
    @return: If the object is a task
    @rtype:  bool"""
    return obj.__class__.__name__ == "Task"


# Regex matches:
#  - 12345678-1234-1234-1234-123456789ABC
#  - Job.12345678-1234-1234-1234-123456789ABC
__REGEX_ID = re.compile(r"(?:Job.)?[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}")


def isStringId(value):
    """Checks if the given string is an id
    @type  value: str
    @param value: a string that may or may not contain an uid
    @rtype:  bool
    @return: True if the string is an id"""
    return __REGEX_ID.match(value)


# pylint: disable=broad-except
def getCuewho(show):
    """Returns the username that is cuewho for the given show
    @param show: Show name
    @type  show: string
    @return: The username who is cuewho for the show
    @rtype:  string"""
    try:

        with open("/shots/%s/home/cue/cuewho.who" % show, "r", encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.warning("Failed to update cuewho: %s\n%s", show, e)
        return "Unknown"


# pylint: disable=global-statement
def getUsername():
    """Returns the username that this process is running under"""
    global __USERNAME
    if not __USERNAME:
        __USERNAME = getpass.getuser()
    return __USERNAME


# pylint: disable=broad-except
def getExtension(username):
    """Gets a user's phone extension."""
    try:
        results = subprocess.check_output(['phone', username])

        for line in results.splitlines():
            if 'Extension' in line and len(line.split()) == 2:
                return line.split()[-1]
        return "Unknown"

    except Exception as e:
        logger.warning("Failed to update extension: %s\n%s", username, e)
        return ""


def getObjectKey(rpcObject):
    """Given a rpc object, get a unique key that in the form
    'class.id'
    @type rpcObject: grpc.Message
    @param rpcObject: Rpc object to get a key for
    @rtype: str
    @return:  String key in the form <class>.<id>
    """
    objectClass = rpcObject.__class__.__name__
    objectId = rpcObject.id()
    return "{}.{}".format(objectClass, objectId)


def findJob(job):
    """Returns a job object, accepts a job object, job id or a job name.
    Returns None if no job is found.
    @param job: A job object, job id or job name
    @type  job: job or str
    @return: A job object or None
    @rtype:  job or None"""
    if isJob(job):
        return job
    if not isinstance(job, str):
        return None
    if isStringId(job):
        if re.search("^Job.", job):
            job = re.sub("Job.", "", job)
        return opencue.api.getJob(job)
    if not re.search(r"^(?:Job.)?([a-z0-9_]+)-([a-z0-9._]+)-", job, re.IGNORECASE):
        return None
    try:
        return opencue.api.findJob(job)
    except Exception as e:
        logger.warning("Error loading job: %s", job)
        logger.debug("Error loading job: %s\n%s", job, e)
        return None


def shellOut(cmd):
    """Runs a command in an external shell."""
    os.system("%s &" % cmd)


def checkShellOut(cmdList, lockGui=False):
    """Run the provided command and check it's results.
    Display an error message if the command failed
    @type: list<string>
    @param: The command to run as a space separated list.
    @type: bool
    @param: True will lock the gui while the cmd is executed, otherwise it is run in the background.
    """
    if not lockGui and platform.system() != "Windows":
        cmdList.append('&')
    try:
        subprocess.check_call(" ".join(cmdList), shell=True)
    except subprocess.CalledProcessError as e:
        text = 'Command {cmd} failed with returncode {code}. {msg}.\n' \
               'Please check your EDITOR environment variable and the ' \
               'Constants.DEFAULT_EDITOR variable.'.format(
                    cmd=e.cmd,
                    code=e.returncode,
                    msg=e.output
                )
        showErrorMessageBox(text, title="ERROR Launching Log Editor!")
    except OSError:
        text = "Command '{cmd}' not found.\n" \
               "Please set the EDITOR environment variable to a valid " \
               "editor command. Or configure an editor command using the " \
               "Constants.DEFAULT_EDITOR variable.".format(cmd=cmdList[0])
        showErrorMessageBox(text, title="ERROR Launching Log Editor!")


def exceptionOutput(e):
    """Returns formatted lines to pass to the logger
    @type  e: exception
    @param e: The exception caught"""
    results = ["Traceback (most recent call last):"]
    for item in traceback.format_list(traceback.extract_tb(sys.exc_info()[2])):
        for line in item.splitlines():
            results.append(line)
    results.append(e)
    return results


def handleExceptions(function):
    """Custom exception handler."""
    # pylint: disable=inconsistent-return-statements
    def new(*args):
        try:
            return function(*args)
        except Exception as e:
            list(map(logger.warning, exceptionOutput(e)))
    return new


def __splitTime(sec):
    """Takes an amount of seconds and returns a tuple for hours, minutes and seconds.
    @rtype:  tuple(int, int, int)
    @return: A tuple that contains hours, minutes and seconds"""
    minutes, sec = divmod(sec, 60)
    hour, minutes = divmod(minutes, 60)
    return (hour, minutes, sec)


def secondsToHHMMSS(sec):
    """Returns time in the format HH:MM:SS
    @rtype:  str
    @return: Time in the format HH:MM:SS"""
    return "%02d:%02d:%02d" % __splitTime(sec)


def secondsToHMMSS(sec):
    """Returns time in the format H:MM:SS
    @rtype:  str
    @return: Time in the format H:MM:SS"""
    return "%d:%02d:%02d" % __splitTime(sec)


def secondsToHHHMM(sec):
    """Returns time in the format HHH:MM
    @rtype:  str
    @return: Time in the format HHH:MM"""
    return "%03d:%02d" % __splitTime(sec)[:2]


def secondsDiffToHMMSS(secA, secB):
    """Returns time difference of arguements in the format H:MM:SS
    @type  secA: int or float
    @param secA: Seconds. 0 will be replaced with current time
    @type  secB: int or float
    @param secB: Seconds. 0 will be replaced with current time
    @rtype:  str
    @return: Time difference of arguments in the format H:MM:SS"""
    if secA == 0:
        secA = time.time()
    if secB == 0:
        secB = time.time()
    return secondsToHMMSS(max(secA, secB) - min(secA, secB))


def dateToMMDDHHMM(sec):
    """Returns date in the format %m/%d %H:%M
    @rtype:  str
    @return: Date in the format %m/%d %H:%M"""
    if sec == 0:
        return "--/-- --:--"
    return time.strftime("%m/%d %H:%M", time.localtime(sec))


def dateToMMDDYYYYHHMM(sec):
    """Returns date in the format %m/%d/%Y %H:%M
    @rtype:  str
    @return: Date in the format %m/%d/%Y %H:%M"""
    if sec == 0:
        return "--/-- --:--"
    return time.strftime("%m/%d/%Y %H:%M", time.localtime(sec))


def memoryToString(kmem, unit=None):
    """Returns an amount of memory in a human-friendly string."""
    k = 1024
    if unit == "K" or not unit and kmem < k:
        return "%dK" % kmem
    if unit == "M" or not unit and kmem < pow(k, 2):
        return "%dM" % (kmem // k)
    return "%.01fG" % (float(kmem) / pow(k, 2))


def getResourceConfig():
    """Reads the given yaml file and returns the entries as a dictionary.
    If no config path is given, the default resources config will be read
    If the given path does not exist, a warning will be printed and an empty
    dictionary will be returned

    @return: Resource config settings
    @rtype: dict<str:str>
    """
    return cuegui.Constants.RESOURCE_LIMITS


################################################################################
# Frame log functions
################################################################################

def getFrameLogFile(job, frame):
    """Get the log file associated with a frame. Return path based on the
    current OS path using Constants.LOG_ROOT_OS to translate paths."""
    my_os = platform.system().lower()
    job_os = job.data.os.lower()

    log_dir = job.data.log_dir
    if my_os != job_os and \
            my_os in cuegui.Constants.LOG_ROOT_OS and \
            job_os in cuegui.Constants.LOG_ROOT_OS:
        log_dir = log_dir.replace(cuegui.Constants.LOG_ROOT_OS[job_os],
                                  cuegui.Constants.LOG_ROOT_OS[my_os], 1)

    return os.path.join(log_dir, "%s.%s.rqlog" % (job.data.name, frame.data.name))


def getFrameLLU(job, frame):
    """Get a frame's last log update time."""
    __now = time.time()
    if __now - getattr(frame, "getFrameLLUTime", 0) >= 5:
        # pylint: disable=bare-except
        try:
            frame.getFrameLLU = __now - os.stat(getFrameLogFile(job, frame)).st_mtime
        except:
            frame.getFrameLLU = 0
        frame.getFrameLLUTime = __now
    return frame.getFrameLLU


def getFrameLastLine(job, frame):
    """Get the last line of a frame log."""
    __now = time.time()
    if __now - getattr(frame, "getFrameLastLineTime", 0) >= 5:
        frame.getFrameLastLine = getLastLine(getFrameLogFile(job, frame))
        frame.getFrameLastLineTime = __now
    return frame.getFrameLastLine


def getLastLine(path):
    """Reads the last line from the file."""

    ansiEscape = r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]'

    try:
        with open(path, 'rb') as fp:
            fp.seek(0, 2)

            backseek = min(4096, fp.tell())
            fp.seek(-backseek, 1)
            buf = fp.read(4096)

            newline_pos = buf.rfind(b'\n', 0, len(buf)-1)

        line = buf[newline_pos+1:].strip().decode("utf-8")

        return re.sub(ansiEscape, "", line)
    except IOError:
        return ""


def popupTail(file, facility=None):
    """Opens an xterm window showing the tail of the given file."""
    if file and not popupWeb(file, facility):
        job_log_cmd = (
                "/usr/bin/xterm -sb -sl 4096 -n RQLOG -geometry 200x50+0+0 -title %s "
                "-e '/usr/bin/tail -n+0 -f %s'" % (os.path.basename(file), file))
        shellOut(job_log_cmd)


def popupView(file, facility=None):
    """Opens the given file in your editor."""
    if file and not popupWeb(file, facility):
        editor_from_env = os.getenv('EDITOR')
        app = cuegui.app()
        if editor_from_env:
            job_log_cmd = editor_from_env.split()
        elif app.settings.contains('LogEditor') and (
                len(app.settings.value("LogEditor").strip()) > 0):
            job_log_cmd = app.settings.value("LogEditor").split()
            if not isinstance(job_log_cmd, list):
                job_log_cmd = job_log_cmd.split()
        else:
            job_log_cmd = cuegui.Constants.DEFAULT_EDITOR.split()
        job_log_cmd.append(str(file))
        checkShellOut(job_log_cmd)


def openURL(url):
    """Opens a URL."""
    webbrowser.open_new(url)
    return True


def popupWeb(file, facility=None):
    """Opens a web browser."""
    client = os.getenv('FACILITY', 'unknown')
    if client in ['yvr'] or (facility == 'yvr' and client in ['lax']):
        webbrowser.open_new('' + file)
        return True
    return False


def popupFrameTail(job, frame, logNumber=0):
    """Opens a tail of a frame log."""
    path = getFrameLogFile(job, frame)
    if logNumber:
        path += ".%s" % logNumber
    popupTail(path, job.data.facility)


def popupFrameView(job, frame, logNumber=0):
    """Opens a frame."""
    path = getFrameLogFile(job, frame)
    if logNumber:
        path += ".%s" % logNumber
    popupView(path, job.data.facility)


def popupFrameXdiff(job, frame1, frame2, frame3 = None):
    """Opens a frame xdiff."""
    for command in ['/usr/bin/xxdiff',
                    '/usr/local/bin/xdiff']:
        if os.path.isfile(command):
            for frame in [frame1, frame2, frame3]:
                if frame:
                    command += " --title1 %s %s" % (frame.data.name, getFrameLogFile(job, frame))
            shellOut(command)

################################################################################
# View output in viewer
################################################################################

def viewOutput(items, actionText):
    """Views the output of a list of jobs or list of layers in viewer

    @type       items: list<Job> or list<Layer>
    @param      items: List of jobs or list of layers to view the entire job's outputs
    @type  actionText: String
    @param actionText: String to identity which viewer to use"""
    if items and len(items) >= 1:
        paths = []

        if isJob(items[0]):
            for job in items:
                path_list = __getOutputFromLayers(job.getLayers())
                paths.extend(path_list)

        elif isLayer(items[0]):
            paths = __getOutputFromLayers(items)

        else:
            raise Exception("The function expects a list of jobs or a list of layers")

        # Launch viewer using paths if paths exists and are valid
        launchViewerUsingPaths(paths, actionText)


def viewFramesOutput(job, frames, actionText):
    """Views the output of a list of frames in viewer using the job's layer
    associated with the frames

    @type  job: Job or None
    @param job: The job with the output to view.
    @type  frames: list<Frame>
    @param frames: List of frames to view the entire job's outputs
    @type  actionText: String
    @param actionText: String to identity which viewer to use"""

    if frames and len(frames) >= 1:
        paths = []

        all_layers = { layer.name(): layer for layer in job.getLayers() }
        for frame in frames:
            paths.extend(getOutputFromFrame(all_layers[frame.layer()], frame))
        launchViewerUsingPaths(paths, actionText)

def getViewer(actionText):
    """Retrieves the viewer from cuegui.Constants.OUTPUT_VIEWERS using the actionText

    @type  actionText: String
    @param actionText: String to identity which viewer to use"""

    for viewer in cuegui.Constants.OUTPUT_VIEWERS:
        if viewer['action_text'] == actionText:
            return viewer
    return None

def launchViewerUsingPaths(paths, actionText, test_mode=False):
    """Launch viewer using paths if paths exists and are valid
    This function relies on the following constants that should be configured on the output_viewer
    section of the config file:
        - OUTPUT_VIEWER_STEREO_MODIFIERS
        - OUTPUT_VIEWER_EXTRACT_ARGS_REGEX
        - OUTPUT_VIEWER_CMD_PATTERN
    @type  paths: list<String>
    @param paths: List of paths
    @type  actionText: String
    @param actionText: String to identity which viewer to use"""
    viewer = getViewer(actionText)
    if not paths:
        if not test_mode:
            showErrorMessageBox(
                "Sorry, unable to find any completed frames with known output paths",
                title="Unable to find completed frames")
        return None

    # If paths are stereo outputs only keep one of the variants.
    # Stereo ouputs are usually differentiated by a modifier like _lf_ and _rt_,
    # the viewer should only be called with one of them if OUTPUT_VIEWER_STEREO_MODIFIERS
    # is set.
    if 'stereo_modifiers' in viewer:
        stereo_modifiers = viewer['stereo_modifiers'].split(",")
        if len(paths) == 2 and len(stereo_modifiers) == 2:
            unified_paths = [path.replace(stereo_modifiers[0].strip(),
                                        stereo_modifiers[1].strip())
                            for path in paths]
            if len(set(unified_paths)) == 1:
                paths.pop()

    # If a regex is provided, the first path will be used to extract groups
    # to be applied cmd_pattern. The number of groups extracted from regexp
    # should be the same as the quantity expected by cmd_pattern.
    # If no regex is provided, cmd_pattern is executed as it is
    sample_path = paths[0]
    regexp = viewer.get('extract_args_regex')
    cmd_pattern = viewer.get('cmd_pattern')
    joined_paths = " ".join(paths)

    # Default to the cmd + paths
    cmd = "%s %s" % (cmd_pattern, joined_paths)
    if regexp:
        try:
            match = re.search(regexp, sample_path)
            if match is None:
                raise KeyError
            args = match.groupdict()
            args.update({"paths": joined_paths})
            # Raises KeyError if args don't match pattern
            cmd = cmd_pattern.format(**args)
        except KeyError:
            print("groups extracted by regex output_viewer.extract_args_regex "
                    "(%s) on sample path (%s) don't match output_viewer.cmd_pattern (%s) " %
                    (regexp, sample_path, cmd_pattern))
            if not test_mode:
                showErrorMessageBox("Sorry, unable to launch viewer with provided parameters",
                                    title="Viewer misconfigured")
            return None

    # Launch viewer and inform user
    msg = 'Launching viewer: {0}'.format(cmd)
    if not test_mode:
        print(msg)
        try:
            # pylint: disable=consider-using-with
            subprocess.Popen(cmd.split())
        except subprocess.CalledProcessError as e:
            showErrorMessageBox(str(e), title='Error running Viewer command')
        except Exception as e:
            showErrorMessageBox(str(e), title='Unable to open output in Viewer')

    return cmd


def __findMainOutputPath(outputs):
    """Returns the main output layer from list of output paths
    @type  outputs: list<str>
    @param outputs: A list of output paths"""
    if not outputs:
        return ''
    try:
        # Try to find the bty layer from the list of output paths
        # The bty layers are named with this convention:
        # <res>_<colorspace>_<format>
        # Example: 2kdcs_lnf_exr, misc_vd8_jpg
        for output in outputs:
            layer_name = output.split('/')[-2]
            if len(layer_name.split('_')) == 3:
                return output
    except IndexError:
        pass
    return outputs[0]


def __getOutputFromLayers(layers):
    """Returns the output paths from the frame logs
    @type  layers: list<Layer>
    @param layers: A list of at least one layer
    @rtype:  list
    @return: The path to the proxy SVI or the primary output."""
    paths = []
    for layer in layers:
        svi_found = False
        outputs = layer.getOutputPaths()
        if outputs:
            for path in outputs:
                if path.find("_svi") != -1:
                    paths.append(path)
                    svi_found = True
                    break
            if not svi_found:
                output = __findMainOutputPath(outputs)
                paths.append(output)
    return paths


def getOutputFromFrame(layer, frame):
    """Returns the output paths from a single frame

    @type  layer: Layer
    @param layer: The frames' layer
    @type  frame: Frame
    @param frame: This frame's log is checked for known output paths
    @rtype:  list
    @return: A list of output paths"""
    try:
        outputs = layer.getOutputPaths()
        if not outputs:
            return []
        seq = FileSequence.FileSequence(__findMainOutputPath(outputs))
        return seq.getFileList(frameSet=FileSequence.FrameSet(str(frame.number())))
    except IndexError:
        return []


__REGEX_AOV = re.compile("aov\\_", re.IGNORECASE)


def reorganizeOrder(paths):
    """ Returns the output paths with aov passes appended to the end of the list
    so viewer doesn't load it first

    @param  paths: list
    @rtype: list
    @return: A list of reorganized output paths"""
    aov_layer = []
    render_layer = []
    if paths:
        for path in paths:
            render_pass_name = path.split("/")[-1]
            if re.search(__REGEX_AOV, render_pass_name):
                aov_layer.append(path)
            else:
                render_layer.append(path)
        paths = render_layer + aov_layer

    return paths

################################################################################
# Drag and drop functions
################################################################################

def startDrag(dragSource, dropActions, objects):
    """Event handler for when a drag starts."""
    del dropActions

    mimeData = QtCore.QMimeData()
    mimeData.setText("\n".join(["%s" % job.data.name for job in objects]))

    mimeDataAdd(mimeData,
                "application/x-job-names",
                [object.data.name for object in objects if isJob(object)])

    mimeDataAdd(mimeData,
                "application/x-job-ids",
                [opencue.id(object) for object in objects if isJob(object)])

    mimeDataAdd(mimeData,
                "application/x-group-names",
                [object.data.name for object in objects if isGroup(object)])

    mimeDataAdd(mimeData,
                "application/x-group-ids",
                [opencue.id(object) for object in objects if isGroup(object)])

    mimeDataAdd(mimeData,
                "application/x-host-names",
                [object.data.name for object in objects if isHost(object)])

    mimeDataAdd(mimeData,
                "application/x-host-ids",
                [opencue.id(object) for object in objects if isHost(object)])

    drag = QtGui.QDrag(dragSource)
    drag.setMimeData(mimeData)
    drag.exec_(QtCore.Qt.MoveAction)


def dragEnterEvent(event, mime_format="application/x-job-names"):
    """Event handler for when a drag enters an area."""
    if event.mimeData().hasFormat(mime_format):
        event.accept()
    else:
        event.ignore()


def dragMoveEvent(event, mime_format="application/x-job-names"):
    """Event handler for when a drag is moved."""
    if event.mimeData().hasFormat(mime_format):
        event.setDropAction(QtCore.Qt.CopyAction)
        event.accept()
    else:
        event.ignore()


# pylint: disable=inconsistent-return-statements
def dropEvent(event, mime_format="application/x-job-names"):
    """Event handler for when a drop occurs."""
    if event.mimeData().hasFormat(mime_format):
        item = event.mimeData().data(mime_format)
        stream = QtCore.QDataStream(item, QtCore.QIODevice.ReadOnly)
        names = stream.readQString()
        event.accept()
        return [name for name in str(names).split(":") if name]


def mimeDataAdd(mimeData, mimeFormat, objects):
    """Sets mime data."""
    data = QtCore.QByteArray()
    stream = QtCore.QDataStream(data, QtCore.QIODevice.WriteOnly)
    text = ":".join(objects)
    stream.writeQString(text)
    mimeData.setData(mimeFormat, data)


def showErrorMessageBox(text, title="ERROR!", detailedText=None):
    """Displays an error dialog."""
    messageBox = QtWidgets.QMessageBox()
    messageBox.setIcon(QtWidgets.QMessageBox.Critical)
    messageBox.setText(text)
    messageBox.setWindowTitle(title)
    if detailedText:
        messageBox.setDetailedText(detailedText)
    messageBox.setStandardButtons(QtWidgets.QMessageBox.Close)
    return messageBox.exec_()


def shutdownThread(thread):
    """Shuts down a WorkerThread."""
    thread.stop()
    # Stop may terminate the underlying thread object yielding a
    # RuntimeError(QtFatal) when wait is called
    try:
        return thread.wait(1500)
    except RuntimeError:
        return False

def getLLU(item):
    """ LLU time from log_path """
    if isProc(item):
        logFile = item.data.log_path
    elif isFrame(item):
        logFile = item.log_path
    else:
        return ""
    try:
        statInfo = os.path.getmtime(logFile)
    except Exception as e:
        logger.info("not able to extract LLU: %s", e)
        return None

    lluTime = time.time() - statInfo

    return lluTime

def numFormat(num, _type):
    """ format LLU time """
    if num == "" or num < .001 or num is None:
        return ""
    if _type == "t":
        return secondsToHHMMSS(int(num))
    if _type == "f":
        return "%.2f" % float(num)

def byteConversion(amount, btype):
    """ convert unit of memory size into bytes for comparing different
        unit measures

    :param amount: unit of memory size
    :ptype amount: float
    :param btype: unit type
    :ptype btype: string
    :return: unit in bytes
    :rtype: float
    """
    n = 1
    conversionMap = {"KB": 1, "TB": 4, "GB": 3, "MB": 2}
    _bytes = amount
    if btype.upper() in conversionMap:
        n = conversionMap[btype.upper()]
    for _ in range(n):
        _bytes *= 1024
    return _bytes


def isPermissible(jobObject):
    """
    Validate if the current user has the correct permissions to perform
    the action

    :param userName: jobObject
    :ptype userName: Opencue Job Object
    :return:
    """
    # Read cached setting from user config file
    hasPermissions = yaml.safe_load(cuegui.app().settings.value("EnableJobInteraction", "False"))
    # If not set by default, check if current user is the job owner
    currentUser = getpass.getuser()
    if not hasPermissions and currentUser.lower() == jobObject.username().lower():
        hasPermissions = True
    return hasPermissions
