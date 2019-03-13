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


import mock
import os
import shutil
import tempfile
import unittest

from FileSequence import FrameSet
import outline
from outline.loader import Outline
from outline.modules.shell import Shell
from outline.modules.shell import ShellSequence
from outline.modules.shell import ShellScript
from tests.test_utils import TemporarySessionDirectory


class ShellModuleTest(unittest.TestCase):

    """Shell Module Tests"""

    @mock.patch('outline.layer.Layer.system')
    def testShell(self, systemMock):
        """Test a simple shell command."""

        command = ['/bin/ls']

        shell = Shell('bah', command=command)
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

        shellSeq = ShellSequence('bah', commands=commands, cores=10, memory='512m')
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

        with TemporarySessionDirectory(), tempfile.NamedTemporaryFile() as scriptFile:

            scriptContents = '# !/bin/sh\necho zoom zoom zoom'

            with open(scriptFile.name, 'w') as fp:
                fp.write(scriptContents)

            outln = Outline()
            outln.setup()
            expectedSessionPath = outln.get_session().put_file(
                scriptFile.name, layer=layerName, rename='script')

            shellScript = ShellScript(layerName, script=scriptFile.name)
            shellScript.set_outline(outln)
            shellScript._setup()
            shellScript._execute(FrameSet('5-6'))

            with open(expectedSessionPath) as fp:
                sessionScriptContents = fp.read()

            self.assertEqual(scriptContents, sessionScriptContents)
            systemMock.assert_has_calls([mock.call(expectedSessionPath, frame=5)])

    @mock.patch('outline.layer.Layer.system')
    def testShellToString(self, systemMock):
        """Test a string shell command."""

        command = '/bin/ls -l ./'

        shell = Shell('bah', command=command)
        shell._execute(FrameSet('5-6'))

        systemMock.assert_has_calls([
            mock.call(command, frame=5),
            mock.call(command, frame=6),
        ])


if __name__ == '__main__':
    unittest.main()

