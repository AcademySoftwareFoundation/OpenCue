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

"""Module for `FileSequence.FrameSet`."""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import object
from .FrameRange import FrameRange


class FrameSet(object):
    """Represents a sequence of `FileSequence.FrameRange`."""

    def __init__(self, frameRange):
        """Construct a FrameSet object by parsing a spec.

        See FrameRange for the supported syntax. A FrameSet follows the same syntax,
        with the addition that it may be a comma-separated list of different FrameRanges.
        """
        self.frameList = self.parseFrameRange(frameRange)

    def __str__(self):
        # TODO(bcipriano) Make this smarter, group frame ranges and by step. (Issue #83)
        return ','.join([str(frame) for frame in self.frameList])

    def __getitem__(self, key):
        return self.frameList[key]

    def __len__(self):
        return self.size()

    def size(self):
        """Gets the number of frames contained in this sequence."""
        return len(self.frameList)

    def get(self, idx):
        """Gets an individual entry in the sequence, by numerical position."""
        return self.frameList[idx]

    def index(self, idx):
        """Query index of frame number in frame set.

        Returns:
            int, index of frame. -1 if frame set does not contain frame.
        """
        try:
            return self.frameList.index(idx)
        except ValueError:
            return -1

    def getAll(self):
        """Gets the full numerical sequence."""
        return self.frameList

    def normalize(self):
        """Sorts and dedeuplicates the sequence."""
        self.frameList = list(set(self.frameList))
        self.frameList.sort()

    @staticmethod
    def parseFrameRange(frameRange):
        """
        Parses a string representation of a frame range into a FrameSet.

        :type frameRange: str
        :param frameRange: String representation of the frame range.
        :rtype: FrameSet
        :return: The FrameSet representing the same sequence.
        """
        frameList = []
        for frameRangeSection in frameRange.split(','):
            frameList.extend(FrameRange.parseFrameRange(frameRangeSection))
        return frameList
