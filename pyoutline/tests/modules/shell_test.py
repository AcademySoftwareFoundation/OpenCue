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
Tests for the outline.modules.shell module.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import range

import tempfile
import unittest

import mock

from FileSequence import FrameSet
import outline
import outline.modules.shell
from .. import test_utils


class ShellModuleTest(unittest.TestCase):

    """Shell Module Tests"""

    def setUp(self):
        outline.Outline.current = None

    @mock.patch('outline.layer.Layer.system')
    def testShell(self, systemMock):
        """Test a simple shell command."""

        command = ['/bin/ls']

        shell = outline.modules.shell.Shell('bah', command=command)
        shell._execute(FrameSet('5-6'))

        systemMock.assert_has_calls([
            mock.call(command, frame=5),
            mock.call(command, frame=6),
        ])

    @mock.patch('outline.layer.Layer.system')
    def testShellSequence(self, systemMock):
        """Test a simple sequence of shell commands"""

        commandCount = 10
        commands = ['/bin/echo %d' % (frame+1) for frame in range(commandCount)]

        shellSeq = outline.modules.shell.ShellSequence(
            'bah', commands=commands, cores=10, memory='512m')
        shellSeq._execute(FrameSet('5-6'))

        self.assertEqual('1-%d' % commandCount, shellSeq.get_frame_range())
        systemMock.assert_has_calls([
            mock.call('/bin/echo 5'),
            mock.call('/bin/echo 6'),
        ])

    @mock.patch('outline.layer.Layer.system')
    def testShellScript(self, systemMock):
        """Test a custom shell script layer"""

        # The script will be copied into the session directory so we have to create a dummy
        # session to use.

        layerName = 'arbitrary-layer'

        with test_utils.TemporarySessionDirectory(), tempfile.NamedTemporaryFile() as scriptFile:

            scriptContents = '# !/bin/sh\necho zoom zoom zoom'

            with open(scriptFile.name, 'w', encoding='utf-8') as fp:
                fp.write(scriptContents)

            outln = outline.Outline()
            outln.setup()
            expectedSessionPath = outln.get_session().put_file(
                scriptFile.name, layer=layerName, rename='script')

            shellScript = outline.modules.shell.ShellScript(layerName, script=scriptFile.name)
            shellScript.set_outline(outln)
            shellScript._setup()
            shellScript._execute(FrameSet('5-6'))

            with open(expectedSessionPath, encoding='utf-8') as fp:
                sessionScriptContents = fp.read()

            self.assertEqual(scriptContents, sessionScriptContents)
            systemMock.assert_has_calls([mock.call(expectedSessionPath, frame=5)])

    @mock.patch('outline.layer.Layer.system')
    def testShellToString(self, systemMock):
        """Test a string shell command."""

        command = '/bin/ls -l ./'

        shell = outline.modules.shell.Shell('bah', command=command)
        shell._execute(FrameSet('5-6'))

        systemMock.assert_has_calls([
            mock.call(command, frame=5),
            mock.call(command, frame=6),
        ])


if __name__ == '__main__':
    unittest.main()
