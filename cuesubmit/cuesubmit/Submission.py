
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
        renderCmd=Constants.RENDER_CMD, frameToken=Constants.FRAME_TOKEN)
    if camera:
        renderCommand += ' -cam {}'.format(camera)
    renderCommand += ' {}'.format(mayaFile)
    return renderCommand


def buildLayer(layerData, command):
    """Create a PyOutline Layer for the given layerData.
    @type layerData: ui.Layer.LayerData
    @param layerData: layer data from the ui
    @type command: str
    @param command: command to run
    """
    layer = Shell(layerData.name, command=command.split(), chunk=layerData.chunks,
                  threads=layerData.cores, range=layerData.layerRange)
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
    return buildLayer(layerData, layerData.cmd)


def buildShellLayer(layerData):
    return buildLayer(layerData, layerData.cmd)


def submitJob(jobData):
    """Submit the job using the PyOutline API."""
    outline = Outline(jobData.name)
    for layerData in jobData['layers']:
        if layerData.layerType == JobTypes.JobTypes.MAYA:
            layer = buildMayaLayer(layerData)
        elif layerData.layerType == JobTypes.JobTypes.SHELL:
            layer = buildShellLayer(layerData)
        elif layerData.layerType == JobTypes.JobTypes.NUKE:
            layer = buildNukeLayer(layerData)
        outline.addLayer(layer)
    cuerun.launch(outline)
