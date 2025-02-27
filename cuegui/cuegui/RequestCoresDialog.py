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


"""Dialog for a job owner to request more cores for a job or frame(s)."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division


try:
    from email.MIMEText import MIMEText
    from email.MIMEMultipart import MIMEMultipart
    from email.Header import Header
except ImportError:
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.header import Header

import smtplib

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

import cuegui.Constants
import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


class RequestCoresDialog(QtWidgets.QDialog):
    """Dialog for a job owner to request more cores for a job or frame(s)."""

    def __init__(self, job, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.setWindowTitle("Email For: %s" % job.data.name)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.setFixedSize(1000, 800)

        self.__email = EmailCoresWidget(job, self)

        hlayout = QtWidgets.QHBoxLayout(self)
        hlayout.addWidget(self.__email)

        self.__email.giveFocus()

        self.__email.send.connect(self.accept)
        self.__email.cancel.connect(self.reject)


class EmailCoresWidget(QtWidgets.QWidget):
    """Widget for displaying an email form for requesting cores."""

    send = QtCore.Signal()
    cancel = QtCore.Signal()

    def __init__(self, job, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.__job = job

        __default_from = "%s@%s" % (job.username(), cuegui.Constants.EMAIL_DOMAIN)
        __default_to = ""
        __default_cc = []
        if cuegui.Constants.SHOW_SUPPORT_CC_TEMPLATE:
            try:
                for address in cuegui.Constants.SHOW_SUPPORT_CC_TEMPLATE:
                    args = {}
                    # {show} is options
                    # {domain} is mandatory
                    if "{show}" in address:
                        args["show"] = job.show()
                    args["domain"] = cuegui.Constants.EMAIL_DOMAIN

                    __default_cc.append(address.format(**args))
            except KeyError:
                logger.info(
                    "Invalid value on cuegui.Constants.SHOW_SUPPORT_CC_TEMPLATE: %s."
                    "\nSee cuegui.yaml email.show_support_cc_template for the "
                    "pattern documentation", cuegui.Constants.SHOW_SUPPORT_CC_TEMPLATE)

        __default_bcc = ""
        __default_subject = "%s%s" % (
            self.EMAIL_REQUEST_CORES_SUBJECT_PREFIX,
            job.data.name,
        )
        __default_body = "Requesting more cores for: \n"
        __default_body += "Job Name:          %s\nGroup (Folder):  %s\n" % (
            self.__job.name(),
            self.__job.group(),
        )
        __default_body += "\n" + self.EMAIL_REQUEST_CORES_BODY_LAYERS_PREFIX
        __default_body += "\n\nLayer Name\t\tMinimum Memory\tMin Cores"
        for layer in self.__job.getLayers():
            __default_body += "\n%s\t\t%s\t\t%s" % (
                layer.name(),
                layer.minMemory(),
                layer.data.min_cores,
            )

        self.__btnSend = QtWidgets.QPushButton("Send", self)
        self.__btnCancel = QtWidgets.QPushButton("Cancel", self)

        # Body Widgets
        self.__email_body = QtWidgets.QTextEdit(self)
        self.__email_body_user_date_info = QtWidgets.QTextEdit(self)
        self.__email_body_user_date_info.insertPlainText("...your text here...")
        self.__email_body_user_extra_info = QtWidgets.QTextEdit(self)
        self.__email_body_user_extra_info.insertPlainText("...your text here...")
        self.appendToDefaultBody(__default_body)

        spacerItem = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )

        self.__email_from = QtWidgets.QLineEdit(__default_from, self)
        self.__email_to = QtWidgets.QLineEdit(__default_to, self)
        self.__email_cc = QtWidgets.QLineEdit(",".join(__default_cc), self)
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
        vlayout.addWidget(
            QtWidgets.QLabel(self.EMAIL_REQUEST_CORES_USER_DATE_PREFIX, self)
        )
        vlayout.addWidget(self.__email_body_user_date_info)
        vlayout.addWidget(
            QtWidgets.QLabel(self.EMAIL_REQUEST_CORES_USER_ADDITIONAL_PREFIX, self)
        )
        vlayout.addWidget(self.__email_body_user_extra_info)

        # Bottom Horizontal Layout
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addItem(spacerItem)
        hlayout.addWidget(self.__btnSend)
        hlayout.addWidget(self.__btnCancel)
        vlayout.addLayout(hlayout)

        self.__btnSend.clicked.connect(self.sendEmail)
        self.__btnCancel.clicked.connect(self.cancel.emit)

    def giveFocus(self):
        """Initializes widget state when the widget gains focus."""
        self.__email_body.setFocus(QtCore.Qt.OtherFocusReason)
        self.__email_body.moveCursor(QtGui.QTextCursor.Start)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body.moveCursor(QtGui.QTextCursor.Down)

        self.__email_body_user_date_info.setFocus(QtCore.Qt.OtherFocusReason)
        self.__email_body_user_date_info.moveCursor(QtGui.QTextCursor.Start)
        self.__email_body_user_date_info.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body_user_date_info.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body_user_date_info.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body_user_date_info.moveCursor(QtGui.QTextCursor.Down)

        self.__email_body_user_extra_info.setFocus(QtCore.Qt.OtherFocusReason)
        self.__email_body_user_extra_info.moveCursor(QtGui.QTextCursor.Start)
        self.__email_body_user_extra_info.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body_user_extra_info.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body_user_extra_info.moveCursor(QtGui.QTextCursor.Down)
        self.__email_body_user_extra_info.moveCursor(QtGui.QTextCursor.Down)

    def build_html_body(self):
        """Format html body for multipart email."""
        html_body_prefix = self.EMAIL_REQUEST_CORES_USER_HTML_BODY_PREFIX.format(
            self.__job.name(),
            self.__job.group(),
            self.EMAIL_REQUEST_CORES_BODY_LAYERS_PREFIX,
        )
        layers_data = ""
        for layer in self.__job.getLayers():
            layers_data += self.EMAIL_REQUEST_CORES_HTML_BODY_TABLE_LAYERS.format(
                layer.name(), layer.minMemory(), layer.data.min_cores
            )

        date_time_info = self.__email_body_user_date_info.toPlainText()
        extra_info = self.__email_body_user_extra_info.toPlainText()
        html_body = self.EMAIL_REQUEST_CORES_HTML_BODY.format(
            html_body_prefix,
            layers_data,
            self.EMAIL_REQUEST_CORES_USER_DATE_PREFIX,
            date_time_info,
            self.EMAIL_REQUEST_CORES_USER_ADDITIONAL_PREFIX,
            extra_info,
        )

        return html_body

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
        return "%s\n\n%s\n%s" % (
            self.__email_body.toPlainText(),
            self.__email_body_user_date_info.toPlainText(),
            self.__email_body_user_extra_info.toPlainText(),
        )

    def appendToDefaultBody(self, txt):
        """Add information to body the email."""
        self.__email_body.append(txt)
        font = self.__email_body.document().defaultFont()
        fontMetrics = QtGui.QFontMetrics(font)
        textSize = fontMetrics.size(0, txt)
        textHeight = textSize.height() + 30
        textWidth = textSize.width()
        self.__email_body.resize(textWidth, textHeight)

    def appendToAddtionalBody(self, txt):
        """Add additional user provided information to body the email."""
        self.__email_body_user_date_info.append(txt)
        self.__email_body_user_extra_info.append(txt)

    def sendEmail(self):
        """Sends the email."""
        print("build_html_body: ", self.build_html_body())
        self.send.emit()

        message = MIMEMultipart(
            "alternative",
            None,
            [
                MIMEText(self.email_body(), "plain", "utf-8"),
                MIMEText(self.build_html_body(), "html"),
            ],
        )

        message["Subject"] = Header(self.email_subject(), "utf-8", continuation_ws=" ")
        message["To"] = self.email_to()
        message["From"] = self.email_from()
        message["Cc"] = self.email_cc()

        recipient_list = []
        if self.email_to():
            recipient_list.extend(self.email_to().split(","))

        if self.email_cc():
            recipient_list.extend(self.email_cc().split(","))

        if self.email_bcc():
            recipient_list.extend(self.email_bcc().split(","))

        server = smtplib.SMTP("smtp")
        server.sendmail(self.email_from(), recipient_list, message.as_string())
        server.quit()

    EMAIL_REQUEST_CORES_SUBJECT_PREFIX = "Requesting Cores for "
    EMAIL_REQUEST_CORES_BODY_LAYERS_PREFIX = (
        "Layers that have frames remaining (waiting and running): "
    )
    EMAIL_REQUEST_CORES_BODY_LAYER_MINIMUM_MEMORY_CORES = (
        "Layer minimum memory and cores "
    )
    EMAIL_REQUEST_CORES_BODY_LAYER_AVERAGE_CORES = (
        "Layer average core hours per completed frame"
    )
    EMAIL_REQUEST_CORES_USER_DATE_PREFIX = (
        "Add Date/Time by which completion is needed:\n "
    )
    EMAIL_REQUEST_CORES_USER_ADDITIONAL_PREFIX = (
        "Add any additional notes (flag priority frames etc.):\n "
    )
    EMAIL_REQUEST_CORES_HTML_BODY_TABLE_LAYERS = (
        "<tr>\n<td>{0}</td><td>{1}</td><td>{2}</td>\n<tr>\n"
    )
    EMAIL_REQUEST_CORES_USER_HTML_BODY_PREFIX = """
        <p><b>Requesting more cores for:</b></p>
        <table>
        <tr>
            <td>Job Name:</td>
            <td>&nbsp;&nbsp;&nbsp;</td>
            <td>{0}</td>
        </tr>
        <tr>
            <td>Group (Folder)</td>
            <td>&nbsp;&nbsp;&nbsp;</td>
            <td>{1}</td>
        </tr>
        </table>
        <br>
        <b>{2}</b>\n
    """
    EMAIL_REQUEST_CORES_HTML_BODY = """
        <html>
        <body>
        <p>{0}</p>
        <table>
            <tr>
                <td><u>Layer Name</u></td>
                <td><u>Minimum Memory</u></td>
                <td><u>Minimum Cores</u></td>
            </tr>
            {1}
        </table>
        <p><b>{2}</b></p>
        <p>{3}</p>
        <p><b>{4}</b></p>
        <p>{5}</p>
        </body>
        </html>
    """
