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



import sys,dl
sys.setdlopenflags(dl.RTLD_NOW|dl.RTLD_GLOBAL)

sys.path.insert(0, './out')

import unittest
import FileSequence

class FileSequenceTestCase(unittest.TestCase):
    def __testFileSequence(self, filespec, **kwargs):
        fs = FileSequence.FileSequence(filespec)

        tests = {'prefix': fs.getPrefix(),
                 'frameSet': fs.frameSet,
                 'suffix': fs.getSuffix(),
                 'padSize': fs.getPadSize(),
                 'dirname': fs.getDirname(),
                 'basename': fs.getBasename()
        }

        for arg,member in tests.items():
            if kwargs.has_key(arg):
                self.assertEqual(member, kwargs[arg], "Comparing '%s', got '%s', expected '%s'" % (arg, str(member), str(kwargs[arg])))

    def __testStringify(self, filespec, index, expected):
        fs = FileSequence.FileSequence(filespec)
        self.assertEqual(expected, fs[index])

    def testVariousFileSequences(self):
        """Test various file sequences are correctly parsed."""
        self.__testFileSequence('foo.1-1#.bar',         prefix='foo.',       frameSet=FileSequence.FrameSet('1-1'),    suffix='.bar',    padSize=4)
        self.__testFileSequence('foo.#.bar',            prefix='foo.',       frameSet=None,               suffix='.bar',    padSize=4)
        self.__testFileSequence('foo.1-15x2#@#@.bar',   prefix='foo.',       frameSet=FileSequence.FrameSet('1-15x2'), suffix='.bar',    padSize=10)
        self.__testFileSequence('foo.1-15x2.bar',       prefix='foo.',       frameSet=FileSequence.FrameSet('1-15x2'), suffix='.bar',    padSize=1)
        self.__testFileSequence('someImage.1,3,5#.rla', prefix='someImage.', frameSet=FileSequence.FrameSet('1,3,5'),  suffix='.rla',    padSize=4)
        self.__testFileSequence('foo.#.exr.tx',         prefix='foo.',       frameSet=None,               suffix='.exr.tx', padSize=4)
        self.__testFileSequence('foo.1-10#.bar.1-9#.bar', prefix='foo.1-10#.bar.', frameSet=FileSequence.FrameSet('1-9'), suffix='.bar', padSize=4)
        self.__testFileSequence('foo.1-9.bar',          prefix='foo.',       frameSet=FileSequence.FrameSet('1-9'),    suffix='.bar',    padSize=1)
        self.__testFileSequence('foo.1-10.bar',         prefix='foo.',       frameSet=FileSequence.FrameSet('1-10'),   suffix='.bar',    padSize=1)
        self.__testFileSequence('foo.9.bar',            prefix='foo.',       frameSet=FileSequence.FrameSet('9-9'),    suffix='.bar',    padSize=1)

        self.__testFileSequence('foo.1-10#.bar',           prefix='foo.',            dirname='',           basename='foo')
        self.__testFileSequence('/foo.1-10#.bar',          prefix='/foo.',           dirname='/',          basename='foo')
        self.__testFileSequence('baz/foo.1-10#.bar',       prefix='baz/foo.',        dirname='baz/',       basename='foo')
        self.__testFileSequence('/baz/foo.1-10#.bar',      prefix='/baz/foo.',       dirname='/baz/',      basename='foo')
        self.__testFileSequence('/bar/baz/foo.1-10#.bar',  prefix='/bar/baz/foo.',   dirname='/bar/baz/',  basename='foo')

        self.__testFileSequence('foo.-15-15#.bar',      prefix='foo.',       frameSet=FileSequence.FrameSet('-15-15'),    suffix='.bar',    padSize=4)
        self.__testFileSequence('foo.-15--1#.bar',      prefix='foo.',       frameSet=FileSequence.FrameSet('-15--1'),    suffix='.bar',    padSize=4)

    def testPadSizeWithoutPadTokens(self):
        """Test the pad size is correctly guessed when no padding tokens are given."""
        self.__testFileSequence('foo.0009.bar',         padSize=4)
        self.__testFileSequence('foo.1-9x0002.bar',     padSize=1)
        self.__testFileSequence('foo.9-1x-0002.bar',    padSize=1)
        self.__testFileSequence('foo.9-09x0002.bar',    padSize=2)
        self.__testFileSequence('foo.9,10.bar',         padSize=1)
        self.__testFileSequence('foo.009,10.bar',       padSize=3)
        self.__testFileSequence('foo.-011.bar',         padSize=4)

        # sequence padded to 4 but frame count goes above 9999
        self.__testFileSequence('foo.0001-10000.bar',   padSize=4)

    def testInvalidSequences(self):
        """Test invalid file sequences throw expected exception."""
        self.assertRaises(ValueError, FileSequence.FileSequence, 'asdasdasda')
        self.assertRaises(ValueError, FileSequence.FileSequence, 'foo.fred#.bar')
        self.assertRaises(ValueError, FileSequence.FileSequence, 'foo..bar')
        self.assertRaises(ValueError, FileSequence.FileSequence, 'foo.-,x#.bar')
        self.assertRaises(ValueError, FileSequence.FileSequence, 'foo.x2.bar')
        self.assertRaises(ValueError, FileSequence.FileSequence, 'foo.-20---10.bar')
        # order reversed
        self.assertRaises(ValueError, FileSequence.FileSequence, 'foo.10-1.bar')
        self.assertRaises(ValueError, FileSequence.FileSequence, 'foo.-10--20.bar')
        # require a prefix
        self.assertRaises(ValueError, FileSequence.FileSequence, '.1')
        #self.assertRaises(ValueError, FileSequence.FileSequence, '0.1')

    def testStringify(self):
        self.__testStringify('foo.011.bar',  0, 'foo.011.bar')
        self.__testStringify('foo.-011.bar', 0, 'foo.-011.bar')


class FrameRangeTestCase(unittest.TestCase):
    def __testFrameRange(self, sequenceString, inTime, outTime, stepSize):
        fr = FileSequence.FrameRange(sequenceString)
        self.assertEquals(fr.inTime, inTime)
        self.assertEquals(fr.outTime, outTime)
        self.assertEquals(fr.stepSize, stepSize)

    def __testContains(self, sequenceString, members):
        fr = FileSequence.FrameRange(sequenceString)

        # via contains
        for item in members:
            self.failUnless(item in fr, "FrameRange '%s' missing '%d'" % (str(fr), item))

        # via iteration
        l = []
        [l.append(item) for item in fr]
        self.assertEquals(tuple(l), members)

    def testVariousFrameRanges(self):
        """Test various frame ranges are correctly parsed."""
        self.__testFrameRange('1',       inTime=1,  outTime=1,  stepSize=1)
        self.__testFrameRange('10',      inTime=10, outTime=10, stepSize=1)
        self.__testFrameRange('1-7',     inTime=1,  outTime=7,  stepSize=1)
        self.__testFrameRange('15-19',   inTime=15, outTime=19, stepSize=1)
        self.__testFrameRange('1-1x1',   inTime=1,  outTime=1,  stepSize=1)
        self.__testFrameRange('1-7x8',   inTime=1,  outTime=7,  stepSize=8)
        self.__testFrameRange('15-1x-2', inTime=15, outTime=1,  stepSize=-2)
        
    def testInvalidFrameRanges(self):
        """Test invalid frame ranges throw expected exception."""
        self.assertRaises(ValueError, FileSequence.FrameRange, '19-15')
        self.assertRaises(ValueError, FileSequence.FrameRange, 'asdasda')
        self.assertRaises(ValueError, FileSequence.FrameRange, '7-1x1')
        self.assertRaises(ValueError, FileSequence.FrameRange, '1-15x-1')

    def testFrameRangeContainsAndIter(self):
        """Test frame ranges expand to the correct members through contains and iteration."""
        self.__testContains('1-10', (1, 2, 3, 4, 5, 6, 7, 8, 9, 10))
        self.__testContains('1-10x2', (1, 3, 5, 7, 9))
        self.__testContains('10-1x-1', (10, 9, 8, 7, 6, 5, 4, 3, 2, 1))
        self.__testContains('20-12x-2', (20, 18, 16, 14, 12))

    def __testIsSequence(self, sequenceStr, isSequence):
        message = "%s is %sa FrameRange" % (sequenceStr, {True:'', False:'not '}[isSequence])
        self.assertEquals(
            FileSequence.FrameRange.isSequence(sequenceStr),
            isSequence, message)

    def testIsSequence(self):
        """Test FrameRange.isSequence."""
        for sequenceStr, isSequence in [
            ('1001', True),
            ('10+12', False),
            ('abc', False),
        ]:
            self.__testIsSequence(sequenceStr, isSequence)


class FrameSetTestCase(unittest.TestCase):
    def __testFrameSet(self, sequenceString, set):
        fs = FileSequence.FrameSet(sequenceString)
        fs_list = list(fs)
        fs_list.sort()
        set.sort()
        self.assertEquals(fs_list, set)

    def __testNearest(self, sequenceString, frame, result):
        fs = FileSequence.FrameSet(sequenceString)
        l, r = fs.nearest(frame)
        self.assertEquals((l, r), result)

    def __testIndex(self, sequenceString, frame, result):
        fs = FileSequence.FrameSet(sequenceString)
        i = fs.index(frame)
        self.assertEquals(i, result)

    def __testRevIndex(self, sequenceString, index, result):
        fs = FileSequence.FrameSet(sequenceString)
        frame = fs[index]
        self.assertEquals(frame, result)

    def __testInvalidRevIndex(self, sequenceString, index):
        fs = FileSequence.FrameSet(sequenceString)
        self.assertRaises(IndexError, fs.__getitem__, index)

    def __testLen(self, sequenceString, length):
        fs = FileSequence.FrameSet(sequenceString)
        self.assertEquals(len(fs), length)

    def __testNormalize(self, sequenceString, result):
        fs = FileSequence.FrameSet(sequenceString)
        fs.normalize()
        self.assertEquals(str(fs), result, "%s -> %s (expected %s)" % (sequenceString, str(fs), result))

    def testVariousFrameSets(self):
        """Test various frame sets are correctly parsed."""
        self.__testFrameSet('1', set=[1])
        self.__testFrameSet('1-2', set=[1,2])
        self.__testFrameSet('1,2', set=[1,2])
        self.__testFrameSet('1-4x2,5,9,15', set=[1,3,5,9,15])

    def testInvalidFrameSets(self):
        """Test invalid frame sets throw expected exception."""
        self.assertRaises(ValueError, FileSequence.FrameSet, 'asbasdas')

    def testNearest(self):
        """Test nearest frame searching."""
        self.__testNearest('1,3', 2, (1,3))
        self.__testNearest('1,3', 1, (None,3))
        self.__testNearest('1,3', 3, (1,None))
        self.__testNearest('1,2,3', 2, (1,3))
        self.__testNearest('2', 2, (None,None))
        self.__testNearest('1-7', 4, (3,5))
        self.__testNearest('7-1x-1', 4, (3,5))
        self.__testNearest('1-7x2', 4, (3,5))
        self.__testNearest('7-1x-2', 4, (3,5))
        self.__testNearest('1-7x14', 4, (1,None))
        self.__testNearest('13-23x4', 19, (17,21))
        self.__testNearest('13-20x4', 19, (17,None))
        self.__testNearest('13-20x4', 1, (None,13))
        self.__testNearest('13-20x4', 13, (None,17))

    def testNormalize(self):
        """Test normalize routine."""
        # trivial cases
        self.__testNormalize('','')
        self.__testNormalize('1','1')
        self.__testNormalize('1-3','1-3')

        # prefer 1,2 over 1-2
        self.__testNormalize('1-2','1,2')
        self.__testNormalize('1-3x2','1,3')

        # original order is lost!
        self.__testNormalize('3-1x-1','1-3')

        # duplicates are pruned
        self.__testNormalize('1-2,2-3','1-3')

        # detect steps
        self.__testNormalize('1,3,5,7','1-7x2')
        self.__testNormalize('1-3x2,5-7x2','1-7x2')
        self.__testNormalize('1,2,4,8,12,16,17,18', '1,2,4-16x4,17,18')

        # prefer to put 16 in the first range because it would be longer
        # [matches seqls: 1,2,4-16x4,17-19]
        self.__testNormalize('1,2,4,8,12,16,17,18,19', '1,2,4-16x4,17-19')
        # prefer to put 16 in the second range because it would be longer
        # [deviates from seqls: 1,2,4-16x4,17-20]
        self.__testNormalize('1,2,4,8,12,16,17,18,19,20', '1,2,4-12x4,16-20')

        # prefer to put 10 in the first range because it makes the
        # range with the higher skip longer (tie breaker)
        # [matches seqls: 1-10x3,12-16x2]
        self.__testNormalize('1,4,7,10,12,14,16', '1-10x3,12-16x2')
        # prefer to put 6 in the second range because it makes the
        # range with the higher skip longer (tie breaker)
        # [deviates from seqls: 1-7x2,10-16x3]
        self.__testNormalize('1,3,5,7,10,13,16', '1-5x2,7-16x3')
        # frames at the end affect multiple other sequences chosen
        self.__testNormalize('1,3,5,10,15,16,17,18', '1-5x2,10,15-18')

        self.__testNormalize('1-639,641,643,645,647,649,651-1000', '1-639,641-649x2,651-1000')

    def testIndex(self):
        """Test list index emulation."""
        self.__testIndex('1,3', 1, 0)
        self.__testIndex('1,3', 2, None)
        self.__testIndex('1,3', 3, 1)
        self.__testIndex('1-10,12-20', 12, 10)
        self.__testIndex('1-10,12-20', 13, 11)

        # 1 3 5 7 9 12 14 16 18 20
        # 0 1 2 3 4  5  6  7  8  9
        self.__testIndex('1-10x2,12-20x2', 12, 5)
        self.__testIndex('1-10x2,12-20x2', 14, 6)
        self.__testIndex('1-10x2,12-20x2', 16, 7)
        self.__testIndex('1-10x2,12-20x2', 18, 8)
        self.__testIndex('1-10x2,12-20x2', 20, 9)

        # 1 3 5 7 9 20 18 16 14 12
        # 0 1 2 3 4  5  6  7  8  9
        self.__testIndex('1-10x2,20-12x-2', 12, 9)
        self.__testIndex('1-10x2,20-12x-2', 14, 8)
        self.__testIndex('1-10x2,20-12x-2', 16, 7)
        self.__testIndex('1-10x2,20-12x-2', 18, 6)
        self.__testIndex('1-10x2,20-12x-2', 20, 5)

        # 1 11 21 31 36 37
        # 0  1  2  3  4  5
        self.__testIndex('1-35x10,36-37', 1, 0)
        self.__testIndex('1-35x10,36-37', 11, 1)
        self.__testIndex('1-35x10,36-37', 21, 2)
        self.__testIndex('1-35x10,36-37', 31, 3)
        self.__testIndex('1-35x10,36-37', 32, None)
        self.__testIndex('1-35x10,36-37', 36, 4)
        self.__testIndex('1-35x10,36-37', 37, 5)

    def testRevIndex(self):
        """Test looking up frame numbers by index."""
        self.__testRevIndex('1-3', 0, 1)
        self.__testRevIndex('1-3', 1, 2)
        self.__testRevIndex('1-3', 2, 3)
        self.__testRevIndex('1-3', -1, 3)
        self.__testRevIndex('1-3', -2, 2)
        self.__testRevIndex('1-3', -3, 1)

        self.__testRevIndex('1,3', 0, 1)
        self.__testRevIndex('1,3', 1, 3)
        self.__testRevIndex('1,3', -1, 3)
        self.__testRevIndex('1,3', -2, 1)

    def testInvalidRevIndex(self):
        """Test looking up out of range indexes."""
        self.__testInvalidRevIndex('1-3', -4)
        self.__testInvalidRevIndex('1-3', 3)

    def testLen(self):
        """Test sequence len emulation."""
        self.__testLen('1', 1)
        self.__testLen('1-10', 10)
        self.__testLen('1,2', 2)
        self.__testLen('1-10x2', 5)

    def __testIsSequence(self, sequenceStr, isSequence):
        message = "%s is %sa FrameSet" % (sequenceStr, {True:'', False:'not '}[isSequence])
        self.assertEquals(
            FileSequence.FrameSet.isSequence(sequenceStr),
            isSequence, message)

    def testIsSequence(self):
        """Test FrameSet.isSequence"""
        for sequenceStr, isSequence in [
            ('101', True),
            ('1001', True),
            ('abc', False),
            ('18?', False),
        ]:
            self.__testIsSequence(sequenceStr, isSequence)


class PaddingTestCase(unittest.TestCase):
    def testOperatorBitwiseAnd(self):
        a = FileSequence.Padding.fromString('009')
        b = FileSequence.Padding.fromString('10')
        self.assertEquals(a, a & b)

        c = FileSequence.Padding.fromString('0001')
        d = FileSequence.Padding.fromString('0002')
        self.assertEquals(c, c & d)
        self.assertEquals(c, d & c)
        self.assertEquals(d, c & d)
        self.assertEquals(d, d & c)

        e = FileSequence.Padding.fromString('1000')
        f = FileSequence.Padding.fromString('100')
        self.assertEquals(f, e & f)
        self.assertEquals(f, f & e)

    def __testCheckString(self, paddingStr, isPadding):
        message = "%s is %svalid initializing Padding" % (paddingStr, {True:'', False:'not '}[isPadding])
        self.assertEquals(
            FileSequence.FrameRange.isSequence(paddingStr),
            isPadding, message)

    def testCheckString(self):
        for paddingStr, isPadding in [
            ('1', True),
            ('-1', True),
            ('001', True),
            ('-001', True),
            ('1001', True),

            ('', False),
            ('-', False),
        ]:
            self.__testCheckString(paddingStr, isPadding)


class FindSequenceTestCase(unittest.TestCase):
    def __testFindSequence(self, fileList, expectedSequences, expectedNonsequences):
        seqs, nonseqs = FileSequence.FindSequence(fileList)
        self.assertEquals(seqs, expectedSequences,
            'FindSequence found sequences %s, expected %s'
            % (map(str, seqs), map(str, expectedSequences)))
        self.assertEquals(nonseqs, expectedNonsequences,
            'FindSequence found nonsequences %s, expected %s'
            % (map(str, nonseqs), map(str, expectedNonsequences)))

    def testFindSequence(self):
        for fileList, seqs, nonseqs in [
            (
                ['foo.0001.bar', 'foo.0002.bar', 'foo.0003.bar'],
                [FileSequence.FileSequence('foo.1-3#.bar')],
                [],
            ),
            (
                ['asldkfgj'],
                [],
                ['asldkfgj'],
            ),
            (
                [   'foo.0001.bar',
                    'bar.0002.baz',
                    'foo.0003.bar',
                    'bar.0004.baz',
                    'foo.0005.bar',
                    'bar.0006.baz',
                ],
                [   FileSequence.FileSequence('bar.2-6x2#.baz'),
                    FileSequence.FileSequence('foo.1-5x2#.bar'),
                ],
                [],
            ),
            (
                ['foo.101-200.bar'],
                [],
                ['foo.101-200.bar'],
            ),
        ]:
            self.__testFindSequence(fileList, seqs, nonseqs)


if __name__ == "__main__":
    unittest.main(argv=sys.argv)
