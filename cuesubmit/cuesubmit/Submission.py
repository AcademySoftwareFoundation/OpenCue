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


from outline import Outline, cuerun
from outline.modules.shell import Shell

from cuesubmit import Constants
from cuesubmit import JobTypes


def buildMayaCmd(layerData):
    """From a layer, build a Maya Render command."""
    camera = layerData.get('camera')
    mayaFile = layerData.get('mayaFile')
    if not mayaFile:
        raise ValueError('No Maya File provided. Cannot submit job.')
    renderCommand = '{renderCmd} -r file -s {frameToken} -e {frameToken}'.format(
        renderCmd=Constants.MAYA_RENDER_CMD, frameToken=Constants.FRAME_TOKEN)
    if camera:
        renderCommand += ' -cam {}'.format(camera)
    renderCommand += ' {}'.format(mayaFile)
    return renderCommand


def buildNukeCmd(layerData):
    """From a layer, build a Nuke Render command."""
    writeNodes = layerData.get('writeNodes')
    nukeFile = layerData.get('nukeFile')
    if not nukeFile:
        raise ValueError('No Nuke file provided. Cannot submit job.')
    renderCommand = '{renderCmd} -F {frameToken} '.format(
        renderCmd=Constants.NUKE_RENDER_CMD, frameToken=Constants.FRAME_TOKEN)
    if writeNodes:
        renderCommand += '-X {} '.format(writeNodes)
    renderCommand += '-x {}'.format(nukeFile)
    return renderCommand


def buildLayer(layerData, command):
    """Create a PyOutline Layer for the given layerData.
    @type layerData: ui.Layer.LayerData
    @param layerData: layer data from the ui
    @type command: str
    @param command: command to run
    """
    layer = Shell(layerData.name, command=command.split(), chunk=layerData.chunk,
                  threads=float(layerData.cores), range=str(layerData.layerRange))
    if layerData.dependType and layerData.dependsOn:
        if layerData.dependType == 'Layer':
            layer.depend_all(layerData.dependsOn)
        else:
            layer.depend_all(layerData.dependsOn)
    return layer


def buildMayaLayer(layerData):
    mayaCmd = buildMayaCmd(layerData)
    return buildLayer(layerData, mayaCmd)


def buildNukeLayer(layerData):
    nukeCmd = buildNukeCmd(layerData)
    return buildLayer(layerData, nukeCmd)


def buildShellLayer(layerData):
    return buildLayer(layerData, layerData.cmd['commandTextBox'])


def submitJob(jobData):
    """Submit the job using the PyOutline API."""
    outline = Outline(jobData['name'])
    for layerData in jobData['layers']:
        if layerData.layerType == JobTypes.JobTypes.MAYA:
            layer = buildMayaLayer(layerData)
        elif layerData.layerType == JobTypes.JobTypes.SHELL:
            layer = buildShellLayer(layerData)
        elif layerData.layerType == JobTypes.JobTypes.NUKE:
            layer = buildNukeLayer(layerData)
        outline.add_layer(layer)
    return cuerun.launch(outline, use_pycuerun=False)
