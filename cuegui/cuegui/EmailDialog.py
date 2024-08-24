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


"""Dialog for emailing a job owner."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import map
try:
    from email.MIMEText import MIMEText
    from email.Header import Header
except ImportError:
    from email.mime.text import MIMEText
    from email.header import Header
# pwd is not available on Windows.
# TODO(bcipriano) Remove this, not needed once user info can come directly from Cuebot.
#  (https://github.com/imageworks/OpenCue/issues/218)
try:
    import pwd
except ImportError:
    pass
import smtplib

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

import cuegui.Constants
import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)

SUBJ_LINE_TOO_LONG = 2


class EmailDialog(QtWidgets.QDialog):
    """Dialog for emailing a job owner."""

    def __init__(self, jobs, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        job_names = ','.join(map(lambda job: job.data.name, jobs))

        self.setWindowTitle("Email For: %s" % job_names)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.setFixedSize(1000, 600)

        self.__email = EmailWidget(jobs, self)

        hlayout = QtWidgets.QHBoxLayout(self)
        hlayout.addWidget(self.__email)

        self.__email.giveFocus()

        self.__email.send.connect(self.accept)
        self.__email.cancel.connect(self.reject)


class EmailWidget(QtWidgets.QWidget):
    """Widget for displaying an email form."""

    send = QtCore.Signal()
    cancel = QtCore.Signal()

    def __init__(self, jobs, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # pylint: disable=unused-private-member
        self.__jobs = jobs

        # Temporary workaround when pwd library is not available (i.e. Windows).
        # TODO(bcipriano) Pull this info directly from Cuebot.
        #  (https://github.com/imageworks/OpenCue/issues/218)
        user_names = set()
        if 'pwd' in globals():
            for job in jobs:
                user_names.add(pwd.getpwnam(job.username()).pw_gecos)
        else:
            for job in jobs:
                user_names.add(job.username())

        user_names = list(user_names)
        if len(user_names) > 1:
            user_names = ', '.join(user_names[:-1]) + (' and %s' % user_names[-1])
        else:
            user_names = user_names[0]

        to_emails = set()
        for job in jobs:
            to_emails.add("%s@%s" % (job.username(), cuegui.Constants.EMAIL_DOMAIN))

        __default_from = "%s-pst@%s" % (jobs[0].show(), cuegui.Constants.EMAIL_DOMAIN)
        __default_to = ','.join(to_emails)
        __default_cc = "%s-pst@%s" % (jobs[0].show(), cuegui.Constants.EMAIL_DOMAIN)
        __default_bcc = ""

        job_names = list(map(lambda job: job.data.name, jobs))
        if len(job_names) > SUBJ_LINE_TOO_LONG:
            __default_subject = "%s%s" % (cuegui.Constants.EMAIL_SUBJECT_PREFIX,
                                          ','.join(job_names[:2]) + '...')
        else:
            __default_subject = "%s%s" % (cuegui.Constants.EMAIL_SUBJECT_PREFIX,
                                          ','.join(job_names))

        __default_body = "%s%s%s" % (cuegui.Constants.EMAIL_BODY_PREFIX,
                                     ',\n'.join(job_names),
                                     cuegui.Constants.EMAIL_BODY_SUFFIX)
        __default_body += "Hi %s,\n\n" % user_names

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

        # Main Vertical Layout
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

        # pylint: disable=no-member
        self.__btnSend.clicked.connect(self.sendEmail)
        self.__btnCancel.clicked.connect(self.cancel.emit)
        # pylint: enable=no-member

    def giveFocus(self):
        """Initializes widget state when the widget gains focus."""
        self.__email_body.setFocus(QtCore.Qt.OtherFocusReason)
        self.__email_body.moveCursor(QtGui.QTextCursor.Start)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)

    def email_from(self):
        """Gets the email sender."""
        return "%s" % self.__email_from.text()

    def email_to(self):
        """Gets the email recipient."""
        return "%s" % self.__email_to.text()

    def email_cc(self):
        """Gets the email CC field."""
        return "%s" % self.__email_cc.text()

    def email_bcc(self):
        """Gets the email BCC field."""
        return "%s" % self.__email_bcc.text()

    def email_subject(self):
        """Gets the email subject."""
        return "%s" % self.__email_subject.text()

    def email_body(self):
        """Get the email body text."""
        return "%s" % self.__email_body.toPlainText()

    def appendToBody(self, txt):
        """Appends text to the email body."""
        self.__email_body.append(txt)

    def setBody(self, txt):
        """Sets the value of the email body."""
        self.__email_body.setText(txt)

    def sendEmail(self):
        """Sends the email."""
        self.send.emit()

        msg = MIMEText(self.email_body(), 'plain', 'utf-8')
        msg["Subject"] = Header(self.email_subject(), 'utf-8', continuation_ws=' ')
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
