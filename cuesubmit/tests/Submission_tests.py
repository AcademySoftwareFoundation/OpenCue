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


import unittest

import cuesubmit.Layer
import cuesubmit.Submission


LAYER_DATA = {
    'name': 'arbitraryLayer_name',
    'layerType': 'randomType',
    'cmd': {'camera': 'renderCam', 'mayaFile': '/path/to/scene.ma'},
    'layerRange': '1-5',
    'cores': '6',
    'env': {'fooKey': 'barVal'},
    'services': ['shell', 'maya'],
    'dependType': cuesubmit.Layer.DependType.Frame,
}


class SubmissionTests(unittest.TestCase):

    def testBuiltMayaLayer(self):
        layer = cuesubmit.Layer.LayerData.buildFactory(**LAYER_DATA)
        cuesubmit.Submission.buildMayaLayer(layer, None)


if __name__ == '__main__':
    unittest.main()
