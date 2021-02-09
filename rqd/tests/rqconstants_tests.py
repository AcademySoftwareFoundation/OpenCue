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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import mock
import shutil
import os.path
import tempfile
import unittest

import six

import rqd.rqconstants


if not six.PY2:
    import importlib

    reload = importlib.reload


class MockConfig(object):
    def __init__(self, content):
        self.tempdir = tempfile.mkdtemp()
        config = os.path.join(self.tempdir, "rqd.conf")
        self.patcher = mock.patch("sys.argv", ["rqd", "-c", config])

        with open(config, "w") as f:
            print(content, file=f)

    def __enter__(self):
        self.patcher.start()
        reload(rqd.rqconstants)
        return self

    def __exit__(self, type, value, traceback):
        self.patcher.stop()
        shutil.rmtree(self.tempdir)

    def __call__(self, func):
        def decorator(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return decorator


class RqConstantTests(unittest.TestCase):
    @MockConfig(
        """
[Override]
DEFAULT_FACILITY =  test_facility
"""
    )
    def test_facility(self):
        self.assertEqual(rqd.rqconstants.DEFAULT_FACILITY, "test_facility")

    @MockConfig(
        """
[Override]
RQD_TAGS =  test_tag1 test_tag2  test_tag3
"""
    )
    def test_tags(self):
        self.assertEqual(rqd.rqconstants.RQD_TAGS, "test_tag1 test_tag2  test_tag3")
