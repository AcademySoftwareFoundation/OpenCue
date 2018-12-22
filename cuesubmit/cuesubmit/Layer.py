

class DependType:
    """Types of Dependencies available in the UI."""

    Null = ''
    Layer = 'Layer'
    Frame = 'Frame'


class LayerData(object):
    """Data object for storing settings about the Layer."""

    def __init__(self):
        self.name = ''
        self.layerType = ''
        self.cmd = {}
        self.layerRange = ''
        self.chunk = '1'
        self.cores = '1'
        self.env = {}
        self.services = []
        self.dependType = DependType.Null
        self.dependsOn = None

    def __str__(self):
        return str(self.toDict())

    def toDict(self):
        """Return a dictionary from the attributes."""
        return {
            'name': self.name,
            'layerType': self.layerType,
            'cmd': self.cmd,
            'layerRange': self.layerRange,
            'chunk': self.chunk,
            'cores': self.cores,
            'env': self.env,
            'services': self.services,
            'dependType': self.dependType,
            'dependsOn': self.dependsOn
        }

    @staticmethod
    def buildFactory(name=None, layerType=None, cmd=None, layerRange=None, chunk=None, cores=None,
                     env=None, services=None, dependType=None, dependsOn=None):
        """Build a new LayerData object with the given settings."""
        layerData = LayerData()
        layerData.update(name, layerType, cmd, layerRange, chunk, cores, env, services, dependType,
                         dependsOn)
        return layerData

    def update(self, name=None, layerType=None, cmd=None, layerRange=None, chunk=None, cores=None,
               env=None, services=None, dependType=None, dependsOn=None):
        """Update this Layer with the provided settings."""
        if name is not None:
            self.name = name
        if layerType is not None:
            self.layerType = layerType
        if cmd is not None:
            self.cmd = cmd
        if layerRange is not None:
            self.layerRange = layerRange
        if chunk is not None:
            self.chunk = chunk
        if cores is not None:
            self.cores = cores
        if env is not None:
            self.env = env
        if services is not None:
            self.services = services
        if dependType is not None:
            self.dependType = dependType
        if dependsOn is not None:
            self.dependsOn = dependsOn
