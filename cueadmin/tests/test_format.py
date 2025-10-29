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


"""Tests for cueadmin.format."""


from __future__ import absolute_import, division, print_function

import sys
import time
import unittest
from unittest import mock

import cueadmin.format as fmt


class FmtTests(unittest.TestCase):
    """Test class for the format module with different test scenarios than format_tests.py."""

    def test_format_time_epoch_edge_cases(self):
        """Test formatTime with epoch edge cases."""
        specific_dates = [(1234567890, "02/13 23:31"), (2147483647, "01/19 03:14")]
        for epoch, _ in specific_dates:
            local_expected = time.strftime("%m/%d %H:%M", time.localtime(epoch))
            self.assertEqual(fmt.formatTime(epoch), local_expected)
        self.assertEqual(fmt.formatTime(0), "--/-- --:--")

    def test_format_time_with_fractional_seconds(self):
        """Test formatTime with fractional seconds in epoch."""
        epoch = 1600000000.75
        expected = time.strftime("%m/%d %H:%M", time.localtime(int(epoch)))
        self.assertEqual(fmt.formatTime(epoch), expected)

    def test_format_time_custom_formats_date_components(self):
        """Test formatTime with various date component formats."""
        # Fixed epoch for September 15, 2020
        epoch = 1600128000

        # Generate expected values dynamically based on local timezone
        local_time = time.localtime(epoch)

        formats = [
            # Year formats
            ("%Y", time.strftime("%Y", local_time)),
            ("%y", time.strftime("%y", local_time)),
            # Month formats
            ("%m", time.strftime("%m", local_time)),
            ("%B", time.strftime("%B", local_time)),
            ("%b", time.strftime("%b", local_time)),
            # Day formats
            ("%d", time.strftime("%d", local_time)),
            ("%j", time.strftime("%j", local_time)),
            ("%A", time.strftime("%A", local_time)),
            ("%a", time.strftime("%a", local_time)),
        ]

        for format_str, expected in formats:
            result = fmt.formatTime(epoch, time_format=format_str)
            self.assertEqual(result, expected)

    def test_format_time_custom_formats_time_components(self):
        """Test formatTime with various time component formats."""
        # Fixed epoch for 3:45:30 PM
        epoch = 1600188330

        formats = [
            # Hour formats
            ("%H", "15"),  # 24-hour (00-23)
            ("%I", "03"),  # 12-hour (01-12)
            ("%p", "PM"),  # AM/PM
            # Minute and second formats
            ("%M", "45"),  # Minutes (00-59)
            ("%S", "30"),  # Seconds (00-59)
        ]

        for format_str, _ in formats:
            local_expected = time.strftime(format_str, time.localtime(epoch))
            result = fmt.formatTime(epoch, time_format=format_str)
            self.assertEqual(result, local_expected)

    def test_format_time_with_different_default_values(self):
        """Test formatTime with various default values."""
        defaults = [
            "",  # Empty string
            "No timestamp",  # Plain text
            "N/A",  # Common abbreviation
            "00/00 00:00",  # Formatted like time
            "❓❓",  # Unicode characters
        ]

        for default_val in defaults:
            self.assertEqual(fmt.formatTime(0, default=default_val), default_val)
            self.assertEqual(fmt.formatTime(None, default=default_val), default_val)

    @mock.patch("time.time")
    def test_find_duration_with_mocked_time(self, mock_time):
        """Test findDuration with various scenarios using mocked time."""
        # Mock current time
        mock_time.return_value = 10000

        # Test when stop time is missing or invalid
        self.assertEqual(fmt.findDuration(9000, 0), 1000)
        self.assertEqual(fmt.findDuration(9000, -1), 1000)

        # Test with both positive times
        self.assertEqual(fmt.findDuration(1000, 2000), 1000)

        # Test with stop < start (actual behavior returns negative value)
        self.assertEqual(fmt.findDuration(5000, 3000), -2000)

    def test_format_duration_precision_edge_cases(self):
        """Test formatDuration with specific times to check precision handling."""
        # Test with various second values to ensure proper formatting
        second_cases = [
            (0, "00:00:00"),
            (1, "00:00:01"),
            (59, "00:00:59"),
            (60, "00:01:00"),
            (61, "00:01:01"),
        ]

        for seconds, expected in second_cases:
            self.assertEqual(fmt.formatDuration(seconds), expected)

        # Test minute handling
        minute_cases = [
            (60, "00:01:00"),
            (120, "00:02:00"),
            (3599, "00:59:59"),
            (3600, "01:00:00"),
            (3601, "01:00:01"),
        ]

        for seconds, expected in minute_cases:
            self.assertEqual(fmt.formatDuration(seconds), expected)

        # Test hour handling for large values
        hour_cases = [
            (3600, "01:00:00"),
            (7200, "02:00:00"),
            (86399, "23:59:59"),
            (86400, "24:00:00"),
            (86401, "24:00:01"),
            (172800, "48:00:00"),
            (172801, "48:00:01"),
        ]

        for seconds, expected in hour_cases:
            self.assertEqual(fmt.formatDuration(seconds), expected)

    def test_format_duration_with_floating_point(self):
        """Test formatDuration with floating-point seconds."""
        # Test floating-point handling (should truncate to integer)
        float_cases = [
            (0.9, "00:00:00"),
            (59.9, "00:00:59"),
            (60.1, "00:01:00"),
            (3599.9, "00:59:59"),
            (3600.1, "01:00:00"),
        ]

        for seconds, expected in float_cases:
            self.assertEqual(fmt.formatDuration(seconds), expected)

    def test_format_duration_with_extreme_values(self):
        """Test formatDuration with extremely large values."""
        # Test with very large values
        large_cases = [
            (86400 * 7, "168:00:00"),  # 1 week
            (86400 * 30, "720:00:00"),  # ~1 month
            (86400 * 365, "8760:00:00"),  # ~1 year
            (86400 * 365 * 10, "87600:00:00"),  # ~10 years
            (
                sys.maxsize,
                f"{sys.maxsize // 3600}:{(sys.maxsize % 3600) // 60:02d}:{sys.maxsize % 60:02d}",
            ),
        ]

        for seconds, expected in large_cases:
            self.assertEqual(fmt.formatDuration(seconds), expected)

    def test_format_long_duration_precision_edge_cases(self):
        """Test formatLongDuration with specific times to check precision handling."""
        # Verify day calculation
        day_cases = [
            (0, "00:00"),  # 0 seconds
            (3599, "00:00"),  # 59 minutes, 59 seconds
            (3600, "00:01"),  # 1 hour
            (7199, "00:01"),  # 1 hour, 59 minutes, 59 seconds
            (7200, "00:02"),  # 2 hours
            (86399, "00:23"),  # 23 hours, 59 minutes, 59 seconds
            (86400, "01:00"),  # 1 day
            (86400 + 3600, "01:01"),  # 1 day, 1 hour
            (86400 + 3600 * 23, "01:23"),  # 1 day, 23 hours
            (
                86400 + 3600 * 23 + 3599,
                "01:23",
            ),  # 1 day, 23 hours, 59 minutes, 59 seconds
        ]

        for seconds, expected in day_cases:
            self.assertEqual(fmt.formatLongDuration(seconds), expected)

    def test_format_long_duration_with_floating_point(self):
        """Test formatLongDuration with floating-point seconds."""
        # Test floating-point handling (should truncate to integer)
        float_cases = [
            (3599.9, "00:00"),
            (3600.1, "00:01"),
            (86399.9, "00:23"),
            (86400.1, "01:00"),
        ]

        for seconds, expected in float_cases:
            self.assertEqual(fmt.formatLongDuration(seconds), expected)

    def test_format_long_duration_with_extreme_values(self):
        """Test formatLongDuration with extremely large values."""
        # Test with very large values
        large_cases = [
            (86400 * 7, "07:00"),
            (86400 * 30, "30:00"),
            (86400 * 365, "365:00"),
            (86400 * 365 * 10, "3650:00"),
            (
                sys.maxsize,
                f"{sys.maxsize // 86400}:{(sys.maxsize % 86400) // 3600:02d}",
            ),
        ]

        for seconds, expected in large_cases:
            self.assertEqual(fmt.formatLongDuration(seconds), expected)

    def test_format_mem_conversion_precision(self):
        """Test formatMem with values at unit boundaries to verify precision."""
        # KB to MB boundary tests
        kb_to_mb_cases = [
            (1023, "1023K"),
            (1024, "1M"),
            (1025, "1M"),
            (1536, "1M"),
            (2047, "1M"),
            (2048, "2M"),
        ]

        for kmem, expected in kb_to_mb_cases:
            self.assertEqual(fmt.formatMem(kmem), expected)

        # MB to GB boundary tests
        mb_to_gb_cases = [
            (1024 * 1024 - 1, "1023M"),
            (1024 * 1024, "1.0G"),
            (1024 * 1024 + 1, "1.0G"),
            (1024 * 1024 * 1.5, "1.5G"),
            (1024 * 1024 * 2 - 1, "2.0G"),
            (1024 * 1024 * 2, "2.0G"),
        ]

        for kmem, expected in mb_to_gb_cases:
            self.assertEqual(fmt.formatMem(kmem), expected)

    def test_format_mem_force_unit_edge_cases(self):
        """Test formatMem with forced units at various sizes."""
        # Test with KB on larger values
        kb_cases = [(512, "512K"), (1024, "1024K"), (1024 * 1024, "1048576K")]

        for kmem, expected in kb_cases:
            self.assertEqual(fmt.formatMem(kmem, unit="K"), expected)

        # Test with MB on values
        mb_cases = [(512, "0M"), (1024, "1M"), (1024 * 1024, "1024M")]

        for kmem, expected in mb_cases:
            self.assertEqual(fmt.formatMem(kmem, unit="M"), expected)

        gb_cases = [(512, "0.0G"), (1024 * 1024, "1.0G"), (1024 * 1024 * 2, "2.0G")]

        for kmem, expected in gb_cases:
            self.assertEqual(fmt.formatMem(kmem, unit="G"), expected)

    def test_format_mem_with_decimal_inputs(self):
        """Test formatMem with decimal/floating point inputs."""
        # Test with decimal inputs
        decimal_cases = [(512.5, "512K"), (1024.5, "1M"), (1024 * 1024 + 0.5, "1.0G")]

        for kmem, expected in decimal_cases:
            self.assertEqual(fmt.formatMem(kmem), expected)

    def test_cutoff_edge_cases(self):
        """Test cutoff function edge cases."""
        self.assertEqual(fmt.cutoff("", 5), "")

        # Shorter than cutoff
        self.assertEqual(fmt.cutoff("12", 5), "12")
        self.assertEqual(fmt.cutoff("abc", 6), "abc")

        # At or above cutoff threshold
        self.assertEqual(fmt.cutoff("123", 5), "123..")
        self.assertEqual(fmt.cutoff("1234", 4), "12..")
        self.assertEqual(fmt.cutoff("123", 3), "1..")
        self.assertEqual(fmt.cutoff("12345", 5), "123..")

        # Very small lengths
        self.assertEqual(fmt.cutoff("a", 1), "..")
        self.assertEqual(fmt.cutoff("ab", 2), "..")

        # Length 0
        self.assertEqual(fmt.cutoff("anything", 0), "anythi..")

        # Whitespace and special characters
        self.assertEqual(fmt.cutoff("   abc", 5), "   ..")
        self.assertEqual(fmt.cutoff("!@#$%^", 4), "!@..")

        # Length greater than string
        self.assertEqual(fmt.cutoff("short", 10), "short")

        # Length equal to string
        self.assertEqual(fmt.cutoff("exact", 5), "exa..")


if __name__ == "__main__":
    unittest.main()
