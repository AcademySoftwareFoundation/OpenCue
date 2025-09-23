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
Unit tests for displayLayers formatting in cueman.
"""

from __future__ import absolute_import, division, print_function

import io
import os
import sys
import unittest
import warnings

import mock

# Suppress protobuf version warnings
warnings.filterwarnings(
    "ignore", category=UserWarning, module="google.protobuf.runtime_version"
)

# Add the parent directory to the path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cueman import main  # pylint: disable=wrong-import-position


class TestDisplayLayers(unittest.TestCase):
    """Test cases for displayLayers formatting function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_job = mock.Mock()
        self.mock_job.data.name = "TestJob"

    def _capture_output(self, job):
        """Helper method to capture stdout output from displayLayers.

        Args:
            job: Mock job object to pass to displayLayers

        Returns:
            Captured output as a string
        """
        captured = io.StringIO()
        sys_stdout = sys.stdout
        sys.stdout = captured
        try:
            main.displayLayers(job)
        finally:
            sys.stdout = sys_stdout
        return captured.getvalue()

    def test_header_and_alignment(self):
        """Test that header is properly formatted and columns are aligned."""
        layer = mock.Mock()
        layer.data.name = "Layer1"
        layer.data.layer_stats.total_frames = 10
        layer.data.layer_stats.succeeded_frames = 5
        layer.data.layer_stats.running_frames = 2
        layer.data.layer_stats.waiting_frames = 2
        layer.data.layer_stats.dead_frames = 1
        layer.data.tags = ["tagA", "tagB"]
        self.mock_job.getLayers.return_value = [layer]
        output = self._capture_output(self.mock_job)

        # Check header presence
        self.assertIn("Layer", output)
        self.assertIn("Total", output)
        self.assertIn("Done", output)
        self.assertIn("Running", output)
        self.assertIn("Waiting", output)
        self.assertIn("Failed", output)

        # Check layer data
        self.assertIn("Layer1", output)
        self.assertIn("tags: tagA | tagB", output)

    def test_layer_name_truncation(self):
        """Test that long layer names are truncated to 29 characters."""
        long_name = "L" * 40
        layer = mock.Mock()
        layer.data.name = long_name
        layer.data.layer_stats.total_frames = 1
        layer.data.layer_stats.succeeded_frames = 1
        layer.data.layer_stats.running_frames = 0
        layer.data.layer_stats.waiting_frames = 0
        layer.data.layer_stats.dead_frames = 0
        layer.data.tags = []
        self.mock_job.getLayers.return_value = [layer]
        output = self._capture_output(self.mock_job)

        # Should contain first 29 characters
        self.assertIn(long_name[:29], output)
        # Should not contain the full 40-character name
        self.assertNotIn(long_name, output)

    def test_frame_statistics_display(self):
        """Test that frame statistics are correctly displayed."""
        layer = mock.Mock()
        layer.data.name = "StatsLayer"
        layer.data.layer_stats.total_frames = 20
        layer.data.layer_stats.succeeded_frames = 10
        layer.data.layer_stats.running_frames = 5
        layer.data.layer_stats.waiting_frames = 3
        layer.data.layer_stats.dead_frames = 2
        layer.data.tags = []
        self.mock_job.getLayers.return_value = [layer]
        output = self._capture_output(self.mock_job)

        # Check all statistics are present
        self.assertIn("20", output)  # total
        self.assertIn("10", output)  # succeeded
        self.assertIn("5", output)   # running
        self.assertIn("3", output)   # waiting
        self.assertIn("2", output)   # dead/failed

    def test_tag_display_formatting(self):
        """Test that tags are formatted with pipe separators."""
        layer = mock.Mock()
        layer.data.name = "TagLayer"
        layer.data.layer_stats.total_frames = 1
        layer.data.layer_stats.succeeded_frames = 1
        layer.data.layer_stats.running_frames = 0
        layer.data.layer_stats.waiting_frames = 0
        layer.data.layer_stats.dead_frames = 0
        layer.data.tags = ["tag1", "tag2", "tag3"]
        self.mock_job.getLayers.return_value = [layer]
        output = self._capture_output(self.mock_job)

        # Check tags formatting
        self.assertIn("tags: tag1 | tag2 | tag3", output)

    def test_empty_layer_handling(self):
        """Test handling of jobs with no layers."""
        self.mock_job.getLayers.return_value = []
        output = self._capture_output(self.mock_job)

        # Should show 0 layers message
        self.assertIn("Job: TestJob has 0 layers", output)

    def test_large_dataset_formatting(self):
        """Test formatting with many layers."""
        layers = []
        for i in range(30):
            layer = mock.Mock()
            layer.data.name = f"Layer{i}"
            layer.data.layer_stats.total_frames = i
            layer.data.layer_stats.succeeded_frames = i // 2
            layer.data.layer_stats.running_frames = i // 4
            layer.data.layer_stats.waiting_frames = i // 8
            layer.data.layer_stats.dead_frames = i % 3
            layer.data.tags = []
            layers.append(layer)
        self.mock_job.getLayers.return_value = layers
        output = self._capture_output(self.mock_job)

        # Check job summary
        self.assertIn("Job: TestJob has 30 layers", output)
        # Check first and last layers are present
        self.assertIn("Layer0", output)
        self.assertIn("Layer29", output)

    def test_unicode_layer_name(self):
        """Test handling of Unicode characters in layer names and tags."""
        layer = mock.Mock()
        layer.data.name = "LäyerÜñîçødë"
        layer.data.layer_stats.total_frames = 1
        layer.data.layer_stats.succeeded_frames = 1
        layer.data.layer_stats.running_frames = 0
        layer.data.layer_stats.waiting_frames = 0
        layer.data.layer_stats.dead_frames = 0
        layer.data.tags = ["täg"]
        self.mock_job.getLayers.return_value = [layer]
        output = self._capture_output(self.mock_job)

        # Check Unicode handling
        self.assertIn("LäyerÜñîçødë", output)
        self.assertIn("täg", output)


if __name__ == "__main__":
    unittest.main()
