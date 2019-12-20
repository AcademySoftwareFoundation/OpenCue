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
Project: opencue

Module: comment.py - comment object

"""

from opencue.compiled_proto import comment_pb2
from opencue.cuebot import Cuebot


class Comment(object):
    """This class contains the grpc implementation related to a Comment."""

    def __init__(self, comment=None):
        self.data = comment
        self.stub = Cuebot.getStub('comment')

    def delete(self):
        """Delete this comment"""
        self.stub.Delete(comment_pb2.CommentDeleteRequest(comment=self.data), timeout=Cuebot.Timeout)

    def save(self):
        """Saves the current comment values"""
        self.stub.Save(comment_pb2.CommentSaveRequest(comment=self.data), timeout=Cuebot.Timeout)

    def message(self):
        """Message of the comment

        :rtype:  str
        :return: comment message"""
        return self.data.message

    def subject(self):
        """Subject of the comment

        :rtype:  str
        :return: comment subject"""
        return self.data.subject

    def user(self):
        """Returns the username of the user who submitted the comment.

        :rtype:  str
        :return: Username of submitter"""
        return self.data.user

    def timestamp(self):
        """Returns the timestamp for the comment as an epoch.

        :rtype:  int
        :return: The time the comment was submitted as an epoch"""
        return self.data.timestamp

    def setMessage(self, message):
        """Set a new message for the comment.

        :type  message: str
        :param message: a new message"""
        self.data.message = message

    def setSubject(self, subject):
        """Set a new subject for the comment.

        :type  subject: str
        :param subject: a new subject"""
        self.data.subject = subject

