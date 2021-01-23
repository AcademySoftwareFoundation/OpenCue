'''CueNodeGraphQt is an OpenCue specific extension of NodeGraphQt

The docs for NodeGraphQt can be found at:
http://chantasticvfx.com/nodeGraphQt/html/nodes.html
'''
import NodeGraphQt.widgets.properties
from .nodes import CueLayerNode
from .constants import NODE_PROP_CUELAYERITEMWIDGET
from .widgets.properties import PropLayerItemWidget

NodeGraphQt.widgets.properties.WIDGET_MAP.update(
    {NODE_PROP_CUELAYERITEMWIDGET: PropLayerItemWidget}
)
