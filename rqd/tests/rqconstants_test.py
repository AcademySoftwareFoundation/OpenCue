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


"""Tests for rqd.rqconstants."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os.path
import shutil
import tempfile
import uuid
import importlib

import mock
import pyfakefs.fake_filesystem_unittest

import opencue_proto.report_pb2
import rqd.rqconstants
import rqd.rqcore
import rqd.rqmachine
import rqd.rqnimby
import rqd.rqutil

from .rqmachine_test import (
    CPUINFO,
    LOADAVG_LOW_USAGE,
    MEMINFO_MODERATE_USAGE,
    PROC_STAT,
)


class MockConfig(object):
    def __init__(self, tempdir, content):
        config = os.path.join(tempdir, str(uuid.uuid4()))
        self.patcher = mock.patch("sys.argv", ["rqd", "-c", config])

        with open(config, "w", encoding='utf-8') as f:
            print(content, file=f)

    def __enter__(self):
        self.patcher.start()
        importlib.reload(rqd.rqconstants)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.patcher.stop()

    def __call__(self, func):
        def decorator(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return decorator


@mock.patch("subprocess.getoutput", new=mock.MagicMock(return_value=""))
@mock.patch.object(
    rqd.rqutil.Memoize, "isCached", new=mock.MagicMock(return_value=False)
)
@mock.patch("platform.system", new=mock.MagicMock(return_value="Linux"))
@mock.patch("os.statvfs", new=mock.MagicMock())
@mock.patch(
    "rqd.rqutil.getHostname", new=mock.MagicMock(return_value="arbitrary-hostname")
)
class RqConstantTests(pyfakefs.fake_filesystem_unittest.TestCase):

    tempdir = tempfile.mkdtemp()

    def setUp(self):
        self.setUpPyfakefs()
        self.fs.add_real_directory(self.tempdir)
        self.fs.create_file("/proc/cpuinfo", contents=CPUINFO)
        self.loadavg = self.fs.create_file("/proc/loadavg", contents=LOADAVG_LOW_USAGE)
        self.procStat = self.fs.create_file("/proc/stat", contents=PROC_STAT)
        self.meminfo = self.fs.create_file(
            "/proc/meminfo", contents=MEMINFO_MODERATE_USAGE
        )

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def makeRqMachine(self):
        rqCore = mock.MagicMock(spec=rqd.rqcore.RqCore)
        nimby = mock.MagicMock(spec=rqd.rqnimby.Nimby)
        rqCore.nimby = nimby
        nimby.is_ready = False
        nimby.locked = False
        coreDetail = opencue_proto.report_pb2.CoreDetail(total_cores=2)
        machine = rqd.rqmachine.Machine(rqCore, coreDetail)

        machine.renderHost = machine.__dict__["_Machine__renderHost"]

        return machine

    @MockConfig(
        tempdir,
        """
[Override]
DEFAULT_FACILITY =  test_facility
RQD_TAGS =  test_tag1 test_tag2  test_tag3
""",
    )
    def test_facility(self):
        self.assertEqual(rqd.rqconstants.DEFAULT_FACILITY, "test_facility")

        machine = self.makeRqMachine()
        self.assertEqual(machine.renderHost.facility, "test_facility")
        self.assertTrue(
            set(["test_tag1", "test_tag2", "test_tag3"]).issubset(
                machine.renderHost.tags
            )
        )
