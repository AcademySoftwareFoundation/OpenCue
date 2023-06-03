
import outline
import outline.cuerun

# from . import Constants

def buildBlenderCmd(layerData):
    blenderFile = layerData.cmd.get('blenderFile')
    outputPath = layerData.cmd.get('outputPath')
    outputFormat = layerData.cmd.get('outputFormat')

    if not blenderFile:
        raise ValueError('No Blender file provided. Cannot submit job.')

    renderCommand = '{renderCmd} -b -noaudio {blenderFile}'.format(
        renderCmd="blender", blenderFile=blenderFile)
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
    threadable = float(layerData.cores) >= 2
    layer = outline.modules.shell.Shell(
        layerData.name, command=command.split(), chunk=layerData.chunk,
        threads=float(layerData.cores), range=str(layerData.layerRange), threadable=threadable)
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
    # print (layerData.cmd.get({}))
    # for layerData in jobData['layers']:
    layer = buildBlenderLayer(layerData, lastLayer)
    ol.add_layer(layer)
    lastLayer = layer

    # return outline.cuerun.launch(ol, use_pycuerun=False)