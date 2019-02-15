#!/usr/local/bin/python

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

from builtins import str
import unittest

from FileSequence import FrameRange
from FileSequence import FrameSet


class FrameRangeTests(unittest.TestCase):

    def testSingleFrame(self):
        frame = 4927

        result = FrameRange(str(frame))

        self.assertEqual([frame], result.getAll())

    def testNegativeSingleFrame(self):
        frame = -4982

        result = FrameRange(str(frame))

        self.assertEqual([frame], result.getAll())

    def testFrameRange(self):
        result = FrameRange('1-7')

        self.assertEqual([1, 2, 3, 4, 5, 6, 7], result.getAll())

    def testNegativeFrameRange(self):
        result = FrameRange('-20--13')

        self.assertEqual([-20, -19, -18, -17, -16, -15, -14, -13], result.getAll())

    def testNegativeToPositiveFrameRange(self):
        result = FrameRange('-5-3')

        self.assertEqual([-5, -4, -3, -2, -1, 0, 1, 2, 3], result.getAll())

    def testReverseFrameRange(self):
        result = FrameRange('6-2')

        self.assertEqual([6, 5, 4, 3, 2], result.getAll())

    def testReverseNegativeFrameRange(self):
        result = FrameRange('-2--6')

        self.assertEqual([-2, -3, -4, -5, -6], result.getAll())

    def testStep(self):
        result = FrameRange('1-8x2')

        self.assertEqual([1, 3, 5, 7], result.getAll())

    def testNegativeStep(self):
        result = FrameRange('8-1x-2')

        self.assertEqual([8, 6, 4, 2], result.getAll())

    def testNegativeStepInvalidRange(self):
        with self.assertRaises(ValueError):
            FrameRange('1-8x-2')

    def testInvertedStep(self):
        result = FrameRange('1-8y2')

        self.assertEqual([2, 4, 6, 8], result.getAll())

    def testNegativeInvertedStep(self):
        result = FrameRange('8-1y-2')

        self.assertEqual([7, 5, 3, 1], result.getAll())

    def testInterleave(self):
        result = FrameRange('1-10:5')

        self.assertEqual([1, 6, 2, 4, 8, 10, 3, 5, 7, 9], result.getAll())

    def testNegativeInterleave(self):
        result = FrameRange('10-1:-5')

        self.assertEqual([10, 5, 9, 7, 3, 1, 8, 6, 4, 2], result.getAll())

    def testNonNumericalInput(self):
        with self.assertRaises(ValueError):
            FrameRange('a')

        with self.assertRaises(ValueError):
            FrameRange('a-b')

        with self.assertRaises(ValueError):
            FrameRange('1-5xc')

        with self.assertRaises(ValueError):
            FrameRange('1-5:c')

    def testInvalidRange(self):
        with self.assertRaises(ValueError):
            FrameRange('1-10-20')

        with self.assertRaises(ValueError):
            FrameRange('1x10-20')

        with self.assertRaises(ValueError):
            FrameRange('1:10-20')

    def testSize(self):
        result = FrameRange('1-7')

        self.assertEquals(7, result.size())

    def testGet(self):
        result = FrameRange('1-7')

        self.assertEquals(5, result.get(4))

    def testIndex(self):
        result = FrameRange('1-7')

        self.assertEquals(5, result.index(6))
        self.assertEquals(-1, result.index(22))

    def testNormalize(self):
        simpleRange = FrameRange('3-5')
        simpleRange.normalize()

        self.assertEqual([3, 4, 5], simpleRange.getAll())

        reverseOrder = FrameRange('3-1x-1')
        reverseOrder.normalize()

        self.assertEqual([1, 2, 3], reverseOrder.getAll())


class FrameSetTests(unittest.TestCase):

    def testMultipleSegments(self):
        result = FrameSet('57,1-3,4-2,12-15x2,76-70x-3,5-12y3,1-7:5')

        self.assertEqual([57, 1, 2, 3, 4, 3, 2, 12, 14, 76, 73, 70, 6, 7, 9, 10, 12, 1, 6, 2, 4, 3, 5, 7], result.getAll())

    def testSize(self):
        result = FrameSet('1-7')

        self.assertEqual(7, result.size())

    def testGet(self):
        result = FrameSet('1-7')

        self.assertEqual(5, result.get(4))

    def testIndex(self):
        result = FrameSet('1-7')

        self.assertEqual(5, result.index(6))
        self.assertEqual(-1, result.index(22))

    def testNormalize(self):
        reverseOrder = FrameSet('5,3-1x-1')
        reverseOrder.normalize()

        self.assertEqual([1, 2, 3, 5], reverseOrder.getAll())

        duplicates = FrameSet('1-2,2-3')
        duplicates.normalize()

        self.assertEqual([1, 2, 3], duplicates.getAll())


if __name__ == '__main__':
    unittest.main()
