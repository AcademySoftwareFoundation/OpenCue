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

"""
Tests for the outline.util module.
"""

import unittest

import outline.util


class CompactFrameRangeTests(unittest.TestCase):

    """Tests for outline.util.compact_frame_range."""

    def test_empty(self):
        self.assertEqual('', outline.util.compact_frame_range([]))

    def test_single_frame(self):
        self.assertEqual('5', outline.util.compact_frame_range([5]))

    def test_contiguous_range(self):
        self.assertEqual(
            '1001-2301', outline.util.compact_frame_range(list(range(1001, 2302))))

    def test_non_contiguous_range(self):
        self.assertEqual(
            '1-3,10,20-22', outline.util.compact_frame_range([1, 2, 3, 10, 20, 21, 22]))

    def test_out_of_order_frames_are_not_regrouped(self):
        # Grouping is based on the input's position, not numeric order, so a
        # descending or shuffled input is not treated as a run.
        self.assertEqual('5,4,3', outline.util.compact_frame_range([5, 4, 3]))

    def test_duplicate_frames_are_preserved(self):
        self.assertEqual('1-2,1', outline.util.compact_frame_range([1, 2, 1]))
