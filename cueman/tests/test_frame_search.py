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
Unit tests for buildFrameSearch function in cueman.main
"""
import unittest
from unittest import mock

from cueman import main

try:
    from opencue.compiled_proto import job_pb2
except ImportError:
    try:
        from opencue_proto import job_pb2
    except ImportError:
        # pylint: disable=too-few-public-methods
        class JobPb2Mock:
            """Mock class for job_pb2 when it's not available."""
            RUNNING = 'RUNNING'
            WAITING = 'WAITING'
        job_pb2 = JobPb2Mock()

class TestBuildFrameSearch(unittest.TestCase):
    """Test cases for the buildFrameSearch function in cueman.main."""
    def setUp(self):
        """Set up test fixtures with default arguments."""
        self.default_args = mock.Mock()
        self.default_args.layer = None
        self.default_args.range = None
        self.default_args.state = None
        self.default_args.memory = 0.01
        self.default_args.duration = 0.01
        self.default_args.page = None
        self.default_args.limit = 1000

    def test_default_search(self):
        """Test default search construction with default memory and duration."""
        with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
            mock_handle.side_effect = [
                [mock.Mock(value=10485)],
                [mock.Mock(value=36)],
            ]
            result = main.buildFrameSearch(self.default_args)
        expected = {"memory": "0-10485", "duration": "0-36", "limit": 1000}
        self.assertEqual(result, expected)

    def test_layer_filter(self):
        """Test layer filter integration with single and multiple layers."""
        args = mock.Mock(**self.default_args.__dict__)
        args.layer = ["layer1", "layer2"]
        result = main.buildFrameSearch(args)
        self.assertIn("layer", result)
        self.assertEqual(result["layer"], ["layer1", "layer2"])

    def test_range_filter(self):
        """Test range filter validation for frame ranges."""
        args = mock.Mock(**self.default_args.__dict__)
        args.range = "1-100"
        result = main.buildFrameSearch(args)
        self.assertIn("range", result)
        self.assertEqual(result["range"], "1-100")

    def test_state_filter_conversion(self):
        """Test state filter conversion from string to proper state enum."""
        args = mock.Mock(**self.default_args.__dict__)
        args.state = ["RUNNING", "WAITING"]
        with mock.patch("cueadmin.common.Convert.strToFrameState") as mock_convert:
            mock_convert.side_effect = [job_pb2.RUNNING, job_pb2.WAITING]
            result = main.buildFrameSearch(args)
        self.assertIn("state", result)
        self.assertEqual(result["state"], [job_pb2.RUNNING, job_pb2.WAITING])

    def test_memory_filter(self):
        """Test memory filter application with range and conversion."""
        args = mock.Mock(**self.default_args.__dict__)
        args.memory = "2-4"
        with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
            mock_handle.return_value = [
                mock.Mock(value=2097152),
                mock.Mock(value=4194304),
            ]
            result = main.buildFrameSearch(args)
        self.assertIn("memory", result)
        self.assertEqual(result["memory"], "4194304")

    def test_duration_filter(self):
        """Test duration filter application with range and conversion."""
        args = mock.Mock(**self.default_args.__dict__)
        args.duration = "1-2"
        with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
            mock_handle.return_value = [
                mock.Mock(value=3600),
                mock.Mock(value=7200),
            ]
            result = main.buildFrameSearch(args)
        self.assertIn("duration", result)
        self.assertEqual(result["duration"], "7200")

    def test_pagination_inclusion(self):
        """Test that page number is included in search parameters."""
        args = mock.Mock(**self.default_args.__dict__)
        args.page = 2
        result = main.buildFrameSearch(args)
        self.assertIn("page", result)
        self.assertEqual(result["page"], 2)

    def test_limit_inclusion(self):
        """Test that result limit is correctly handled."""
        args = mock.Mock(**self.default_args.__dict__)
        args.limit = 500
        result = main.buildFrameSearch(args)
        self.assertIn("limit", result)
        self.assertEqual(result["limit"], 500)

    def test_empty_filters(self):
        """Test that function returns empty dict when no filters are provided."""
        args = mock.Mock()
        args.layer = None
        args.range = None
        args.state = None
        args.memory = None
        args.duration = None
        args.page = None
        args.limit = None
        result = main.buildFrameSearch(args)
        self.assertEqual(result, {})

    def test_single_layer_filter(self):
        """Test layer filter with a single layer."""
        args = mock.Mock(**self.default_args.__dict__)
        args.layer = ["single_layer"]
        result = main.buildFrameSearch(args)
        self.assertIn("layer", result)
        self.assertEqual(result["layer"], ["single_layer"])

    def test_memory_filter_no_results(self):
        """Test memory filter when handleIntCriterion returns None."""
        args = mock.Mock(**self.default_args.__dict__)
        args.memory = "invalid"
        with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
            mock_handle.return_value = None
            result = main.buildFrameSearch(args)
        self.assertNotIn("memory", result)

    def test_duration_filter_no_results(self):
        """Test duration filter when handleIntCriterion returns None."""
        args = mock.Mock(**self.default_args.__dict__)
        args.duration = "invalid"
        with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
            mock_handle.return_value = None
            result = main.buildFrameSearch(args)
        self.assertNotIn("duration", result)

    def test_combined_filters(self):
        """Test multiple filters applied simultaneously."""
        args = mock.Mock()
        args.layer = ["layer1"]
        args.range = "1-50"
        args.state = ["RUNNING"]
        args.memory = 2.0
        args.duration = 1.0
        args.page = 1
        args.limit = 100

        with mock.patch("cueadmin.common.Convert.strToFrameState") as mock_convert, \
             mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
            mock_convert.return_value = job_pb2.RUNNING
            mock_handle.side_effect = [
                [mock.Mock(value=2097152)],  # memory
                [mock.Mock(value=3600)],      # duration
            ]
            result = main.buildFrameSearch(args)

        self.assertIn("layer", result)
        self.assertIn("range", result)
        self.assertIn("state", result)
        self.assertIn("memory", result)
        self.assertIn("duration", result)
        self.assertIn("page", result)
        self.assertIn("limit", result)
        self.assertEqual(result["layer"], ["layer1"])
        self.assertEqual(result["range"], "1-50")
        self.assertEqual(result["state"], [job_pb2.RUNNING])
        self.assertEqual(result["memory"], "2097152")
        self.assertEqual(result["duration"], "3600")
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["limit"], 100)

    def test_state_single_value(self):
        """Test state filter with a single state value."""
        args = mock.Mock(**self.default_args.__dict__)
        args.state = ["RUNNING"]
        with mock.patch("cueadmin.common.Convert.strToFrameState") as mock_convert:
            mock_convert.return_value = job_pb2.RUNNING
            result = main.buildFrameSearch(args)
        self.assertIn("state", result)
        self.assertEqual(result["state"], [job_pb2.RUNNING])

    def test_memory_filter_empty_list(self):
        """Test memory filter when handleIntCriterion returns an empty list."""
        args = mock.Mock(**self.default_args.__dict__)
        args.memory = 0
        with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
            mock_handle.return_value = []
            result = main.buildFrameSearch(args)
        self.assertNotIn("memory", result)

    def test_duration_filter_empty_list(self):
        """Test duration filter when handleIntCriterion returns an empty list."""
        args = mock.Mock(**self.default_args.__dict__)
        args.duration = 0
        with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
            mock_handle.return_value = []
            result = main.buildFrameSearch(args)
        self.assertNotIn("duration", result)

if __name__ == "__main__":
    unittest.main()
