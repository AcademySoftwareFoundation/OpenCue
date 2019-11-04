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
    camera = layerData.cmd.get('camera')
    mayaFile = layerData.cmd.get('mayaFile')
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
    writeNodes = layerData.cmd.get('writeNodes')
    nukeFile = layerData.cmd.get('nukeFile')
    if not nukeFile:
        raise ValueError('No Nuke file provided. Cannot submit job.')
    renderCommand = '{renderCmd} -F {frameToken} '.format(
        renderCmd=Constants.NUKE_RENDER_CMD, frameToken=Constants.FRAME_TOKEN)
    if writeNodes:
        renderCommand += '-X {} '.format(writeNodes)
    renderCommand += '-x {}'.format(nukeFile)
    return renderCommand

def buildBlenderCmd(layerData):
    """From a layer, build a Blender render command."""
    blenderFile = layerData.cmd.get('blenderFile')
    outputPath = layerData.cmd.get('outputPath')
    outputFormat = layerData.cmd.get('outputFormat')
    if not blenderFile:
        raise ValueError('No Blender file provided. Cannot submit job.')
    
    renderCommand = '{renderCmd} -b -noaudio {blenderFile}'.format(
        renderCmd=Constants.BLENDER_RENDER_CMD, blenderFile=blenderFile)
    if outputPath:
        renderCommand += ' -o {}'.format(outputPath)
    if outputFormat:
        renderCommand += ' -F {}'.format(outputFormat)
    # The render frame must come after the scene and output
    renderCommand += ' -f {frameToken}'.format(frameToken=Constants.FRAME_TOKEN)
    return renderCommand


def buildLayer(layerData, command, lastLayer=None):
    """Create a PyOutline Layer for the given layerData.
    @type layerData: ui.Layer.LayerData
    @param layerData: layer data from the ui
    @type command: str
    @param command: command to run
    @type lastLayer: outline.layer.Layer
    @param lastLayer: layer that this new layer should be dependent on if dependType is set.
    """
    if float(layerData.cores) >= 2:
        threadable = True
    else:
        threadable = False
    layer = Shell(layerData.name, command=command.split(), chunk=layerData.chunk,
                  threads=float(layerData.cores), range=str(layerData.layerRange),
                  threadable=threadable)
    if layerData.services:
        layer.set_service(layerData.services[0])
    if layerData.limits:
        layer.set_limits(layerData.limits)
    if layerData.dependType and lastLayer:
        if layerData.dependType == 'Layer':
            layer.depend_all(lastLayer)
        else:
            layer.depend_on(lastLayer)
    return layer


def buildMayaLayer(layerData, lastLayer):
    mayaCmd = buildMayaCmd(layerData)
    return buildLayer(layerData, mayaCmd, lastLayer)


def buildNukeLayer(layerData, lastLayer):
    nukeCmd = buildNukeCmd(layerData)
    return buildLayer(layerData, nukeCmd, lastLayer)


def buildBlenderLayer(layerData, lastLayer):
    blenderCmd = buildBlenderCmd(layerData)
    return buildLayer(layerData, blenderCmd, lastLayer)

def buildShellLayer(layerData, lastLayer):
    return buildLayer(layerData, layerData.cmd['commandTextBox'], lastLayer)


def submitJob(jobData):
    """Submit the job using the PyOutline API."""
    outline = Outline(jobData['name'], shot=jobData['shot'], show=jobData['show'],
                      user=jobData['username'])
    lastLayer = None
    for layerData in jobData['layers']:
        if layerData.layerType == JobTypes.JobTypes.MAYA:
            layer = buildMayaLayer(layerData, lastLayer)
        elif layerData.layerType == JobTypes.JobTypes.SHELL:
            layer = buildShellLayer(layerData, lastLayer)
        elif layerData.layerType == JobTypes.JobTypes.NUKE:
            layer = buildNukeLayer(layerData, lastLayer)
        elif layerData.layerType == JobTypes.JobTypes.BLENDER:
            layer = buildBlenderLayer(layerData, lastLayer)
        else:
            raise ValueError('unrecognized layer type %s' % layerData.layerType)
        outline.add_layer(layer)
        lastLayer = layer
    return cuerun.launch(outline, use_pycuerun=False)
