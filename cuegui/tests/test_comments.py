#  Copyright (c) OpenCue Project Authors
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


"""Tests for cuegui.Comments."""


import time
import unittest

import mock

from qtpy import QtCore
from qtpy import QtWidgets

import opencue_proto.comment_pb2
import opencue_proto.job_pb2
import opencue.wrappers.comment
import opencue.wrappers.job

import cuegui.Comments
import cuegui.Style

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class CommentsTests(unittest.TestCase):
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, getStubMock):
        app = test_utils.createApplication()
        app.settings = QtCore.QSettings()
        cuegui.Style.init()

        commentProto = opencue_proto.comment_pb2.Comment(
            id='comment-id-1', timestamp=int(time.time()), user='user-who-made-comment',
            subject='comment-subject', message='this is the comment message body')
        self.comment = opencue.wrappers.comment.Comment(commentProto)
        getStubMock.return_value.GetComments.return_value = \
            opencue_proto.job_pb2.JobGetCommentsResponse(
                comments=opencue_proto.comment_pb2.CommentSeq(comments=[commentProto]))

        self.job_name = "fooJob"
        self.job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name=self.job_name))
        self.parentWidget = QtWidgets.QWidget()
        self.commentListDialog = cuegui.Comments.CommentListDialog(
            [self.job], parent=self.parentWidget)

    def test_shouldDisplayComment(self):
        self.assertEqual(
            1, self.commentListDialog._CommentListDialog__treeSubjects.topLevelItemCount())
        comments_per_job = self.commentListDialog.getComments()
        comment = comments_per_job[self.job_name][0]
        self.assertEqual(self.comment.timestamp(), comment.timestamp())
        self.assertEqual(self.comment.user(), comment.user())
        self.assertEqual(self.comment.subject(), comment.subject())
        self.assertEqual(self.comment.message(), comment.message())

    def test_shouldRefreshJobComments(self):
        self.job.getComments = mock.Mock(return_value=[])

        self.commentListDialog.refreshComments()

        self.job.getComments.assert_called()
