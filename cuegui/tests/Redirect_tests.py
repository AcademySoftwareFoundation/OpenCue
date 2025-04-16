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


"""Tests for cuegui.Redirect."""


import unittest

import mock
import qtpy.QtCore
import qtpy.QtGui

import opencue_proto.show_pb2

import cuegui.Redirect
import cuegui.Style

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class RedirectTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, getStubMock):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()

        getStubMock.return_value.GetActiveShows.return_value = \
            opencue_proto.show_pb2.ShowGetActiveShowsResponse(
                shows=opencue_proto.show_pb2.ShowSeq(shows=[]))
        getStubMock.return_value.FindShow.return_value = \
            opencue_proto.show_pb2.ShowFindShowResponse(
                show=opencue_proto.show_pb2.Show())

        self.redirect = cuegui.Redirect.RedirectWidget()

    def test_setup(self):
        pass
