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


"""
Utility functions.
"""


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

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets
import yaml
from yaml.scanner import ScannerError

import opencue

import cuegui.ConfirmationDialog
import cuegui.Constants
import cuegui.Logger


logger = cuegui.Logger.getLogger(__file__)

__USERNAME = None


def questionBoxYesNo(parent, title, text, items = []):
    """A simple yes/no alert box
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
    results = {"rootgroup": 0, "group": 0, "job": 0}
    for object in objects:
        if isJob(object):
            results["job"] += 1
        elif isGroup(object):
            results["group"] += 1
        elif isRootGroup(object):
            results["rootgroup"] += 1
    results["total"] = len(objects)
    return results


def countJobTypes(objects):
    results = {"paused": False, "unpaused": False, "hasDead": False,
               "autoEating": False, "notEating": False}

    for object in objects:
        if isJob(object):
            if isinstance(object, opencue.wrappers.job.NestedJob):
                object = object.asJob()
            if object.data.is_paused:
                results["paused"] = True
            else:
                results["unpaused"] = True
            if object.data.job_stats.dead_frames:
                results["hasDead"] = True
            if object.data.auto_eat:
                results["autoEating"] = True
            else:
                results["notEating"] = True
    return results


def qvarToString(qv):
    """converts a QVariant to a python string"""
    return str(qv)


def qvarToFloat(qv):
    """converts a Qvariant to a python float"""
    return float(qv)


def isJob(object):
    """Returns true of the object is a job, false if not
    @return: If the object is a job
    @rtype:  bool"""
    return object.__class__.__name__ in ["Job", "NestedJob"]


def isLayer(object):
    """Returns true if the object is a layer, false if not
    @return: If the object is a layer
    @rtype:  bool"""
    return object.__class__.__name__ == "Layer"


def isFrame(object):
    """Returns true if the object is frame, false if not
    @return: If the object is a frame
    @rtype:  bool"""
    return object.__class__.__name__ == "Frame"


def isShow(object):
    """Returns true if the object is a show, false if not
    @return: If the object is a show
    @rtype:  bool"""
    return object.__class__.__name__ == "Show"


def isRootGroup(object):
    """Returns true if the object is a root, false if not
    @return: If the object is a root group
    @rtype:  bool"""
    return object.__class__.__name__ in ["NestedGroup", "Group"] and not object.parent


def isGroup(object):
    """Returns true if the object is a group, false if not
    @return: If the object is a group
    @rtype:  bool"""
    return object.__class__.__name__ in ["NestedGroup", "Group"] and (not hasattr(object, "parent") or object.parent)


def isHost(object):
    """Returns true of the object is a host, false if not
    @return: If the object is a host
    @rtype:  bool"""
    return object.__class__.__name__ in ["NestedHost", "Host"]


def isProc(object):
    """Returns true if the object is a proc, false if not
    @return: If the object is a proc
    @rtype:  bool"""
    return object.__class__.__name__ in ["Proc", "NestedProc"]


def isTask(object):
    """Returns true if the object is a task, false if not
    @return: If the object is a task
    @rtype:  bool"""
    return object.__class__.__name__ == "Task"


__REGEX_ID = re.compile("[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}")


def isStringId(value):
    """Checks if the given string is an id
    @type  value: str
    @param value: a string that may or may not contain an uid
    @rtype:  bool
    @return: True if the string is an id"""
    return __REGEX_ID.match(value)


def getCuewho(show):
    """Returns the username that is cuewho for the given show
    @param show: Show name
    @type  show: string
    @return: The username who is cuewho for the show
    @rtype:  string"""
    try:
        file = open("cuewho.who" % show, "r")
        return file.read()
    except Exception as e:
        logger.warning("Failed to update cuewho: %s\n%s" % (show, e))
        return "Unknown"


def getUsername():
    """Returns the username that this process is running under"""
    global __USERNAME
    if not __USERNAME:
        __USERNAME = getpass.getuser()
    return __USERNAME


def getExtension(username):
    try:
        # TODO: Replace this with a direct call to the phone util that the
        # phone widget uses once code is stable
        results = subprocess.check_output('phone %s' % username)

        for line in results.splitlines():
            if line.find('Extension') != -1 and len(line.split()) == 2:
                return line.split()[-1]
        return "Unknown"

    except Exception as e:
        logger.warning("Failed to update extension: %s\n%s" % (username, e))
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
        return opencue.api.getJob(job)
    if not re.search("^([a-z0-9]+)\-([a-z0-9\.]+)\-", job, re.IGNORECASE):
        return None
    try:
        return opencue.api.findJob(job)
    except Exception as e:
        logger.warning("Error loading job: %s" % job)
        logger.debug("Error loading job: %s\n%s" % (job, e))
        return None


def shellOut(cmd):
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
        subprocess.check_call(cmdList)
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
    min, sec = divmod(sec, 60)
    hour, min = divmod(min, 60)
    return (hour, min, sec)


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


def memoryToString(kmem, unit = None):
    k = 1024
    if unit == "K" or not unit and kmem < k:
        return "%dK" % kmem
    if unit == "M" or not unit and kmem < pow(k,2):
        return "%dM" % (kmem // k)
    if unit == "G" or not unit and kmem < pow(k,3):
        return "%.01fG" % (float(kmem) / pow(k,2))


def getResourceConfig(path=None):
    """Reads the given yaml file and returns the entries as a dictionary.
    If no config path is given, the default resources config will be read
    If the given path does not exist, a warning will be printed and an empty
    dictionary will be returned

    @param path: The path for the yaml file to read
    @type path: str
    @return: The entries in the given yaml file
    @rtype: dict<str:str>
    """

    config = {}
    if not path:
        path = '{}/cue_resources.yaml'.format(cuegui.Constants.DEFAULT_INI_PATH)
    try:
        with open(path, 'r') as fileObject:
            config = yaml.load(fileObject, Loader=yaml.SafeLoader)
    except (IOError, ScannerError) as e:
        print ('WARNING: Could not read config file %s: %s'
               % (path, e))
    return config


################################################################################
# Frame log functions
################################################################################

def getFrameLogFile(job, frame):
    return os.path.join(job.data.log_dir, "%s.%s.rqlog" % (job.data.name, frame.data.name))


def getFrameLLU(job, frame):
    __now = time.time()
    if __now - getattr(frame, "getFrameLLUTime", 0) >= 5:
        try:
            frame.getFrameLLU = __now - os.stat(getFrameLogFile(job, frame)).st_mtime
        except:
            frame.getFrameLLU = 0
        frame.getFrameLLUTime = __now
    return frame.getFrameLLU


def getFrameLastLine(job, frame):
    __now = time.time()
    if __now - getattr(frame, "getFrameLastLineTime", 0) >= 5:
        frame.getFrameLastLine = getLastLine(getFrameLogFile(job, frame))
        frame.getFrameLastLineTime = __now
    return frame.getFrameLastLine


def getLastLine(path):
    """Reads the last line from the file"""
    ansiEscape = '(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]'

    try:
        fp=open(path, 'r')
        fp.seek(0, 2)

        backseek = min(4096, fp.tell())
        fp.seek(-backseek, 1)
        buf = fp.read(4096)

        newline_pos = buf.rfind("\n",0,len(buf)-1)
        fp.close()

        line = buf[newline_pos+1:].strip()

        return re.sub(ansiEscape, "", line)
    except IOError:
        return ""


def popupTail(file, facility=None):
    if file and not popupWeb(file, facility):
        JOB_LOG_CMD = "/usr/bin/xterm -sb -sl 4096 -n RQLOG -geometry 200x50+0+0 -title %s -e '/usr/bin/tail -n+0 -f %s'" % (os.path.basename(file), file)
        shellOut(JOB_LOG_CMD)


def popupView(file, facility=None):
    if file and not popupWeb(file, facility):
        editor_from_env = os.getenv('EDITOR')
        if editor_from_env:
            job_log_cmd = editor_from_env.split()
        elif QtGui.qApp.settings.contains('LogEditor'):
            job_log_cmd = QtGui.qApp.settings.value("LogEditor")
        else:
            job_log_cmd = cuegui.Constants.DEFAULT_EDITOR.split()
        job_log_cmd.append(str(file))
        checkShellOut(job_log_cmd)


def openURL(url):
    import webbrowser
    webbrowser.open_new(url)
    return True


def popupWeb(file, facility=None):
    client = os.getenv('FACILITY', 'unknown')
    if client in ['yvr'] or (facility == 'yvr' and client in ['lax']):
        import webbrowser
        webbrowser.open_new('' + file)
        return True
    return False


def popupFrameTail(job, frame, logNumber = 0):
    path = getFrameLogFile(job, frame)
    if logNumber:
        path += ".%s" % logNumber
    popupTail(path, job.data.facility)


def popupFrameView(job, frame, logNumber = 0):
    path = getFrameLogFile(job, frame)
    if logNumber:
        path += ".%s" % logNumber
    popupView(path, job.data.facility)


def popupFrameXdiff(job, frame1, frame2, frame3 = None):
    for command in ['/usr/bin/xxdiff',
                    '/usr/local/bin/xdiff']:
        if os.path.isfile(command):
            for frame in [frame1, frame2, frame3]:
                if frame:
                    command += " --title1 %s %s" % (frame.data.name, getFrameLogFile(job, frame))
            shellOut(command)


def getOutputFromLayers(job, layers):
    """Returns the output paths from the frame logs
    @type  job: Job
    @param job: A job object
    @type  layers: list<Layer>
    @param layers: A list of at least one later
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
                paths.append(outputs[0])
    return paths


def getOutputFromFrame(job, layer, frame):
    """Returns the output paths from a single frame
    @type  job: Job
    @param job: A job object
    @type  frame: Frame
    @param frame: This frame's log is checked for known output paths
    @rtype:  list
    @return: A list of output paths"""
    try:
        main_output = layer.getOutputPaths()[0]
        main_output = main_output.replace("#", "%04d" % frame.data.number)
        return [main_output]
    except IndexError:
        return []


################################################################################
# Drag and drop functions
################################################################################

def startDrag(dragSource, dropActions, objects):
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


def dragEnterEvent(event, format = "application/x-job-names"):
    if event.mimeData().hasFormat(format):
        event.accept()
    else:
        event.ignore()


def dragMoveEvent(event, format = "application/x-job-names"):
    if event.mimeData().hasFormat(format):
        event.setDropAction(QtCore.Qt.CopyAction)
        event.accept()
    else:
        event.ignore()


def dropEvent(event, format = "application/x-job-names"):
    if event.mimeData().hasFormat(format):
        item = event.mimeData().data(format)
        stream = QtCore.QDataStream(item, QtCore.QIODevice.ReadOnly)
        names = stream.readQString()
        event.accept()
        return [name for name in str(names).split(":") if name]


def mimeDataAdd(mimeData, format, objects):
    data = QtCore.QByteArray()
    stream = QtCore.QDataStream(data, QtCore.QIODevice.WriteOnly)
    text = ":".join(objects)
    stream.writeQString(text)
    mimeData.setData(format, data)


def showErrorMessageBox(text, title="ERROR!", detailedText=None):
    messageBox = QtWidgets.QMessageBox()
    messageBox.setIcon(QtWidgets.QMessageBox.Critical)
    messageBox.setText(text)
    messageBox.setWindowTitle(title)
    if detailedText:
        messageBox.setDetailedText(detailedText)
    messageBox.setStandardButtons(QtWidgets.QMessageBox.Close)
    return messageBox.exec_()

def shutdownThread(thread):
    """Shutdown a WorkerThread."""
    thread.stop()
    return thread.wait(1500)
