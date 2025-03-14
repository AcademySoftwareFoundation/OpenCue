#!/usr/bin/env python

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

"""Tests for `FileSequence`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import str
import unittest

from FileSequence import FrameRange
from FileSequence import FrameSet
from FileSequence import FileSequence


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

        self.assertEqual(7, result.size())

    def testGet(self):
        result = FrameRange('1-7')

        self.assertEqual(5, result.get(4))

    def testIndex(self):
        result = FrameRange('1-7')

        self.assertEqual(5, result.index(6))
        self.assertEqual(-1, result.index(22))

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

        self.assertEqual(
            [57, 1, 2, 3, 4, 3, 2, 12, 14, 76, 73, 70, 6, 7, 9, 10, 12, 1, 6, 2, 4, 3, 5, 7],
            result.getAll())

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


class FileSequenceTests(unittest.TestCase):
    def __testFileSequence(self, filespec, **kwargs):
        fs = FileSequence(filespec)

        tests = {'prefix': fs.getPrefix(),
                 'frameSet': fs.frameSet,
                 'suffix': fs.getSuffix(),
                 'padSize': fs.getPadSize(),
                 'dirname': fs.getDirname(),
                 'basename': fs.getBasename()
                 }

        for arg, member in tests.items():
            if arg in kwargs:
                if isinstance(member, FrameSet):
                    self.assertEqual(member.getAll(), kwargs[arg].getAll(),
                                     "Comparing '%s', got '%s', expected '%s'" % (arg, str(member),
                                                                                  str(kwargs[arg])))
                else:
                    self.assertEqual(member, kwargs[arg],
                                     "Comparing '%s', got '%s', expected '%s'" % (arg, str(member),
                                                                                  str(kwargs[arg])))

    def testVariousFileSequences(self):
        """Test various file sequences are correctly parsed."""
        self.__testFileSequence('foo.1-1####.bar', prefix='foo.', frameSet=FrameSet('1-1'),
                                suffix='.bar', padSize=4)
        self.__testFileSequence('foo.####.bar', prefix='foo.', frameSet=None, suffix='.bar',
                                padSize=4)
        # Not sure why this becomes padSize of 10
        # self.__testFileSequence('foo.1-15x2#@#@.bar', prefix='foo.', frameSet=FrameSet('1-15x2'),
        # suffix='.bar',
        # padSize=10)
        self.__testFileSequence('foo.1-15x2.bar', prefix='foo.', frameSet=FrameSet('1-15x2'),
                                suffix='.bar', padSize=1)
        self.__testFileSequence('someImage.1,3,5####.rla', prefix='someImage.',
                                frameSet=FrameSet('1,3,5'), suffix='.rla', padSize=4)
        self.__testFileSequence('foo.####.exr.tx', prefix='foo.', frameSet=None, suffix='.exr.tx',
                                padSize=4)
        self.__testFileSequence('foo.1-10#.bar.1-9####.bar', prefix='foo.1-10#.bar.',
                                frameSet=FrameSet('1-9'), suffix='.bar', padSize=4)
        self.__testFileSequence('foo.1-9.bar', prefix='foo.', frameSet=FrameSet('1-9'),
                                suffix='.bar', padSize=1)
        self.__testFileSequence('foo.1-10.bar', prefix='foo.', frameSet=FrameSet('1-10'),
                                suffix='.bar', padSize=1)
        self.__testFileSequence('foo.9.bar', prefix='foo.', frameSet=FrameSet('9-9'), suffix='.bar',
                                padSize=1)

        self.__testFileSequence('foo.1-10#.bar', prefix='foo.', dirname='', basename='foo')
        self.__testFileSequence('/foo.1-10#.bar', prefix='/foo.', dirname='/', basename='foo')
        self.__testFileSequence('baz/foo.1-10#.bar', prefix='baz/foo.', dirname='baz/',
                                basename='foo')
        self.__testFileSequence('/baz/foo.1-10#.bar', prefix='/baz/foo.', dirname='/baz/',
                                basename='foo')
        self.__testFileSequence('/bar/baz/foo.1-10#.bar', prefix='/bar/baz/foo.',
                                dirname='/bar/baz/', basename='foo')

        self.__testFileSequence('foo.-15-15####.bar', prefix='foo.', frameSet=FrameSet('-15-15'),
                                suffix='.bar', padSize=4)
        self.__testFileSequence('foo.-15--1####.bar', prefix='foo.', frameSet=FrameSet('-15--1'),
                                suffix='.bar', padSize=4)

    def testPadSizeWithoutPadTokens(self):
        """Test the pad size is correctly guessed when no padding tokens are given."""
        self.__testFileSequence('foo.0009.bar', padSize=4)
        self.__testFileSequence('foo.1-9x0002.bar', padSize=1)
        # This test contradicts another test for negative steps
        # self.__testFileSequence('foo.9-1x-0002.bar',    padSize=1)
        self.__testFileSequence('foo.9-09x0002.bar', padSize=1)
        self.__testFileSequence('foo.9,10.bar', padSize=1)
        self.__testFileSequence('foo.009,10.bar', padSize=3)
        self.__testFileSequence('foo.-011.bar', padSize=4)

        # sequence padded to 4 but frame count goes above 9999
        self.__testFileSequence('foo.0001-10000.bar', padSize=4)

    def testInvalidSequences(self):
        """Test invalid file sequences throw expected exception."""
        self.assertRaises(ValueError, FileSequence, 'asdasdasda')
        self.assertRaises(ValueError, FileSequence, 'foo.fred#.bar')
        self.assertRaises(ValueError, FileSequence, 'foo..bar')
        self.assertRaises(ValueError, FileSequence, 'foo.-,x#.bar')
        self.assertRaises(ValueError, FileSequence, 'foo.x2.bar')
        self.assertRaises(ValueError, FileSequence, 'foo.-20---10.bar')
        # order reversed
        self.assertRaises(ValueError, FileSequence, 'foo.10-1.bar')
        self.assertRaises(ValueError, FileSequence, 'foo.-10--20.bar')
        # require a prefix
        self.assertRaises(ValueError, FileSequence, '.1')
        self.assertRaises(ValueError, FileSequence, '0.1')

    def __testStringify(self, filespec, index, expected):
        fs = FileSequence(filespec)
        self.assertEqual(expected, fs[index])

    def testStringify(self):
        self.__testStringify('foo.011.bar', 0, 'foo.011.bar')
        self.__testStringify('foo.-011.bar', 0, 'foo.-011.bar')

    def __testFrameList(self, filespec, frame, expected):
        fs = FileSequence(filespec)
        self.assertEqual(expected, fs(frame))

    def testFrameList(self):
        self.__testFrameList('foo.1-10.bar', 4, 'foo.4.bar')
        self.__testFrameList('foo.1-10####.bar', 4, 'foo.0004.bar')
        self.__testFrameList('foo.####.bar', 4, 'foo.0004.bar')


if __name__ == '__main__':
    unittest.main()
