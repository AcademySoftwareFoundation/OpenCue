
import outline
import outline.cuerun
import outline.modules.shell

import bpy

def buildBlenderCmd(layerData):
    blenderFile = layerData.get('cmd').get('blenderFile')
    outputPath = layerData.get('cmd').get('outputPath')
    outputFormat = layerData.get('cmd').get('outputFormat')

    # Hardware use for rendering
    addon_prefs = bpy.context.preferences.addons['OpenCue'].preferences
    use_gpu = addon_prefs.use_gpu
    if use_gpu:
        renderHW = "CUDA"
    else:
        renderHW = "CPU"

    if not blenderFile:
        raise ValueError('No Blender file provided. Cannot submit job.')

    renderCommand = '{renderCmd} -b -noaudio {blenderFile} -E CYCLES -- --cycles-device {renderHW}'.format(
        renderCmd="blender", blenderFile=blenderFile, renderHW=renderHW)
    if outputPath:
        renderCommand += ' -o {}'.format(outputPath)
    if outputFormat:
        renderCommand += ' -F {}'.format(outputFormat)
    # The render frame must come after the scene and output
    renderCommand += ' -f {frameToken}'.format(frameToken="#IFRAME#")
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
    threadable = float(layerData.get('cores')) >= 2
    layer = outline.modules.shell.Shell(
        layerData.get('name'), command=command.split(), chunk=layerData.get('chunk'),
        threads=float(layerData.get('cores')), range=str(layerData.get('layerRange')), threadable=threadable)
    if layerData.get('services'):
        layer.set_service(layerData.services[0])
    if layerData.get('limits'):
        layer.set_limits(layerData.limits)
    if layerData.get('dependType') and lastLayer:
        if layerData.dependType == 'Layer':
            layer.depend_all(lastLayer)
        else:
            layer.depend_on(lastLayer)
    return layer

def buildBlenderLayer(layerData, lastLayer):
    """Builds a PyOutline layer running a Blender command."""
    blenderCmd = buildBlenderCmd(layerData)
    return buildLayer(layerData, blenderCmd, lastLayer)

def submit(jobData):
    """Submits the job using the PyOutline API."""
    ol = outline.Outline(
        jobData['name'], shot=jobData['shot'], show=jobData['show'], user=jobData['username'])
    lastLayer = None
    layerData = jobData['layers']
    layer = buildBlenderLayer(layerData, lastLayer)
    ol.add_layer(layer)
    lastLayer = layer

    return outline.cuerun.launch(ol, use_pycuerun=False)