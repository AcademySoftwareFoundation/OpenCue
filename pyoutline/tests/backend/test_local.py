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

"""
Tests for the outline_backend_local module.
"""

import os
import unittest

import mock

import outline
import outline.cuerun
import outline_backend_local


SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts'))


class BuildCommandTest(unittest.TestCase):
    def setUp(self):
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        outline.config.set('outline', 'home', '')
        outline.config.set('outline', 'user_dir', '')
        self.ol = outline.load_outline(path)
        self.launcher = outline.cuerun.OutlineLauncher(self.ol)
        self.layer = self.ol.get_layer('cmd')

    def testBuildShellCommand(self):
        frameNum = 47

        generatedCmd = outline_backend_local.build_command(self.ol, self.layer, frameNum)

        self.assertEqual(
            [
                '/wrappers/local_wrap_frame', '', 'testing', 'default', '/bin/pycuerun',
                '%s/shell.outline -e  %d-cmd' % (SCRIPTS_DIR, frameNum), ' -v latest',
                ' -r ', '-D'
            ], generatedCmd)


class SerializeTest(unittest.TestCase):
    def setUp(self):
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        self.ol = outline.load_outline(path)
        self.launcher = outline.cuerun.OutlineLauncher(self.ol)

    def testSerialize(self):
        self.assertEqual(
            outline_backend_local.Dispatcher,
            outline_backend_local.serialize(self.launcher).__class__)

    def testSerializeSimple(self):
        self.assertEqual(
            outline_backend_local.Dispatcher,
            outline_backend_local.serialize_simple(self.launcher).__class__)


class BuildFrameRangeTest(unittest.TestCase):
    def testBuildFrameRange(self):
        self.assertEqual([3, 4, 5, 6, 7, 8, 9], outline_backend_local.build_frame_range('3-9', 1))

    def testBuildChunkedFrameRange(self):
        self.assertEqual([3, 7], outline_backend_local.build_frame_range('3-9', 4))

    def testBuildLargeChunkedFrameRange(self):
        self.assertEqual([3], outline_backend_local.build_frame_range('3-9', 87))


class DispatcherTest(unittest.TestCase):
    @mock.patch('subprocess.call')
    def testDispatch(self, subprocessCallMock):
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        ol = outline.load_outline(path)
        launcher = outline.cuerun.OutlineLauncher(ol)
        subprocessCallMock.return_value = 0

        outline_backend_local.launch(launcher)

class BackendOverrideTest(unittest.TestCase):

    def setUp(self):
        outline.Outline.current = None

    def testOverrideBackendWithEnvVar(self):
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        ol = outline.load_outline(path)

        outline.config.set('outline', 'backend', 'local')

        launcher = outline.cuerun.OutlineLauncher(ol)

        # Check that the backend configured on the launcher matches
        self.assertEqual('local', launcher.get('backend'))
        self.assertEqual('local', launcher.get_flag('backend'))

        # Check that the imported backend module resolves to the rest backend
        backend_module = outline.cuerun.import_backend_module(launcher.get('backend'))
        self.assertIs(outline_backend_local, backend_module)


if __name__ == '__main__':
    unittest.main()
