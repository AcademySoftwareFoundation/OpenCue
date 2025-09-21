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


"""Tests for cuesubmit.Layer"""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import unittest

import cuesubmit.Layer


LAYER_DATA = {
    'name': 'arbitraryLayer_name',
    'layerType': 'randomType',
    'cmd': 'echo #IFRAME#',
    'layerRange': '1-5',
    'limits': [],
    'overrideCores': True,
    'cores': '6',
    'env': {'fooKey': 'barVal'},
    'services': ['shell', 'maya'],
    'dependType': cuesubmit.Layer.DependType.Frame,
}


class LayerTests(unittest.TestCase):

    def testFactoryAndUpdate(self):
        layer = cuesubmit.Layer.LayerData.buildFactory(**LAYER_DATA)

        self.assertEqual('arbitraryLayer_name', layer.name)
        self.assertEqual('randomType', layer.layerType)
        self.assertEqual('echo #IFRAME#', layer.cmd)
        self.assertEqual('1-5', layer.layerRange)
        self.assertEqual(True, layer.overrideCores)
        self.assertEqual('6', layer.cores)
        self.assertEqual('1', layer.chunk)
        self.assertEqual(None, layer.dependsOn)

    def testFactoryAndToDict(self):
        layer = cuesubmit.Layer.LayerData.buildFactory(**LAYER_DATA)

        expectedLayerData = LAYER_DATA.copy()
        expectedLayerData['chunk'] = '1'
        expectedLayerData['dependsOn'] = None

        self.assertEqual(expectedLayerData, layer.toDict())


if __name__ == '__main__':
    unittest.main()
