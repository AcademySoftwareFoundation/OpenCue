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


"""Unit tests for cueman main module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import os
import sys
import unittest
import warnings

import mock

# Suppress protobuf version warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf.runtime_version")

# Try different import paths for proto modules depending on environment
try:
    from opencue.compiled_proto import job_pb2
except ImportError:
    try:
        from opencue_proto import job_pb2
    except ImportError:
        # Create a mock module for testing if proto isn't available
        import types
        job_pb2 = types.ModuleType('job_pb2')
        job_pb2.RUNNING = 'RUNNING'
        job_pb2.WAITING = 'WAITING'
        job_pb2.DEAD = 'DEAD'
        job_pb2.SUCCEEDED = 'SUCCEEDED'
        # Add Order mock class
        job_pb2.Order = types.ModuleType('Order')
        job_pb2.Order.keys = lambda: ['FIRST', 'LAST', 'REVERSE']

# Add the parent directory to the path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cueman import main  # pylint: disable=wrong-import-position


class TestCuemanMain(unittest.TestCase):
    """Test cases for cueman main module functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = mock.Mock(spec=argparse.ArgumentParser)
        self.args = mock.Mock()

    def test_format_nargs_input_single_job(self):
        """Test formatting of single job name."""
        nargs_input = ["job1"]
        result = main.format_nargs_input(nargs_input)
        self.assertEqual(result, ["job1"])

    def test_format_nargs_input_comma_separated(self):
        """Test formatting of comma-separated job names."""
        nargs_input = ["job1,job2,job3"]
        result = main.format_nargs_input(nargs_input)
        self.assertEqual(result, ["job1", "job2", "job3"])

    def test_format_nargs_input_with_spaces(self):
        """Test formatting of comma-separated job names with spaces."""
        nargs_input = ["job1, job2, job3"]
        result = main.format_nargs_input(nargs_input)
        self.assertEqual(result, ["job1", "job2", "job3"])

    def test_buildFrameSearch_default(self):
        """Test building frame search with default values."""
        args = mock.Mock()
        args.layer = None
        args.range = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        with mock.patch('cueadmin.common.handleIntCriterion') as mock_handle:
            mock_handle.side_effect = [
                [mock.Mock(value=10485)],  # memory conversion
                [mock.Mock(value=36)]      # duration conversion
            ]
            result = main.buildFrameSearch(args)

        expected = {
            "memory": "0-10485",
            "duration": "0-36",
            "limit": 1000
        }
        self.assertEqual(result, expected)

    def test_buildFrameSearch_with_layer(self):
        """Test building frame search with layer filter."""
        args = mock.Mock()
        args.layer = ["layer1", "layer2"]
        args.range = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        result = main.buildFrameSearch(args)
        self.assertIn("layer", result)
        self.assertEqual(result["layer"], ["layer1", "layer2"])

    def test_buildFrameSearch_with_range(self):
        """Test building frame search with range filter."""
        args = mock.Mock()
        args.layer = None
        args.range = "1-100"
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        result = main.buildFrameSearch(args)
        self.assertIn("range", result)
        self.assertEqual(result["range"], "1-100")

    def test_buildFrameSearch_with_state(self):
        """Test building frame search with state filter."""
        args = mock.Mock()
        args.layer = None
        args.range = None
        args.state = ["RUNNING", "WAITING"]
        args.memory = 0.01
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        with mock.patch('cueadmin.common.Convert.strToFrameState') as mock_convert:
            mock_convert.side_effect = [
                job_pb2.RUNNING,
                job_pb2.WAITING
            ]
            result = main.buildFrameSearch(args)

        self.assertIn("state", result)
        self.assertEqual(len(result["state"]), 2)

    def test_buildFrameSearch_with_memory_range(self):
        """Test building frame search with memory range."""
        args = mock.Mock()
        args.layer = None
        args.range = None
        args.state = None
        args.memory = "2-4"
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        with mock.patch('cueadmin.common.handleIntCriterion') as mock_handle:
            mock_handle.return_value = [mock.Mock(value=2097152), mock.Mock(value=4194304)]
            result = main.buildFrameSearch(args)

        self.assertIn("memory", result)

    def test_buildFrameSearch_with_page(self):
        """Test building frame search with page number."""
        args = mock.Mock()
        args.layer = None
        args.range = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = 2
        args.limit = 1000

        result = main.buildFrameSearch(args)
        self.assertIn("page", result)
        self.assertEqual(result["page"], 2)

    @mock.patch('opencue.api.findJob')
    @mock.patch('opencue.api.findLayer')
    def test_staggerJob_with_layers(self, mock_findLayer, mock_findJob):
        """Test staggerJob function with specific layers."""
        mock_job = mock.Mock()
        mock_layer1 = mock.Mock()
        mock_layer2 = mock.Mock()

        mock_findJob.return_value = mock_job
        mock_findLayer.side_effect = [mock_layer1, mock_layer2]

        main.staggerJob(mock_job, ["layer1", "layer2"], "1-100", "5")

        mock_findLayer.assert_any_call(mock_job, "layer1")
        mock_findLayer.assert_any_call(mock_job, "layer2")
        mock_layer1.staggerFrames.assert_called_once_with("1-100", 5)
        mock_layer2.staggerFrames.assert_called_once_with("1-100", 5)

    def test_staggerJob_without_layers(self):
        """Test staggerJob function without specific layers."""
        mock_job = mock.Mock()

        main.staggerJob(mock_job, None, "1-100", "5")

        mock_job.staggerFrames.assert_called_once_with("1-100", 5)

    @mock.patch('opencue.api.findLayer')
    def test_reorderJob_with_valid_order(self, mock_findLayer):
        """Test reorderJob function with valid order."""
        mock_job = mock.Mock()
        mock_layer = mock.Mock()
        mock_findLayer.return_value = mock_layer

        # Mock the Order.keys() method to return valid orders
        with mock.patch.object(job_pb2, 'Order', create=True) as mock_order:
            mock_order.keys.return_value = ['FIRST', 'LAST', 'REVERSE']
            main.reorderJob(mock_job, ["layer1"], "1-100", "FIRST")

        mock_findLayer.assert_called_once_with(mock_job, "layer1")
        mock_layer.reorderFrames.assert_called_once_with("1-100", "FIRST")

    def test_reorderJob_with_invalid_order(self):
        """Test reorderJob function with invalid order."""
        mock_job = mock.Mock()

        with mock.patch.object(job_pb2, 'Order', create=True) as mock_order:
            mock_order.keys.return_value = ['FIRST', 'LAST', 'REVERSE']
            with self.assertRaises(ValueError) as cm:
                main.reorderJob(mock_job, None, "1-100", "INVALID")

        self.assertIn("Invalid ordering", str(cm.exception))

    @mock.patch('getpass.getuser')
    def test_terminateJobs(self, mock_getuser):
        """Test terminateJobs function."""
        mock_getuser.return_value = "testuser"
        mock_job1 = mock.Mock()
        mock_job1.name.return_value = "job1"
        mock_job2 = mock.Mock()
        mock_job2.name.return_value = "job2"

        jobs = [mock_job1, mock_job2]

        with mock.patch('sys.stdout'):
            main.terminateJobs(jobs)

        mock_job1.kill.assert_called_once_with(reason=main.KILL_REASON)
        mock_job2.kill.assert_called_once_with(reason=main.KILL_REASON)


class TestCuemanHandleArgs(unittest.TestCase):
    """Test cases for handleArgs function."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = mock.Mock()
        # Set all command flags to None by default
        self.args.lf = None
        self.args.lp = None
        self.args.ll = None
        self.args.info = None
        self.args.pause = None
        self.args.resume = None
        self.args.term = None
        self.args.eat = None
        self.args.kill = None
        self.args.retry = None
        self.args.done = None
        self.args.stagger = None
        self.args.reorder = None
        self.args.retries = None
        self.args.autoeaton = None
        self.args.autoeatoff = None
        self.args.force = False

    def test_handleArgs_no_command(self):
        """Test handleArgs when no command is provided."""
        # Mock all command attributes to None/False
        for cmd in ['lf', 'lp', 'll', 'info', 'pause', 'resume', 'term', 'eat',
                    'kill', 'retry', 'done', 'stagger', 'reorder', 'retries',
                    'autoeaton', 'autoeatoff']:
            setattr(self.args, cmd, None)

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

    @mock.patch('opencue.api.findJob')
    @mock.patch('cueadmin.output.displayFrames')
    def test_handleArgs_list_frames(self, mock_display, mock_findJob):
        """Test handleArgs with -lf flag."""
        self.args.lf = "test_job"
        mock_job = mock.Mock()
        mock_frames = ["frame1", "frame2"]
        mock_job.getFrames.return_value = mock_frames
        mock_findJob.return_value = mock_job

        main.handleArgs(self.args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.getFrames.assert_called_once()
        mock_display.assert_called_once_with(mock_frames)

    @mock.patch('opencue.api.findJob')
    @mock.patch('cueadmin.output.displayJobInfo')
    def test_handleArgs_info(self, mock_display, mock_findJob):
        """Test handleArgs with -info flag."""
        self.args.info = "test_job"
        mock_job = mock.Mock()
        mock_findJob.return_value = mock_job

        main.handleArgs(self.args)

        mock_findJob.assert_called_once_with("test_job")
        mock_display.assert_called_once_with(mock_job)

    @mock.patch('opencue.api.findJob')
    def test_handleArgs_pause(self, mock_findJob):
        """Test handleArgs with -pause flag."""
        self.args.pause = ["job1,job2"]

        mock_job1 = mock.Mock()
        mock_job1.isPaused.return_value = False
        mock_job1.name.return_value = "job1"
        mock_job1.pause = mock.Mock()

        mock_job2 = mock.Mock()
        mock_job2.isPaused.return_value = True
        mock_job2.name.return_value = "job2"
        mock_job2.pause = mock.Mock()

        mock_findJob.side_effect = [mock_job1, mock_job2]

        with mock.patch('sys.stdout'):
            main.handleArgs(self.args)

        self.assertEqual(mock_findJob.call_count, 2)
        mock_job1.pause.assert_called_once()
        self.assertEqual(mock_job2.pause.call_count, 0)


if __name__ == '__main__':
    unittest.main()
