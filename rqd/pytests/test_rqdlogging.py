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


"""Pytests for rqd.rqdlogging"""


import mock
import pytest
import opencue_proto.rqd_pb2
from rqd.rqlogging import LokiLogger

@pytest.fixture
@mock.patch('opencue_proto.rqd_pb2_grpc.RunningFrameStub')
@mock.patch('opencue_proto.rqd_pb2_grpc.RqdInterfaceStub')
@mock.patch('grpc.insecure_channel', new=mock.MagicMock())
def runFrame(stubMock, frameStubMock):
    rf = opencue_proto.rqd_pb2.RunFrame()
    rf.job_id = "SD6F3S72DJ26236KFS"
    rf.job_name = "edu-trn_job-name"
    rf.frame_id = "FD1S3I154O646UGSNN"
    return rf

# pylint: disable=redefined-outer-name
def test_LokiLogger(runFrame):
    ll = LokiLogger("http://localhost:3100", runFrame)
    assert isinstance(ll, LokiLogger)

def test_LokiLogger_invalid_runFrame():
    rf = None

    with pytest.raises(AttributeError) as excinfo:
        LokiLogger("http://localhost:3100", rf)
    assert excinfo.type == AttributeError
