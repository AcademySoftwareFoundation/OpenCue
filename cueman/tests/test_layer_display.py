"""
Unit tests for displayLayers formatting in cueman.
"""

import unittest
from unittest import mock
import os
import sys
import io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cueman import main

class TestDisplayLayers(unittest.TestCase):
    def setUp(self):
        self.mock_job = mock.Mock()
        self.mock_job.data.name = "TestJob"

    def _capture_output(self, job):
        captured = io.StringIO()
        sys_stdout = sys.stdout
        sys.stdout = captured
        try:
            main.displayLayers(job)
        finally:
            sys.stdout = sys_stdout
        return captured.getvalue()

    def test_header_and_alignment(self):
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
        self.assertIn("Layer1", output)
        self.assertIn("tags: tagA | tagB", output)

    def test_layer_name_truncation(self):
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
        self.assertIn(long_name[:29], output)
        self.assertNotIn(long_name, output)

    def test_frame_statistics_display(self):
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
        self.assertIn("20", output)
        self.assertIn("10", output)
        self.assertIn("5", output)
        self.assertIn("3", output)
        self.assertIn("2", output)

    def test_tag_display_formatting(self):
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
        self.assertIn("tags: tag1 | tag2 | tag3", output)

    def test_empty_layer_handling(self):
        self.mock_job.getLayers.return_value = []
        output = self._capture_output(self.mock_job)
        self.assertIn("Job: TestJob has 0 layers", output)

    def test_large_dataset_formatting(self):
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
        self.assertIn("Job: TestJob has 30 layers", output)
        self.assertIn("Layer0", output)
        self.assertIn("Layer29", output)

    def test_unicode_layer_name(self):
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
        self.assertIn("LäyerÜñîçødë", output)
        self.assertIn("täg", output)

if __name__ == "__main__":
    unittest.main()
