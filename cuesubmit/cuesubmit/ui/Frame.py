from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from cuesubmit.ui import Widgets


class FrameSpecWidget(Widgets.CueHelpWidget):
    """Widget for entering a frame spec."""

    helpText = 'Enter a FrameSpec value.\n' \
               'A frame spec consists of a start time, an optional end time, a step, ' \
               'and an interleave.\n' \
               'Multiple ranges can be added together by separating with commas.\n' \
               '    Ex:\n' \
               '    1-10x3\n' \
               '    1-10y3 // inverted step\n' \
               '    10-1x-1\n' \
               '    1 // same as "1-1x1"\n' \
               '    1-10:5 // interleave of 5\n' \
               '    1-5x2, 6-10 // 1 through 5 with a step of 2 and 6 through 10\n'

    def __init__(self, parent=None):
        super(FrameSpecWidget, self).__init__(parent)
        self.frameSpecInput = Widgets.CueLabelLineEdit('Frame Spec:')
        self.contentLayout.addWidget(self.frameSpecInput)
