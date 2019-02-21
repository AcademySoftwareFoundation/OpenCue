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
Displays the email dialog when emailing an artist.
"""
from __future__ import absolute_import


from builtins import str
from builtins import map
try:
    from email.MIMEText import MIMEText
    from email.Header import Header
except ImportError:
    from email.mime.text import MIMEText
    from email.header import Header
import os
# pwd is not available on Windows.
# TODO(bcipriano) Clean this up.
try:
    import pwd
except ImportError:
    pass
import smtplib

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import opencue
from . import Logger
from . import Utils
from . import Constants


logger = Logger.getLogger(__file__)


class EmailDialog(QtWidgets.QDialog):
    def __init__(self, job, format, parent = None):
        QtWidgets.QDialog.__init__(self, parent)

        try:
            self.__frames = job.getFrames(state=[opencue.api.job_pb2.DEAD])
        except:
            self.__frames = []

        self.setWindowTitle("Email For: %s" % job.data.name)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.setFixedSize(1000,600)

        self.__email = EmailWidget(job, format, self)
        self.__appendDeadFrameInfo(job)
        self.__logView = LogViewWidget(job, self.__frames, self)

        hlayout = QtWidgets.QHBoxLayout(self)
        hlayout.addWidget(self.__email)
        hlayout.addWidget(self.__logView)

        self.__email.giveFocus()

        self.__email.send.connect(self.accept)
        self.__email.cancel.connect(self.reject)

    def __appendDeadFrameInfo(self, job):
        """Adds frame data to email body
        @type  job: job
        @param job: The job to email about"""
        if job.data.job_stats.dead_frames:
            self.__email.appendToBody("\nFrames:")
            i_total_render_time = 0
            i_total_retries = 0
            for frame in self.__frames:
                self.__email.appendToBody("%s\t%s\tRuntime: %s\tRetries: %d" % (
                    frame.data.name,
                    frame.state(),
                    Utils.secondsToHHMMSS(frame.runTime()), frame.retries()))
                i_total_render_time += frame.retries() * frame.runTime()
                i_total_retries += frame.retries()
            try:
                self.__email.appendToBody("\nEstimated Proc Hours: %0.2f\n\n" % \
                                              ((i_total_render_time / 3600.0)))
            except:
                pass

class LogViewWidget(QtWidgets.QWidget):
    def __init__(self, job, frames, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        QtWidgets.QVBoxLayout(self)
        ly = self.layout()

        self.__job = job
        self.__frames = frames

        self.__sel_frames = QtWidgets.QComboBox(self)
        for frame in frames:
            self.__sel_frames.addItem(frame.data.name)

        self.__txt_find = QtWidgets.QLineEdit(self)

        self.__txt_log = QtWidgets.QPlainTextEdit(self)
        self.__txt_log.setWordWrapMode(QtGui.QTextOption.NoWrap)
        self.__txt_log.ensureCursorVisible()

        if self.__frames:
            self.switchLogEvent(self.__frames[0].data.name)

        ly.addWidget(QtWidgets.QLabel("Select Frame:", self))
        ly.addWidget(self.__sel_frames)
        ly.addWidget(QtWidgets.QLabel("Find:", self))
        ly.addWidget(self.__txt_find)
        ly.addWidget(self.__txt_log)

        self.__sel_frames.activated.connect(self.switchLogEvent)
        self.__txt_find.returnPressed.connect(self.findEvent)

    def __getFrame(self, name):
        for frame in self.__frames:
            if frame.data.name == name:
                return frame

    def switchLogEvent(self, str_frame):
        try:
            self.__txt_log.clear()
            log_file_path = Utils.getFrameLogFile(self.__job, self.__getFrame(str_frame))
            fp = open(log_file_path,"r")
            if os.path.getsize(log_file_path) > 1242880:
                fp.seek(0, 2)
                fp.seek(-1242880, 1)
            # Bad characters in the log can cause the remainder of the log to be left out
            # so ignore any invalid characters
            self.__txt_log.appendPlainText(fp.read().decode('utf8', 'ignore'))
            self.__txt_log.textCursor().movePosition(QtGui.QTextCursor.End)
            self.__txt_log.appendPlainText("\n")
            fp.close()

        except Exception as e:
            list(map(logger.warning, Utils.exceptionOutput(e)))
            logger.info("error loading frame: %s, %s" % (str_frame, e))

    def findEvent(self):
        """attempts to find the text from the find text box,
        highlights and scrolls to it"""
        document = self.__txt_log.document()
        cursor = document.find(
            str(self.__txt_find.text()).strip(),
            self.__txt_log.textCursor().position(),
            QtWidgets.QTextDocument.FindBackward)
        if cursor.position() > 1:
            self.__txt_log.setTextCursor(cursor)

class EmailWidget(QtWidgets.QWidget):

    send = QtCore.Signal()
    cancel = QtCore.Signal()

    def __init__(self, job, format, parent=None):
        QtWidgets.QWidget.__init__(self)

        self.__job = job

        # Temporary workaround when pwd library is not available (i.e. Windows).
        # TODO(bcipriano) Clean this up.
        if 'pwd' in globals():
            user_name = pwd.getpwnam(job.username()).pw_gecos
        else:
            user_name = job.username()

        __default_from = "%s-pst@%s" % (job.show(), Constants.EMAIL_DOMAIN)
        __default_to = "%s@%s" % (job.username(), Constants.EMAIL_DOMAIN)
        __default_cc = "%s-pst@%s" % (job.show(), Constants.EMAIL_DOMAIN)
        __default_bcc = ""
        __default_subject = "%s%s" % (Constants.EMAIL_SUBJECT_PREFIX, job.data.name)
        __default_body = "%s%s%s" % (Constants.EMAIL_BODY_PREFIX, job.data.name,
                                     Constants.EMAIL_BODY_SUFFIX)
        __default_body += "Hi %s,\n\n" % user_name

        self.__btnSend = QtWidgets.QPushButton("Send", self)
        self.__btnCancel = QtWidgets.QPushButton("Cancel", self)

        # Body Widgets
        self.__email_body = QtWidgets.QTextEdit(self)
        self.appendToBody(__default_body)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Minimum)

        self.__email_from = QtWidgets.QLineEdit(__default_from, self)
        self.__email_to = QtWidgets.QLineEdit(__default_to, self)
        self.__email_cc = QtWidgets.QLineEdit(__default_cc, self)
        self.__email_bcc = QtWidgets.QLineEdit(__default_bcc, self)
        self.__email_subject = QtWidgets.QLineEdit(__default_subject, self)

        # Main Virtical Layout
        vlayout = QtWidgets.QVBoxLayout(self)

        # Top Grid Layout
        glayout = QtWidgets.QGridLayout()
        glayout.setContentsMargins(0, 0, 0, 0)

        glayout.addWidget(QtWidgets.QLabel("From:", self), 0, 0)
        glayout.addWidget(self.__email_from, 0, 1)

        glayout.addWidget(QtWidgets.QLabel("To:", self), 1, 0)
        glayout.addWidget(self.__email_to, 1, 1)

        glayout.addWidget(QtWidgets.QLabel("CC:", self), 2, 0)
        glayout.addWidget(self.__email_cc, 2, 1)

        glayout.addWidget(QtWidgets.QLabel("BCC:", self), 3, 0)
        glayout.addWidget(self.__email_bcc, 3, 1)

        glayout.addWidget(QtWidgets.QLabel("Subject:", self), 4, 0)
        glayout.addWidget(self.__email_subject, 4, 1)

        vlayout.addLayout(glayout)
        vlayout.addWidget(self.__email_body)

        # Bottom Horizontal Layout
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addItem(spacerItem)
        hlayout.addWidget(self.__btnSend)
        hlayout.addWidget(self.__btnCancel)
        vlayout.addLayout(hlayout)

        self.__btnSend.clicked.connect(self.sendEmail)
        self.__btnCancel.clicked.connect(self.cancel.emit)

    def giveFocus(self):
        self.__email_body.setFocus(QtCore.Qt.OtherFocusReason)
        self.__email_body.moveCursor(QtGui.QTextCursor.Start)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)

    def email_from(self):
        return "%s" % self.__email_from.text()

    def email_to(self):
        return "%s" % self.__email_to.text()

    def email_cc(self):
        return "%s" % self.__email_cc.text()

    def email_bcc(self):
        return "%s" % self.__email_bcc.text()

    def email_subject(self):
        return "%s" % self.__email_subject.text()

    def email_body(self):
        return "%s" % self.__email_body.toPlainText().toAscii()

    def appendToBody(self, txt):
        self.__email_body.append(txt)

    def setBody(self, txt):
        self.__email_body.setText(txt)

    def sendEmail(self):
        self.send.emit()

        msg = MIMEText(self.email_body())
        msg["Subject"] = Header(self.email_subject(), continuation_ws=' ')
        msg["To"] = self.email_to()
        msg["From"] = self.email_from()
        msg["Cc"] = self.email_cc()

        recipient_list = []
        if self.email_to():
            recipient_list.extend(self.email_to().split(","))

        if self.email_cc():
            recipient_list.extend(self.email_cc().split(","))

        if self.email_bcc():
            recipient_list.extend(self.email_bcc().split(","))

        server = smtplib.SMTP('smtp')
        server.sendmail(self.email_from(), recipient_list, msg.as_string())
        server.quit()
