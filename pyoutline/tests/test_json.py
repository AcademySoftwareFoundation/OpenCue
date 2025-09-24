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
Tests for the outline.json module.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import unittest
from xml.etree import ElementTree as Et

import mock

import outline
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
                    '"env": {"LAYER_KEY1": "LAYER_VALUE1"}, '
                    '"command": ["/bin/ls"]'
                 '}]'
             '}')

        ol = outline.load_json(s)
        self.assertEqual('test_job', ol.get_name())
        self.assertEqual('1-10', ol.get_frame_range())
        self.assertEqual('LAYER_VALUE1', ol.get_layer('layer_1').get_env('LAYER_KEY1'))

        ol.get_layer('layer_1').set_env('LAYER_KEY2', 'LAYER_VALUE2')

        l = outline.cuerun.OutlineLauncher(ol)
        root = Et.fromstring(l.serialize())
        env1 = root.find('job/layers/layer/env/key[@name="LAYER_KEY1"]')
        self.assertEqual('LAYER_VALUE1', env1.text)
        env2 = root.find('job/layers/layer/env/key[@name="LAYER_KEY2"]')
        self.assertEqual('LAYER_VALUE2', env2.text)

    @mock.patch('outline.layer.Layer.system')
    @mock.patch.dict(os.environ, {}, clear=True)
    def testJsonFile(self, systemMock):
        """Load JSON from a file"""
        with open(os.path.join(JSON_DIR, 'shell.outline'), encoding='utf-8') as fp:
            ol = outline.load_json(fp.read())
        with test_utils.TemporarySessionDirectory():
            ol.setup()
            layer = ol.get_layer('shell_layer')
            self.assertEqual('LAYER_VALUE', layer.get_env('LAYER_KEY'))
            layer.execute('1000')

            systemMock.assert_has_calls([mock.call(['/bin/ls'], frame=1000)])
            self.assertEqual('LAYER_VALUE', os.environ['LAYER_KEY'])

    def testFacility(self):
        """Test facility from JSON"""
        with open(os.path.join(JSON_DIR, 'facility.json'), encoding='utf-8') as fp:
            ol = outline.load_json(fp.read())
            self.assertEqual('test_facility', ol.get_facility())


if __name__ == '__main__':
    unittest.main()
