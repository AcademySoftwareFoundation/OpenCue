#!/usr/bin/env python

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

"""Tests for `opencue.wrappers.comment`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import comment_pb2
import opencue.wrappers.comment


TEST_COMMENT_MESSAGE = "hi, I'm a message"


@mock.patch('opencue.cuebot.Cuebot.getStub')
class CommentTests(unittest.TestCase):

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = comment_pb2.CommentDeleteResponse()
        getStubMock.return_value = stubMock

        comment = opencue.wrappers.comment.Comment(
            comment_pb2.Comment(message=TEST_COMMENT_MESSAGE))
        comment.delete()

        stubMock.Delete.assert_called_with(
            comment_pb2.CommentDeleteRequest(comment=comment.data), timeout=mock.ANY)

    def testSave(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Save.return_value = comment_pb2.CommentSaveResponse()
        getStubMock.return_value = stubMock

        comment = opencue.wrappers.comment.Comment(
            comment_pb2.Comment(message=TEST_COMMENT_MESSAGE))
        comment.save()

        stubMock.Save.assert_called_with(
            comment_pb2.CommentSaveRequest(comment=comment.data), timeout=mock.ANY)


if __name__ == '__main__':
    unittest.main()
