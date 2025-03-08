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


"""Code for constructing a job submission and sending it to the Cuebot."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
import re

import outline
import outline.cuerun
import outline.modules.shell

from cuesubmit import Constants
from cuesubmit import JobTypes
from cuesubmit import Util


def isSoloFlag(flag):
    """ Check if the flag is solo, meaning it has no associated value
     solo flags are marked with a ~ (ex: --background~)
     """
    return re.match(r"^-+\w+~$", flag)


def isFlag(flag):
    """ Check if the provided string is a flag (starts with a -)"""
    return re.match(r"^-+\w+$", flag)


def formatValue(flag, value, isPath, isMandatory):
    """ Adds quotes around file/folder path variables
     and provide an error value to display for missing mandatory values.
    """
    if isPath and value:
        value = f'"{value}"'
    if isMandatory and value in ('', None):
        value = f'!!missing value for {flag}!!'
    return value


def buildDynamicCmd(layerData):
    """From a layer, builds a customized render command."""
    renderCommand = Constants.RENDER_CMDS[layerData.layerType].get('command')
    for (flag, isPath, isMandatory), value in layerData.cmd.items():
        if isSoloFlag(flag):
            renderCommand += f' {flag[:-1]}'
            continue
        value = formatValue(flag, value, isPath, isMandatory)
        if isFlag(flag) and value not in ('', None):
            # flag and value
            renderCommand += f' {flag} {value}'
            continue
        # solo argument without flag
        if value not in ('', None):
            renderCommand += f' {value}'

    return renderCommand


def buildMayaCmd(layerData, silent=False):
    """From a layer, builds a Maya Render command."""
    camera = layerData.cmd.get('camera')
    mayaFile = layerData.cmd.get('mayaFile')
    if not mayaFile and not silent:
        raise ValueError('No Maya File provided. Cannot submit job.')
    renderCommand = '{renderCmd} -r file -s {frameStart} -e {frameEnd}'.format(
        renderCmd=Constants.MAYA_RENDER_CMD,
        frameStart=Constants.FRAME_START_TOKEN,
        frameEnd=Constants.FRAME_END_TOKEN)
    if camera:
        renderCommand += ' -cam {}'.format(camera)
    renderCommand += ' {}'.format(mayaFile)
    return renderCommand


def buildNukeCmd(layerData, silent=False):
    """From a layer, builds a Nuke Render command."""
    writeNodes = layerData.cmd.get('writeNodes')
    nukeFile = layerData.cmd.get('nukeFile')
    if not nukeFile and not silent:
        raise ValueError('No Nuke file provided. Cannot submit job.')
    renderCommand = '{renderCmd} -F {frameToken} '.format(
        renderCmd=Constants.NUKE_RENDER_CMD, frameToken=Constants.FRAME_TOKEN)
    if writeNodes:
        renderCommand += '-X {} '.format(writeNodes)
    renderCommand += '-x {}'.format(nukeFile)
    return renderCommand


def buildBlenderCmd(layerData, silent=False):
    """From a layer, builds a Blender render command."""
    blenderFile = layerData.cmd.get('blenderFile')
    outputPath = layerData.cmd.get('outputPath')
    outputFormat = layerData.cmd.get('outputFormat')
    frameRange = layerData.layerRange
    if not blenderFile and not silent:
        raise ValueError('No Blender file provided. Cannot submit job.')

    renderCommand = '{renderCmd} -b -noaudio {blenderFile}'.format(
        renderCmd=Constants.BLENDER_RENDER_CMD, blenderFile=blenderFile)
    if outputPath:
        renderCommand += ' -o {}'.format(outputPath)
    if outputFormat:
        renderCommand += ' -F {}'.format(outputFormat)
    if re.match(r"^\d+-\d+$", frameRange):
        # Render frames from start to end (inclusive) via '-a' command argument
        renderCommand += (' -s {startFrame} -e {endFrame} -a'
                          .format(startFrame=Constants.FRAME_START_TOKEN,
                                  endFrame=Constants.FRAME_END_TOKEN))
    else:
        # The render frame must come after the scene and output
        renderCommand += ' -f {frameToken}'.format(frameToken=Constants.FRAME_TOKEN)
    return renderCommand


def buildLayer(layerData, command, lastLayer=None):
    """Creates a PyOutline Layer for the given layerData.

    @type layerData: ui.Layer.LayerData
    @param layerData: layer data from the ui
    @type command: str
    @param command: command to run
    @type lastLayer: outline.layer.Layer
    @param lastLayer: layer that this new layer should be dependent on if dependType is set.
    """
    threadable = False
    if layerData.overrideCores:
        threadable = float(layerData.cores) >= 2 or float(layerData.cores) <= 0
    elif layerData.services and layerData.services[0] in Util.getServices():
        threadable = Util.getServiceOption(layerData.services[0], 'threadable')

    cores = layerData.cores if layerData.overrideCores else None
    layer = outline.modules.shell.Shell(
        layerData.name, command=command.split(), chunk=layerData.chunk,
        cores=cores,
        range=str(layerData.layerRange), threadable=threadable)
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


def buildLayerCommand(layerData, silent=False):
    """Builds the command to be sent per jobType"""
    if layerData.layerType in JobTypes.JobTypes.FROM_CONFIG_FILE:
        command = buildDynamicCmd(layerData)
    elif layerData.layerType == JobTypes.JobTypes.MAYA:
        command = buildMayaCmd(layerData, silent)
    elif layerData.layerType == JobTypes.JobTypes.SHELL:
        command = layerData.cmd.get('commandTextBox') if silent else layerData.cmd['commandTextBox']
    elif layerData.layerType == JobTypes.JobTypes.NUKE:
        command = buildNukeCmd(layerData, silent)
    elif layerData.layerType == JobTypes.JobTypes.BLENDER:
        command = buildBlenderCmd(layerData, silent)
    else:
        if silent:
            command = 'Error: unrecognized layer type {}'.format(layerData.layerType)
        else:
            raise ValueError('unrecognized layer type {}'.format(layerData.layerType))
    return command


def submitJob(jobData):
    """Submits the job using the PyOutline API."""
    ol = outline.Outline(
        jobData['name'], shot=jobData['shot'], show=jobData['show'], user=jobData['username'])
    lastLayer = None
    for layerData in jobData['layers']:
        command = buildLayerCommand(layerData)
        layer = buildLayer(layerData, command, lastLayer)
        ol.add_layer(layer)
        lastLayer = layer

    if 'facility' in jobData:
        ol.set_facility(jobData['facility'])

    return outline.cuerun.launch(ol, use_pycuerun=False)
