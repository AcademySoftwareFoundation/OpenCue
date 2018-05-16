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
Project: Cue3

Module: comment.py - comment object

Created: July 9, 2008

Contact: Middle-Tier Group (middle-tier@imageworks.com)

SVN: $Id$
"""
import cue.CueClientIce as CueClientIce

class _Comment(CueClientIce.Comment):
    """Ice Implementation of Comment Interface"""
    def __init__(self):
        CueClientIce.Comment.__init__(self)

    def delete(self):
        """Delete this comment"""
        self.proxy.delete()

    def save(self):
        """Saves the current comment values"""
        self.proxy.save(self.data)

class Comment(_Comment):
    def __init__(self):
        _Comment.__init__(self)

    def message(self):
        """Message of the comment
        @rtype:  str
        @return: comment message"""
        return self.data.message

    def subject(self):
        """Subject of the comment
        @rtype:  str
        @return: comment subject"""
        return self.data.subject

    def user(self):
        """Returns the username of the user who submitted the comment
        @rtype:  str
        @return: Username of submitter"""
        return self.data.user

    def timestamp(self):
        """Returns the timestamp for the comment as an epoch
        @rtype:  int
        @return: The time the comment was submitted as an epoch"""
        return self.data.timestamp

    def setMessage(self, message):
        """set a new message for the comment
        @type  message: str
        @param message: a new message"""
        self.data.message = message

    def setSubject(self, subject):
        """set a new subject for the comment
        @type  subject: str
        @param subject: a new subject"""
        self.data.subject = subject

