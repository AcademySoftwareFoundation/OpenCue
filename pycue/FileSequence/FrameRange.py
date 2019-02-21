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


from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from builtins import str
from builtins import range
from builtins import object
import re
from collections import OrderedDict


class FrameRange(object):
    """Represents a sequence of image frames."""

    SINGLE_FRAME_PATTERN = re.compile(r'^(-?)\d+$')
    SIMPLE_FRAME_RANGE_PATTERN = re.compile(r'^(?P<sf>(-?)\d+)-(?P<ef>(-?)\d+)$')
    STEP_PATTERN = re.compile(r'^(?P<sf>(-?)\d+)-(?P<ef>(-?)\d+)(?P<stepSep>[xy])(?P<step>(-?)\d+)$')
    INTERLEAVE_PATTERN = re.compile(r'^(?P<sf>(-?)\d+)-(?P<ef>(-?)\d+):(?P<step>(-?)\d+)$')

    def __init__(self, frameRange):
        """
        Construct a FrameRange object by parsing a spec.

        FrameSet("1-10x3");
        FrameSet("1-10y3"); // inverted step
        FrameSet("10-1x-1");
        FrameSet("1"); // same as "1-1x1"
        FrameSet("1-10:5"); // interleave of 5

        A valid spec consists of:

        An inTime.
        An optional hyphen and outTime.
        An optional x or y and stepSize.
        Or an optional : and interleaveSize.
        If outTime is less than inTime, stepSize must be negative.

        A stepSize of 0 produces an empty FrameRange.

        A stepSize cannot be combined with a interleaveSize.

        A stepSize designated with y creates an inverted step. Frames that would be included
        with an x step are excluded.

        Example: 1-10y3 == 2, 3, 5, 6, 8, 9.

        An interleaveSize alters the order of frames when iterating over the FrameRange. The
        iterator will first produce the list of frames from inTime to outTime with a stepSize
        equal to interleaveSize. The interleaveSize is then divided in half, producing another
        set of frames unique from the first set. This process is repeated until interleaveSize
        reaches 1.

        Example: 1-10:5 == 1, 6, 2, 4, 8, 10, 3, 5, 7, 9.
        """
        self.frameList = self.parseFrameRange(frameRange)

    def __str__(self):
        # TODO(bcipriano) Make this smarter, group frame ranges and by step. (Issue #83)
        return ','.join([str(frame) for frame in self.frameList])

    def __getitem__(self, key):
        return self.frameList[key]

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
        self.frameList = list(set(self.frameList))
        self.frameList.sort()

    @classmethod
    def parseFrameRange(cls, frameRange):
        singleFrameMatcher = re.match(cls.SINGLE_FRAME_PATTERN, frameRange)
        if singleFrameMatcher:
            return [int(frameRange)]

        simpleRangeMatcher = re.match(cls.SIMPLE_FRAME_RANGE_PATTERN, frameRange)
        if simpleRangeMatcher:
            startFrame = int(simpleRangeMatcher.group('sf'))
            endFrame = int(simpleRangeMatcher.group('ef'))
            return cls.getIntRange(startFrame, endFrame, (1 if endFrame >= startFrame else -1))

        rangeWithStepMatcher = re.match(cls.STEP_PATTERN, frameRange)
        if rangeWithStepMatcher:
            startFrame = int(rangeWithStepMatcher.group('sf'))
            endFrame = int(rangeWithStepMatcher.group('ef'))
            step = int(rangeWithStepMatcher.group('step'))
            stepSep = rangeWithStepMatcher.group('stepSep')
            return cls.getSteppedRange(startFrame, endFrame, step, stepSep == 'y')

        rangeWithInterleaveMatcher = re.match(cls.INTERLEAVE_PATTERN, frameRange)
        if rangeWithInterleaveMatcher:
            startFrame = int(rangeWithInterleaveMatcher.group('sf'))
            endFrame = int(rangeWithInterleaveMatcher.group('ef'))
            step = int(rangeWithInterleaveMatcher.group('step'))
            return cls.getInterleavedRange(startFrame, endFrame, step)

        raise ValueError('unrecognized frame range syntax ' + frameRange)

    @staticmethod
    def getIntRange(start, end, step):
        return list(range(start, end+(step // abs(step)), step))

    @classmethod
    def getSteppedRange(cls, start, end, step, inverseStep):
        cls.validateStepSign(start, end, step)
        steppedRange = cls.getIntRange(start, end, step)
        if inverseStep:
            fullRange = cls.getIntRange(start, end, (-1 if step < 0 else 1))
            return [frame for frame in fullRange if frame not in steppedRange]
        return steppedRange

    @classmethod
    def getInterleavedRange(cls, start, end, step):
        cls.validateStepSign(start, end, step)
        interleavedFrames = OrderedDict()
        incrValue = step // abs(step)
        while abs(step) > 0:
            interleavedFrames.update([(frame, None) for frame in cls.getIntRange(start, end, step)])
            start += incrValue
            step = int(step / 2.0)
        return list(interleavedFrames.keys())

    @staticmethod
    def validateStepSign(start, end, step):
        if step > 1 and end < start:
            raise ValueError(
                'end frame may not be less than start frame when using a positive step')
        elif step == 0:
            raise ValueError('step cannot be zero')
        elif step < 0 and end >= start:
            raise ValueError(
                'end frame may not be greater than start frame when using a negative step')
