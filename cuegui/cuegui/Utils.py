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

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
import getpass
import six

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


__REGEX_ID = re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}")


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
    if not isinstance(job, six.string_types):
        return None
    if isStringId(job):
        return opencue.api.getJob(job)
    if not re.search(r"^([a-z0-9\_]+)\-([a-z0-9\.\_]+)\-", job, re.IGNORECASE):
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
        elif app.settings.contains('LogEditor'):
            job_log_cmd = app.settings.value("LogEditor")
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
    return thread.wait(1500)

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
    hasPermissions = False
    # Case 1. Check if current user is the job owner
    currentUser = getpass.getuser()
    if currentUser.lower() == jobObject.username().lower():
        hasPermissions = True

    # Case 2. Check if "Enable not owned Job Interactions" is Enabled
    if bool(int(QtGui.qApp.settings.value("EnableJobInteraction", 0))):
        hasPermissions = True

    return hasPermissions
