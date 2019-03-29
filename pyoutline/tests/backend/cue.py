#!/usr/local64/bin/python2.5

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


import os
import unittest

from xml.etree import ElementTree as Et

import outline
import outline.backend.cue


SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')


class SerializeTest(unittest.TestCase):
    def testSerializeShellOutline(self):
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        ol = outline.load_outline(path)
        launcher = outline.cuerun.OutlineLauncher(ol)
        outlineXml = outline.backend.cue.serialize(launcher)

        expectedXml = ('<?xml version="1.0"?>'
                       '<!DOCTYPE spec PUBLIC "SPI Cue  Specification Language" "http://localhost:8080/spcue/dtd/cjsl-1.8.dtd">'
                       '<spec>'
                         '<facility>local</facility>'
                         '<show>testing</show>'
                         '<shot>default</shot>'
                         '<user>cipriano</user>'
                         '<email>cipriano@example.com</email>'
                         '<uid>272943</uid>'
                         '<job name="shell">'
                           '<paused>False</paused>'
                           '<maxretries>2</maxretries>'
                           '<autoeat>False</autoeat>'
                           '<env />'
                           '<layers>'
                             '<layer name="cmd" type="Render">'
                               '<cmd>/wrappers/opencue_wrap_frame  /bin/pycuerun /Users/cipriano/opencue/pyoutline/tests/backend/../scripts/shell.outline -e #IFRAME#-cmd  --version latest  --repos  --debug</cmd>'
                               '<range>1000-1000</range>'
                               '<chunk>1</chunk>'
                               '<services><service>shell</service></services>'
                             '</layer>'
                           '</layers>'
                         '</job>'
                         '<depends />'
                       '</spec>')

        self.assertEqual(expectedXml, outlineXml)


if __name__ == '__main__':
    unittest.main()

