#!/usr/bin/env python

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

import base64
import ctypes
import mock
import platform
import unittest

import rqd.rqplatform_windows

# these values dumped from live windows machines:
one_cpu_data = base64.b64decode(b'AwAAADAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQD/DwAAAAAAAAAAAAAAAAAA')
two_cpu_data = base64.b64decode(b'AwAAACwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQD/////AAAAAAAAAAADAAAALAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAP////8AAAAAAAAAAA==')
fake_cpu_data = None  # type: bytes


def _fake_cpu_info(which, buffer, size):
    # type: (ctypes.c_int, ctypes.Array[ctypes.c_byte], ctypes._CArgObject) -> ctypes.c_int
    """A fake version of GetLogicalProcessorInformationEx"""

    # hackery to get underlying byref object:
    actual_size = size._obj  # type: ctypes.c_ulong

    buffer_big_enough = actual_size.value >= len(fake_cpu_data)

    # set size to required buffer size regardless
    ctypes.pointer(actual_size)[0] = ctypes.c_ulong(len(fake_cpu_data))

    if not buffer_big_enough:
        ctypes.windll.kernel32.SetLastError(ctypes.c_ulong(122))  # ERROR_INSUFFICIENT_BUFFER
        return ctypes.c_int(0)  # FALSE
    else:
        # copy data over
        for ix in range(0, len(fake_cpu_data)):
            buffer[ix] = fake_cpu_data[ix]

        return ctypes.c_int(1)  # TRUE


if platform.system() == 'Windows':
    class PlatformWindowsTests(unittest.TestCase):

        def test_can_get_real_processor_count(self):
            """Makes sure the code can run successfully on Windows."""
            self.assertGreater(rqd.rqplatform_windows._getWindowsProcessorCount(), 0)

        @mock.patch.object(
            ctypes.windll.kernel32,
            'GetLogicalProcessorInformationEx',
            _fake_cpu_info)
        def test_can_parse_one_cpu_data_mocked(self):
            """Makes sure that we can parse the canned data and get the expected result"""
            global fake_cpu_data
            fake_cpu_data = one_cpu_data
            self.assertEqual(rqd.rqplatform_windows._getWindowsProcessorCount(), 1)

        @mock.patch.object(
            ctypes.windll.kernel32,
            'GetLogicalProcessorInformationEx',
            _fake_cpu_info)
        def test_can_parse_two_cpu_data_mocked(self):
            """Makes sure that we can parse the canned data and get the expected result"""
            global fake_cpu_data
            fake_cpu_data = two_cpu_data
            self.assertEqual(rqd.rqplatform_windows._getWindowsProcessorCount(), 2)


if __name__ == '__main__':
    unittest.main()
