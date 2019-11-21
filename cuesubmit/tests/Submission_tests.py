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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import mock
import unittest

import cuesubmit.JobTypes
import cuesubmit.Layer
import cuesubmit.Submission
import outline.depend


MAYA_LAYER_DATA = {
    'name': 'arbitraryMayaLayer_name',
    'layerType': cuesubmit.JobTypes.JobTypes.MAYA,
    'cmd': {'camera': 'renderCam', 'mayaFile': '/path/to/scene.ma'},
    'layerRange': '1-5',
    'cores': '6',
    'services': ['maya', 'foo'],
}

NUKE_LAYER_DATA = {
    'name': 'arbitraryNukeLayer_name',
    'layerType': cuesubmit.JobTypes.JobTypes.NUKE,
    'cmd': {'writeNodes': 'Write1,Write2', 'nukeFile': '/path/to/script.nk'},
    'layerRange': '17-124',
    'cores': '1',
    'services': ['nuke'],
}

SHELL_LAYER_DATA = {
    'name': 'arbitraryShellLayer_name',
    'layerType': cuesubmit.JobTypes.JobTypes.SHELL,
    'cmd': {'commandTextBox': 'echo #IFRAME#'},
    'layerRange': '6-10',
    'cores': '1',
    'services': ['shell'],
    'dependType': cuesubmit.Layer.DependType.Frame,
}


@mock.patch('outline.cuerun.launch')
class SubmissionTests(unittest.TestCase):

    def testSubmitMayaJob(self, launchMock):
        cuesubmit.Submission.submitJob({
            'name': 'arbitrary-maya-job',
            'shot': 'arbitrary-shot-name',
            'show': 'arbitrary-show-name',
            'username': 'arbitrary-user',
            'layers': [cuesubmit.Layer.LayerData.buildFactory(**MAYA_LAYER_DATA)],
        })

        outline = launchMock.call_args[0][0]
        self.assertEqual(1, len(outline.get_layers()))
        layer = outline.get_layer(MAYA_LAYER_DATA['name'])
        self.assertEqual(MAYA_LAYER_DATA['name'], layer.get_name())
        self.assertEqual(
            [
                'Render', '-r', 'file', '-s', '#IFRAME#', '-e', '#IFRAME#', '-cam',
                MAYA_LAYER_DATA['cmd']['camera'], MAYA_LAYER_DATA['cmd']['mayaFile']
            ],
            layer.get_arg('command')
        )
        self.assertEqual(MAYA_LAYER_DATA['layerRange'], layer.get_frame_range())
        self.assertEqual('maya', layer.get_service())

    def testSubmitNukeJob(self, launchMock):
        cuesubmit.Submission.submitJob({
            'name': 'arbitrary-nuke-job',
            'shot': 'arbitrary-shot-name',
            'show': 'arbitrary-show-name',
            'username': 'arbitrary-user',
            'layers': [cuesubmit.Layer.LayerData.buildFactory(**NUKE_LAYER_DATA)],
        })

        outline = launchMock.call_args[0][0]
        self.assertEqual(1, len(outline.get_layers()))
        layer = outline.get_layer(NUKE_LAYER_DATA['name'])
        self.assertEqual(NUKE_LAYER_DATA['name'], layer.get_name())
        self.assertEqual(
            [
                'nuke', '-F', '#IFRAME#', '-X', NUKE_LAYER_DATA['cmd']['writeNodes'],
                '-x', NUKE_LAYER_DATA['cmd']['nukeFile']
            ],
            layer.get_arg('command')
        )
        self.assertEqual(NUKE_LAYER_DATA['layerRange'], layer.get_frame_range())
        self.assertEqual('nuke', layer.get_service())

    def testSubmitMayaAndShellJob(self, launchMock):
        cuesubmit.Submission.submitJob({
            'name': 'arbitrary-maya-shell-job',
            'shot': 'arbitrary-shot-name',
            'show': 'arbitrary-show-name',
            'username': 'arbitrary-user',
            'layers': [
                cuesubmit.Layer.LayerData.buildFactory(**MAYA_LAYER_DATA),
                cuesubmit.Layer.LayerData.buildFactory(**SHELL_LAYER_DATA)
            ],
        })

        ol = launchMock.call_args[0][0]
        self.assertEqual(2, len(ol.get_layers()))

        mayaLayer = ol.get_layer(MAYA_LAYER_DATA['name'])
        self.assertEqual(MAYA_LAYER_DATA['name'], mayaLayer.get_name())
        self.assertEqual(
            [
                'Render', '-r', 'file', '-s', '#IFRAME#', '-e', '#IFRAME#', '-cam',
                MAYA_LAYER_DATA['cmd']['camera'], MAYA_LAYER_DATA['cmd']['mayaFile']
            ],
            mayaLayer.get_arg('command')
        )
        self.assertEqual(MAYA_LAYER_DATA['layerRange'], mayaLayer.get_frame_range())
        self.assertEqual('maya', mayaLayer.get_service())

        shellLayer = ol.get_layer(SHELL_LAYER_DATA['name'])
        self.assertEqual(SHELL_LAYER_DATA['name'], shellLayer.get_name())
        self.assertEqual(['echo', '#IFRAME#'], shellLayer.get_arg('command'))
        self.assertEqual(SHELL_LAYER_DATA['layerRange'], shellLayer.get_frame_range())
        self.assertEqual('shell', shellLayer.get_service())
        self.assertEqual(1, len(shellLayer.get_depends()))

        depend = shellLayer.get_depends()[0]
        self.assertEqual(mayaLayer, depend.get_depend_on_layer())
        self.assertEqual(shellLayer, depend.get_dependant_layer())
        self.assertEqual(outline.depend.DependType.FrameByFrame, depend.get_type())


if __name__ == '__main__':
    unittest.main()
