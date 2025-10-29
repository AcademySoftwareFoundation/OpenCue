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


"""Unit tests for memory and duration filtering logic in cueman."""

import unittest
from unittest import mock
import argparse

from cueadmin import common
from cueman import main as cueman_main


def build_args(**kwargs):
    """Build a minimal argparse.Namespace for testing."""
    fields = [
        "lf", "lp", "ll", "info",
        "pause", "resume", "term", "eat", "kill", "retry", "done",
        "stagger", "reorder", "retries", "autoeaton", "autoeatoff",
        "force",
        "layer", "state", "range", "memory", "duration", "page", "limit",
        "server", "facility", "verbose",
    ]
    args_dict = {f: kwargs.get(f, None) for f in fields}
    # Defaults
    if "force" not in kwargs:
        args_dict["force"] = False
    if "duration" not in kwargs:
        args_dict["duration"] = cueman_main.DEFAULT_MIN_DURATION
    if "memory" not in kwargs:
        args_dict["memory"] = cueman_main.DEFAULT_MIN_MEMORY
    return argparse.Namespace(**args_dict)


class TestMemoryRangeParsing(unittest.TestCase):
    """Test memory range parsing functionality."""

    @mock.patch("opencue.api.getProcs")
    def test_memory_range_parsing_1_to_4_gb(self, mock_getProcs):
        """Test memory range parsing: 1-4 GB."""
        args = build_args(lp="job1", memory="1-4", duration="0.01")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 1 GB = 1048576 KB, 4 GB = 4194304 KB
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["memory"], "1048576-4194304")

    @mock.patch("opencue.api.getProcs")
    def test_memory_range_parsing_2_to_8_gb(self, mock_getProcs):
        """Test memory range parsing: 2-8 GB."""
        args = build_args(lp="job1", memory="2-8", duration="0.01")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 2 GB = 2097152 KB, 8 GB = 8388608 KB
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["memory"], "2097152-8388608")

    @mock.patch("opencue.api.getProcs")
    def test_memory_greater_than_2_gb(self, mock_getProcs):
        """Test memory filtering: gt2 (greater than 2 GB)."""
        args = build_args(lp="job1", memory="gt2", duration="0.01")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 2 GB = 2097152 KB
        # The function calls getProcs twice for gt pattern:
        # once with less_than, then with greater_than
        self.assertEqual(mock_getProcs.call_count, 2)
        # Check the final call has memory_greater_than
        final_call_kwargs = mock_getProcs.call_args_list[-1][1]
        self.assertEqual(final_call_kwargs["memory_greater_than"], 2097152)

    @mock.patch("opencue.api.getProcs")
    def test_memory_greater_than_5_gb_lowercase(self, mock_getProcs):
        """Test memory filtering: gt5 (lowercase)."""
        args = build_args(lp="job1", memory="gt5", duration="0.01")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 5 GB = 5242880 KB
        # The function calls getProcs twice for gt pattern
        self.assertEqual(mock_getProcs.call_count, 2)
        final_call_kwargs = mock_getProcs.call_args_list[-1][1]
        self.assertEqual(final_call_kwargs["memory_greater_than"], 5242880)

    @mock.patch("opencue.api.getProcs")
    def test_memory_less_than_5_gb(self, mock_getProcs):
        """Test memory filtering: lt5 (less than 5 GB)."""
        args = build_args(lp="job1", memory="lt5", duration="0.01")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 5 GB = 5242880 KB
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["memory_less_than"], 5242880)

    @mock.patch("opencue.api.getProcs")
    def test_memory_less_than_3_gb_lowercase(self, mock_getProcs):
        """Test memory filtering: lt3 (lowercase)."""
        args = build_args(lp="job1", memory="lt3", duration="0.01")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 3 GB = 3145728 KB
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["memory_less_than"], 3145728)


class TestDurationRangeParsing(unittest.TestCase):
    """Test duration range parsing functionality."""

    @mock.patch("opencue.api.getProcs")
    def test_duration_range_parsing_1_5_to_3_0_hours(self, mock_getProcs):
        """Test duration range parsing: 1.5-3.0 hours."""
        args = build_args(lp="job1", memory="1", duration="1.5-3.0")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 1.5 hours = 5400 seconds, 3.0 hours = 10800 seconds
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["duration"], "5400-10800")

    @mock.patch("opencue.api.getProcs")
    def test_duration_range_parsing_0_5_to_2_5_hours(self, mock_getProcs):
        """Test duration range parsing: 0.5-2.5 hours."""
        args = build_args(lp="job1", memory="1", duration="0.5-2.5")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 0.5 hours = 1800 seconds, 2.5 hours = 9000 seconds
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["duration"], "1800-9000")

    @mock.patch("opencue.api.getProcs")
    def test_duration_single_value(self, mock_getProcs):
        """Test duration with single value (treated as max)."""
        args = build_args(lp="job1", memory="1", duration="2")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 2 hours = 7200 seconds
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["duration"], "0-7200")

    @mock.patch("opencue.api.getProcs")
    def test_duration_integer_range(self, mock_getProcs):
        """Test duration with integer range."""
        args = build_args(lp="job1", memory="1", duration="1-3")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 1 hour = 3600 seconds, 3 hours = 10800 seconds
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["duration"], "3600-10800")


class TestUnitConversion(unittest.TestCase):
    """Test unit conversion functions."""

    def test_gigs_to_kb_conversion_1_gb(self):
        """Test conversion: 1 GB to KB."""
        result = common.Convert.gigsToKB(1)
        self.assertEqual(result, 1048576)

    def test_gigs_to_kb_conversion_4_gb(self):
        """Test conversion: 4 GB to KB."""
        result = common.Convert.gigsToKB(4)
        self.assertEqual(result, 4194304)

    def test_gigs_to_kb_conversion_0_5_gb(self):
        """Test conversion: 0.5 GB to KB."""
        result = common.Convert.gigsToKB(0.5)
        self.assertEqual(result, 524288)

    def test_gigs_to_kb_conversion_fractional(self):
        """Test conversion: 2.5 GB to KB."""
        result = common.Convert.gigsToKB(2.5)
        self.assertEqual(result, 2621440)

    def test_hours_to_seconds_conversion_1_hour(self):
        """Test conversion: 1 hour to seconds."""
        result = common.Convert.hoursToSeconds(1)
        self.assertEqual(result, 3600)

    def test_hours_to_seconds_conversion_2_5_hours(self):
        """Test conversion: 2.5 hours to seconds."""
        result = common.Convert.hoursToSeconds(2.5)
        self.assertEqual(result, 9000)

    def test_hours_to_seconds_conversion_0_5_hours(self):
        """Test conversion: 0.5 hours to seconds."""
        result = common.Convert.hoursToSeconds(0.5)
        self.assertEqual(result, 1800)

    def test_hours_to_seconds_conversion_fractional(self):
        """Test conversion: 1.5 hours to seconds."""
        result = common.Convert.hoursToSeconds(1.5)
        self.assertEqual(result, 5400)


class TestInvalidRangeHandling(unittest.TestCase):
    """Test handling of invalid range inputs."""

    def test_memory_invalid_format_raises_error(self):
        """Test that invalid memory format raises ValueError."""
        args = build_args(lp="job1", memory="invalid", duration="0.01")

        with self.assertRaises(ValueError):
            cueman_main._get_proc_filters(args)

    def test_duration_invalid_format_returns_none(self):
        """Test that invalid duration format returns None."""
        args = build_args(lp="job1", memory="1", duration="invalid")

        result, _ = cueman_main._get_proc_filters(args)

        # Should return None for invalid input
        self.assertIsNone(result)

    @mock.patch("opencue.api.getProcs")
    def test_memory_empty_string(self, mock_getProcs):
        """Test memory with empty string."""
        args = build_args(lp="job1", memory="", duration="1")
        mock_getProcs.return_value = []

        result, _ = cueman_main._get_proc_filters(args)

        # Empty memory should not cause errors, just filter by duration
        self.assertIsNotNone(result)


class TestBoundaryConditions(unittest.TestCase):
    """Test boundary conditions for filtering."""

    @mock.patch("opencue.api.getProcs")
    def test_memory_zero_boundary(self, mock_getProcs):
        """Test memory with zero value is accepted (0-5 means up to 5GB)."""
        args = build_args(lp="job1", memory="0-1", duration="0.01")
        mock_getProcs.return_value = []

        result, _ = cueman_main._get_proc_filters(args)

        # Should accept 0 as valid (0-1 means up to 1 GB)
        self.assertIsNotNone(result)

    @mock.patch("opencue.api.getProcs")
    def test_memory_large_value(self, mock_getProcs):
        """Test memory with large value (100 GB)."""
        args = build_args(lp="job1", memory="gt100", duration="0.01")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 100 GB = 104857600 KB
        # The function calls getProcs twice for gt pattern
        self.assertEqual(mock_getProcs.call_count, 2)
        final_call_kwargs = mock_getProcs.call_args_list[-1][1]
        self.assertEqual(final_call_kwargs["memory_greater_than"], 104857600)

    @mock.patch("opencue.api.getProcs")
    def test_duration_zero_boundary(self, mock_getProcs):
        """Test duration with zero value is accepted (0-1 means up to 1 hour)."""
        args = build_args(lp="job1", memory="1", duration="0-1")
        mock_getProcs.return_value = []

        result, _ = cueman_main._get_proc_filters(args)

        # Should accept 0 as valid (0-1 means up to 1 hour)
        self.assertIsNotNone(result)

    @mock.patch("opencue.api.getProcs")
    def test_duration_large_value(self, mock_getProcs):
        """Test duration with large value (24 hours)."""
        args = build_args(lp="job1", memory="1", duration="24")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 24 hours = 86400 seconds
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["duration"], "0-86400")

    @mock.patch("opencue.api.getProcs")
    def test_memory_small_fractional_value(self, mock_getProcs):
        """Test memory with small fractional value (0.01 GB - boundary default)."""
        args = build_args(lp="job1", memory="0.01", duration="0.01")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 0.01 GB = 10485 KB (rounded down due to int conversion)
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        # The value should be memory_less_than since it doesn't match gt/lt/range pattern
        self.assertIn("memory_less_than", call_kwargs)

    @mock.patch("opencue.api.getProcs")
    def test_duration_small_fractional_value(self, mock_getProcs):
        """Test duration with small fractional value (0.01 hours - boundary default)."""
        args = build_args(lp="job1", memory="1", duration="0.01")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 0.01 hours = 36 seconds
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["duration"], "0-36")


class TestRegexPatternMatching(unittest.TestCase):
    """Test regex pattern matching for gt/lt operators."""

    def test_regex_pattern_range_matching(self):
        """Test RE_PATTERN_RANGE regex matches valid ranges."""
        pattern = cueman_main.RE_PATTERN_RANGE

        # Valid ranges
        self.assertIsNotNone(pattern.search("1-4"))
        self.assertIsNotNone(pattern.search("1.5-3.0"))
        self.assertIsNotNone(pattern.search("0.5-2.5"))
        self.assertIsNotNone(pattern.search("10-20"))

    def test_regex_pattern_range_not_matching(self):
        """Test RE_PATTERN_RANGE regex doesn't match invalid patterns."""
        pattern = cueman_main.RE_PATTERN_RANGE

        # Invalid patterns
        self.assertIsNone(pattern.search("gt2"))
        self.assertIsNone(pattern.search("lt5"))
        self.assertIsNone(pattern.search("2"))
        self.assertIsNone(pattern.search("invalid"))

    def test_regex_pattern_greater_less_than_matching(self):
        """Test RE_PATTERN_GREATER_LESS_THAN regex matches valid gt/lt operators."""
        pattern = cueman_main.RE_PATTERN_GREATER_LESS_THAN

        # Valid gt/lt patterns
        self.assertIsNotNone(pattern.search("gt2"))
        self.assertIsNotNone(pattern.search("lt5"))
        self.assertIsNotNone(pattern.search("GT10"))
        self.assertIsNotNone(pattern.search("LT100"))
        self.assertIsNotNone(pattern.search("gt100"))

    def test_regex_pattern_greater_less_than_not_matching(self):
        """Test RE_PATTERN_GREATER_LESS_THAN regex doesn't match invalid patterns."""
        pattern = cueman_main.RE_PATTERN_GREATER_LESS_THAN

        # Invalid patterns
        self.assertIsNone(pattern.search("1-4"))
        self.assertIsNone(pattern.search("2"))
        self.assertIsNone(pattern.search("invalid"))
        self.assertIsNone(pattern.search("gt"))  # Missing number
        self.assertIsNone(pattern.search("lt"))  # Missing number


class TestDefaultValueApplication(unittest.TestCase):
    """Test default value application."""

    @mock.patch("opencue.api.getProcs")
    def test_default_memory_value(self, mock_getProcs):
        """Test default memory value (0.01 GB) is applied correctly."""
        args = build_args(lp="job1")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # Default duration 0.01 hours = 36 seconds
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["duration"], "0-36")

    @mock.patch("opencue.api.getProcs")
    def test_default_duration_value(self, mock_getProcs):
        """Test default duration value (0.01 hours) is applied correctly."""
        args = build_args(lp="job1")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # Default is applied in the build_args helper
        self.assertEqual(args.duration, cueman_main.DEFAULT_MIN_DURATION)
        self.assertEqual(args.memory, cueman_main.DEFAULT_MIN_MEMORY)


class TestFilterCombination(unittest.TestCase):
    """Test filter combination with other parameters."""

    @mock.patch("opencue.api.getProcs")
    def test_combined_memory_and_duration_filters(self, mock_getProcs):
        """Test combined memory and duration filters."""
        args = build_args(lp="job1", memory="2-4", duration="1-2")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["memory"], "2097152-4194304")
        self.assertEqual(call_kwargs["duration"], "3600-7200")
        self.assertEqual(call_kwargs["job"], ["job1"])

    @mock.patch("opencue.api.getProcs")
    def test_combined_gt_memory_and_duration_range(self, mock_getProcs):
        """Test combined gt memory and duration range."""
        args = build_args(lp="job1", memory="gt3", duration="0.5-1.5")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # The function calls getProcs twice for gt pattern
        self.assertEqual(mock_getProcs.call_count, 2)
        final_call_kwargs = mock_getProcs.call_args_list[-1][1]
        self.assertEqual(final_call_kwargs["memory_greater_than"], 3145728)
        self.assertEqual(final_call_kwargs["duration"], "1800-5400")

    @mock.patch("opencue.api.getProcs")
    def test_combined_lt_memory_and_duration_single(self, mock_getProcs):
        """Test combined lt memory and single duration value."""
        args = build_args(lp="job1", memory="lt8", duration="3")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["memory_less_than"], 8388608)
        self.assertEqual(call_kwargs["duration"], "0-10800")

    @mock.patch("opencue.api.getProcs")
    def test_duration_only_filter_no_memory(self, mock_getProcs):
        """Test duration filter without explicit memory filter."""
        args = build_args(lp="job1", duration="2")
        # Don't set memory explicitly to test no memory condition
        args.memory = None
        mock_getProcs.return_value = []

        # Manually set duration to avoid default
        args.duration = "2"

        result, _ = cueman_main._get_proc_filters(args)

        # When memory is None but duration is set, it should still work
        # by checking if memory condition exists
        # The function should handle this gracefully


class TestProcFiltersEdgeCases(unittest.TestCase):
    """Test edge cases for _get_proc_filters function."""

    def test_memory_range_with_same_min_max(self):
        """Test memory range where min equals max is rejected."""
        args = build_args(lp="job1", memory="2-2", duration="0.01")

        result, _ = cueman_main._get_proc_filters(args)

        # Should return None for invalid input
        self.assertIsNone(result)

    def test_duration_range_with_same_min_max(self):
        """Test duration range where min equals max is rejected."""
        args = build_args(lp="job1", memory="1", duration="1-1")

        result, _ = cueman_main._get_proc_filters(args)

        # Should return None for invalid input
        self.assertIsNone(result)

    def test_very_small_memory_values_with_integers(self):
        """Test memory range parsing only works with integers in the code."""
        # The current implementation uses int() cast which doesn't work with floats
        # This test documents the actual behavior
        args = build_args(lp="job1", memory="1-2", duration="0.01")

        # This should work fine
        with mock.patch("opencue.api.getProcs") as mock_getProcs:
            mock_getProcs.return_value = []
            cueman_main._get_proc_filters(args)
            mock_getProcs.assert_called_once()

    @mock.patch("opencue.api.getProcs")
    def test_very_small_duration_values(self, mock_getProcs):
        """Test very small duration values."""
        args = build_args(lp="job1", memory="1", duration="0.001-0.002")
        mock_getProcs.return_value = []

        cueman_main._get_proc_filters(args)

        # 0.001 hours = 3 seconds, 0.002 hours = 7 seconds (rounded down)
        mock_getProcs.assert_called_once()
        call_kwargs = mock_getProcs.call_args[1]
        self.assertEqual(call_kwargs["duration"], "3-7")

    @mock.patch("opencue.api.getProcs")
    def test_proc_filters_returns_tuple(self, mock_getProcs):
        """Test that _get_proc_filters returns a tuple."""
        args = build_args(lp="job1", memory="1-4", duration="1-2")
        mock_procs = ["proc1", "proc2"]
        mock_getProcs.return_value = mock_procs

        result = cueman_main._get_proc_filters(args)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], mock_procs)
        self.assertEqual(result[1], "3600-7200")

    def test_proc_filters_with_error_raises_exception(self):
        """Test that _get_proc_filters raises exception on invalid input."""
        args = build_args(lp="job1", memory="invalid", duration="0.01")

        with self.assertRaises(ValueError):
            cueman_main._get_proc_filters(args)


class TestInputValidationBugFixes(unittest.TestCase):
    """Test fixes for input validation bugs reported in issue #1998."""

    def test_duration_double_dash_rejected(self):
        """Test that '2--5' format is rejected (issue #1998)."""
        args = build_args(lp="job1", memory="1", duration="2--5")

        result, _ = cueman_main._get_proc_filters(args)

        # Should return None for invalid input
        self.assertIsNone(result)

    def test_duration_multiple_values_rejected(self):
        """Test that '2-3-5' format is rejected (issue #1998)."""
        args = build_args(lp="job1", memory="1", duration="2-3-5")

        result, _ = cueman_main._get_proc_filters(args)

        # Should return None for invalid input
        self.assertIsNone(result)

    def test_duration_reversed_range_rejected(self):
        """Test that '5-2' format is rejected (min > max) (issue #1998)."""
        args = build_args(lp="job1", memory="1", duration="5-2")

        result, _ = cueman_main._get_proc_filters(args)

        # Should return None for invalid input
        self.assertIsNone(result)

    def test_duration_negative_value_rejected(self):
        """Test that negative duration is rejected (issue #1998)."""
        args = build_args(lp="job1", memory="1", duration="-5")

        result, _ = cueman_main._get_proc_filters(args)

        # Should return None for invalid input
        self.assertIsNone(result)

    def test_duration_negative_range_rejected(self):
        """Test that negative duration range is rejected (issue #1998)."""
        args = build_args(lp="job1", memory="1", duration="-2-5")

        result, _ = cueman_main._get_proc_filters(args)

        # Should return None for invalid input
        self.assertIsNone(result)

    def test_memory_double_dash_rejected(self):
        """Test that '2--5' memory format is rejected."""
        args = build_args(lp="job1", memory="2--5", duration="0.01")

        result, _ = cueman_main._get_proc_filters(args)

        # Should return None for invalid input
        self.assertIsNone(result)

    def test_memory_multiple_values_rejected(self):
        """Test that '2-3-5' memory format is rejected."""
        args = build_args(lp="job1", memory="2-3-5", duration="0.01")

        result, _ = cueman_main._get_proc_filters(args)

        # Should return None for invalid input
        self.assertIsNone(result)

    def test_memory_reversed_range_rejected(self):
        """Test that '5-2' memory format is rejected (min > max)."""
        args = build_args(lp="job1", memory="5-2", duration="0.01")

        result, _ = cueman_main._get_proc_filters(args)

        # Should return None for invalid input
        self.assertIsNone(result)

    @mock.patch("opencue.api.getProcs")
    def test_valid_duration_range_accepted(self, mock_getProcs):
        """Test that valid duration range '2-5' is accepted (issue #1998)."""
        args = build_args(lp="job1", memory="1", duration="2-5")
        mock_getProcs.return_value = []

        result, _ = cueman_main._get_proc_filters(args)

        # Should NOT return None for valid input
        self.assertIsNotNone(result)
        mock_getProcs.assert_called_once()

    @mock.patch("opencue.api.getProcs")
    def test_valid_duration_single_value_accepted(self, mock_getProcs):
        """Test that valid single duration '5' is accepted (issue #1998)."""
        args = build_args(lp="job1", memory="1", duration="5")
        mock_getProcs.return_value = []

        result, _ = cueman_main._get_proc_filters(args)

        # Should NOT return None for valid input
        self.assertIsNotNone(result)
        mock_getProcs.assert_called_once()


class TestBuildFrameSearchWithFilters(unittest.TestCase):
    """Test buildFrameSearch function with memory and duration filters."""

    @mock.patch("cueadmin.common.handleIntCriterion")
    def test_build_frame_search_with_memory_filter(self, mock_handleIntCriterion):
        """Test buildFrameSearch with memory filter."""
        # Mock the criterion object
        mock_criterion = mock.Mock()
        mock_criterion.value = 2097152
        mock_handleIntCriterion.return_value = [mock_criterion]

        args = build_args(lf="job1", memory="2", limit=1000)

        search = cueman_main.buildFrameSearch(args)

        # Memory should be converted and formatted
        self.assertIn("memory", search)
        self.assertEqual(search["limit"], 1000)

    @mock.patch("cueadmin.common.handleIntCriterion")
    def test_build_frame_search_with_duration_filter(self, mock_handleIntCriterion):
        """Test buildFrameSearch with duration filter."""
        # Mock the criterion object
        mock_criterion = mock.Mock()
        mock_criterion.value = 7200
        mock_handleIntCriterion.return_value = [mock_criterion]

        args = build_args(lf="job1", duration="2", limit=1000)

        search = cueman_main.buildFrameSearch(args)

        # Duration should be converted and formatted
        self.assertIn("duration", search)
        self.assertEqual(search["limit"], 1000)

    def test_build_frame_search_with_default_memory(self):
        """Test buildFrameSearch with default memory value."""
        args = build_args(lf="job1", memory=cueman_main.DEFAULT_MIN_MEMORY, limit=1000)

        search = cueman_main.buildFrameSearch(args)

        # Default memory should create a range from 0
        self.assertIn("memory", search)
        # Should be "0-<converted_value>"
        self.assertTrue(search["memory"].startswith("0-"))

    def test_build_frame_search_with_default_duration(self):
        """Test buildFrameSearch with default duration value."""
        args = build_args(lf="job1", duration=cueman_main.DEFAULT_MIN_DURATION, limit=1000)

        search = cueman_main.buildFrameSearch(args)

        # Default duration should create a range from 0
        self.assertIn("duration", search)
        # Should be "0-<converted_value>"
        self.assertTrue(search["duration"].startswith("0-"))

    @mock.patch("cueadmin.common.handleIntCriterion")
    def test_build_frame_search_combined_filters(self, mock_handleIntCriterion):
        """Test buildFrameSearch with multiple combined filters."""
        # Mock the criterion objects
        mock_criterion = mock.Mock()
        mock_criterion.value = 7200
        mock_handleIntCriterion.return_value = [mock_criterion]

        args = build_args(
            lf="job1",
            layer=["layer1"],
            range="1-100",
            state=["RUNNING"],
            memory="2",
            duration="2",
            page=2,
            limit=500
        )

        search = cueman_main.buildFrameSearch(args)

        # All filters should be present
        self.assertIn("layer", search)
        self.assertIn("range", search)
        self.assertIn("state", search)
        self.assertIn("memory", search)
        self.assertIn("duration", search)
        self.assertIn("page", search)
        self.assertIn("limit", search)
        self.assertEqual(search["page"], 2)
        self.assertEqual(search["limit"], 500)


if __name__ == "__main__":
    unittest.main()
