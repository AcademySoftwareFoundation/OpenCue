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


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import mock
import os
import unittest

from outline import load_json
from . import test_utils


JSON_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'json')


class JsonTest(unittest.TestCase):

    def testJson(self):
        """Load in a json string"""
        s = ('{'
                 '"name": "test_job", '
                 '"range": "1-10", '
                 '"layers": [{'
                    '"name": "layer_1", '
                    '"module": "outline.modules.shell.Shell", '
                    '"command": ["/bin/ls"]'
                 '}]'
             '}')

        ol = load_json(s)
        self.assertEqual('test_job', ol.get_name())
        self.assertEqual('1-10', ol.get_frame_range())

    @mock.patch('outline.layer.Layer.system')
    def testJsonFile(self, systemMock):
        """Load JSON from a file"""
        with open(os.path.join(JSON_DIR, 'shell.outline')) as fp:
            ol = load_json(fp.read())
        with test_utils.TemporarySessionDirectory():
            ol.setup()
            ol.get_layer('shell_layer').execute('1000')

            systemMock.assert_has_calls([mock.call(['/bin/ls'], frame=1000)])


if __name__ == '__main__':
    unittest.main()
