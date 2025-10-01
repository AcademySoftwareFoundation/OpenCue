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


"""Unit tests for cueman command line argument parsing."""

from __future__ import absolute_import, division, print_function

import argparse
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


class TestArgumentParser(unittest.TestCase):
    """Test cases for command line argument parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.original_argv = sys.argv

    def tearDown(self):
        """Clean up after tests."""
        sys.argv = self.original_argv

    def parse_args(self, argv):
        """Helper method to parse arguments.

        Args:
            argv: List of command line arguments

        Returns:
            Parsed arguments object
        """
        parser = argparse.ArgumentParser()

        # Add general options
        general = parser.add_argument_group("General Options")
        general.add_argument(
            "-server", action="store", nargs="+", metavar="HOSTNAME"
        )
        general.add_argument("-facility", action="store", metavar="CODE")
        general.add_argument("-verbose", "-v", action="store_true")
        general.add_argument("-force", action="store_true")
        general.add_argument("--version", action="version", version="test 1.0")

        # Add query options
        query = parser.add_argument_group("Query Options")
        query.add_argument("-lf", action="store")
        query.add_argument("-lp", "-lap", action="store", metavar="JOB")
        query.add_argument("-ll", action="store", metavar="JOB")

        query_options = parser.add_argument_group("Frame Query Options")
        query_options.add_argument("-state", action="store", nargs="+")
        query_options.add_argument("-range", action="store")
        query_options.add_argument("-layer", action="store", nargs="+")
        query_options.add_argument("-page", action="store", type=int)
        query_options.add_argument("-limit", action="store", type=int, default=1000)
        query_options.add_argument("-duration", action="store", default=0.01)
        query_options.add_argument("-memory", action="store", default=0.01)

        # Job Options
        job = parser.add_argument_group("Job Options")
        job.add_argument("-info", action="store", metavar="JOB")
        job.add_argument("-pause", "--pause", action="store", nargs="+", metavar="JOB")
        job.add_argument("-resume", "--resume", action="store", nargs="+", metavar="JOB")
        job.add_argument("-term", action="store", nargs="+", metavar="JOB")
        job.add_argument("-eat", action="store")
        job.add_argument("-kill", action="store")
        job.add_argument("-retry", action="store")
        job.add_argument("-done", action="store")
        job.add_argument("-stagger", action="store", nargs=3)
        job.add_argument("-reorder", action="store", nargs=3)
        job.add_argument("-retries", action="store", nargs=2)
        job.add_argument("-autoeaton", action="store", nargs="+", metavar="JOB")
        job.add_argument("-autoeatoff", action="store", nargs="+", metavar="JOB")

        return parser.parse_args(argv)

    def test_no_arguments(self):
        """Test parser with no arguments."""
        args = self.parse_args([])
        self.assertIsNone(args.lf)
        self.assertIsNone(args.lp)
        self.assertIsNone(args.ll)
        self.assertIsNone(args.info)
        self.assertFalse(args.verbose)
        self.assertFalse(args.force)

    def test_list_frames_flag(self):
        """Test -lf flag parsing."""
        args = self.parse_args(["-lf", "test_job"])
        self.assertEqual(args.lf, "test_job")

    def test_list_procs_flag(self):
        """Test -lp flag parsing."""
        args = self.parse_args(["-lp", "test_job"])
        self.assertEqual(args.lp, "test_job")

    def test_list_procs_lap_alias(self):
        """Test -lap alias for -lp flag."""
        args = self.parse_args(["-lap", "test_job"])
        self.assertEqual(args.lp, "test_job")

    def test_list_layers_flag(self):
        """Test -ll flag parsing."""
        args = self.parse_args(["-ll", "test_job"])
        self.assertEqual(args.ll, "test_job")

    def test_info_flag(self):
        """Test -info flag parsing."""
        args = self.parse_args(["-info", "test_job"])
        self.assertEqual(args.info, "test_job")

    def test_pause_flag_single_job(self):
        """Test -pause flag with single job."""
        args = self.parse_args(["-pause", "test_job"])
        self.assertEqual(args.pause, ["test_job"])

    def test_pause_flag_multiple_jobs(self):
        """Test -pause flag with multiple jobs."""
        args = self.parse_args(["-pause", "job1", "job2", "job3"])
        self.assertEqual(args.pause, ["job1", "job2", "job3"])

    def test_pause_long_flag(self):
        """Test --pause long flag parsing."""
        args = self.parse_args(["--pause", "test_job"])
        self.assertEqual(args.pause, ["test_job"])

    def test_resume_flag(self):
        """Test -resume flag parsing."""
        args = self.parse_args(["-resume", "test_job"])
        self.assertEqual(args.resume, ["test_job"])

    def test_resume_long_flag(self):
        """Test --resume long flag parsing."""
        args = self.parse_args(["--resume", "test_job"])
        self.assertEqual(args.resume, ["test_job"])

    def test_term_flag(self):
        """Test -term flag parsing."""
        args = self.parse_args(["-term", "test_job"])
        self.assertEqual(args.term, ["test_job"])

    def test_term_flag_multiple_jobs(self):
        """Test -term flag with multiple jobs."""
        args = self.parse_args(["-term", "job1", "job2"])
        self.assertEqual(args.term, ["job1", "job2"])

    def test_eat_flag(self):
        """Test -eat flag parsing."""
        args = self.parse_args(["-eat", "test_job"])
        self.assertEqual(args.eat, "test_job")

    def test_kill_flag(self):
        """Test -kill flag parsing."""
        args = self.parse_args(["-kill", "test_job"])
        self.assertEqual(args.kill, "test_job")

    def test_retry_flag(self):
        """Test -retry flag parsing."""
        args = self.parse_args(["-retry", "test_job"])
        self.assertEqual(args.retry, "test_job")

    def test_done_flag(self):
        """Test -done flag parsing."""
        args = self.parse_args(["-done", "test_job"])
        self.assertEqual(args.done, "test_job")

    def test_stagger_flag(self):
        """Test -stagger flag parsing."""
        args = self.parse_args(["-stagger", "test_job", "1-100", "5"])
        self.assertEqual(args.stagger, ["test_job", "1-100", "5"])

    def test_stagger_flag_missing_args(self):
        """Test -stagger flag with missing arguments."""
        with self.assertRaises(SystemExit):
            self.parse_args(["-stagger", "test_job", "1-100"])

    def test_reorder_flag(self):
        """Test -reorder flag parsing."""
        args = self.parse_args(["-reorder", "test_job", "1-100", "FIRST"])
        self.assertEqual(args.reorder, ["test_job", "1-100", "FIRST"])

    def test_reorder_flag_missing_args(self):
        """Test -reorder flag with missing arguments."""
        with self.assertRaises(SystemExit):
            self.parse_args(["-reorder", "test_job"])

    def test_retries_flag(self):
        """Test -retries flag parsing."""
        args = self.parse_args(["-retries", "test_job", "3"])
        self.assertEqual(args.retries, ["test_job", "3"])

    def test_retries_flag_missing_count(self):
        """Test -retries flag with missing count argument."""
        with self.assertRaises(SystemExit):
            self.parse_args(["-retries", "test_job"])

    def test_autoeaton_flag(self):
        """Test -autoeaton flag parsing."""
        args = self.parse_args(["-autoeaton", "test_job"])
        self.assertEqual(args.autoeaton, ["test_job"])

    def test_autoeaton_flag_multiple_jobs(self):
        """Test -autoeaton flag with multiple jobs."""
        args = self.parse_args(["-autoeaton", "job1", "job2"])
        self.assertEqual(args.autoeaton, ["job1", "job2"])

    def test_autoeatoff_flag(self):
        """Test -autoeatoff flag parsing."""
        args = self.parse_args(["-autoeatoff", "test_job"])
        self.assertEqual(args.autoeatoff, ["test_job"])

    def test_verbose_flag_short(self):
        """Test -v short verbose flag."""
        args = self.parse_args(["-v", "-info", "test_job"])
        self.assertTrue(args.verbose)

    def test_verbose_flag_long(self):
        """Test -verbose long flag."""
        args = self.parse_args(["-verbose", "-info", "test_job"])
        self.assertTrue(args.verbose)

    def test_force_flag(self):
        """Test -force flag parsing."""
        args = self.parse_args(["-force", "-term", "test_job"])
        self.assertTrue(args.force)

    def test_server_flag_single(self):
        """Test -server flag with single hostname."""
        args = self.parse_args(["-server", "cuebot1.example.com", "-info", "test_job"])
        self.assertEqual(args.server, ["cuebot1.example.com"])

    def test_server_flag_multiple(self):
        """Test -server flag with multiple hostnames."""
        args = self.parse_args(["-server", "cuebot1", "cuebot2", "-info", "test_job"])
        self.assertEqual(args.server, ["cuebot1", "cuebot2"])

    def test_facility_flag(self):
        """Test -facility flag parsing."""
        args = self.parse_args(["-facility", "LAX", "-info", "test_job"])
        self.assertEqual(args.facility, "LAX")

    def test_state_filter_single(self):
        """Test -state flag with single state."""
        args = self.parse_args(["-lf", "test_job", "-state", "RUNNING"])
        self.assertEqual(args.state, ["RUNNING"])

    def test_state_filter_multiple(self):
        """Test -state flag with multiple states."""
        args = self.parse_args(["-lf", "test_job", "-state", "RUNNING", "WAITING"])
        self.assertEqual(args.state, ["RUNNING", "WAITING"])

    def test_range_filter(self):
        """Test -range flag parsing."""
        args = self.parse_args(["-lf", "test_job", "-range", "1-100"])
        self.assertEqual(args.range, "1-100")

    def test_layer_filter_single(self):
        """Test -layer flag with single layer."""
        args = self.parse_args(["-lf", "test_job", "-layer", "render"])
        self.assertEqual(args.layer, ["render"])

    def test_layer_filter_multiple(self):
        """Test -layer flag with multiple layers."""
        args = self.parse_args(["-lf", "test_job", "-layer", "render", "comp"])
        self.assertEqual(args.layer, ["render", "comp"])

    def test_page_filter(self):
        """Test -page flag parsing."""
        args = self.parse_args(["-lf", "test_job", "-page", "2"])
        self.assertEqual(args.page, 2)
        self.assertIsInstance(args.page, int)

    def test_page_filter_invalid_type(self):
        """Test -page flag with non-integer value."""
        with self.assertRaises(SystemExit):
            self.parse_args(["-lf", "test_job", "-page", "not_a_number"])

    def test_limit_filter(self):
        """Test -limit flag parsing."""
        args = self.parse_args(["-lf", "test_job", "-limit", "500"])
        self.assertEqual(args.limit, 500)
        self.assertIsInstance(args.limit, int)

    def test_limit_default_value(self):
        """Test -limit flag default value."""
        args = self.parse_args(["-lf", "test_job"])
        self.assertEqual(args.limit, 1000)

    def test_duration_filter(self):
        """Test -duration flag parsing."""
        args = self.parse_args(["-lf", "test_job", "-duration", "1.5"])
        self.assertEqual(args.duration, "1.5")

    def test_duration_default_value(self):
        """Test -duration flag default value."""
        args = self.parse_args(["-lf", "test_job"])
        self.assertEqual(args.duration, 0.01)

    def test_memory_filter(self):
        """Test -memory flag parsing."""
        args = self.parse_args(["-lf", "test_job", "-memory", "2.0"])
        self.assertEqual(args.memory, "2.0")

    def test_memory_filter_range(self):
        """Test -memory flag with range."""
        args = self.parse_args(["-lf", "test_job", "-memory", "2-4"])
        self.assertEqual(args.memory, "2-4")

    def test_memory_filter_greater_than(self):
        """Test -memory flag with greater than."""
        args = self.parse_args(["-lf", "test_job", "-memory", "gt4"])
        self.assertEqual(args.memory, "gt4")

    def test_memory_filter_less_than(self):
        """Test -memory flag with less than."""
        args = self.parse_args(["-lf", "test_job", "-memory", "lt8"])
        self.assertEqual(args.memory, "lt8")

    def test_memory_default_value(self):
        """Test -memory flag default value."""
        args = self.parse_args(["-lf", "test_job"])
        self.assertEqual(args.memory, 0.01)

    def test_combined_query_options(self):
        """Test combining multiple query options."""
        args = self.parse_args([
            "-lf", "test_job",
            "-layer", "render",
            "-range", "1-100",
            "-state", "RUNNING",
            "-page", "1",
            "-limit", "500"
        ])
        self.assertEqual(args.lf, "test_job")
        self.assertEqual(args.layer, ["render"])
        self.assertEqual(args.range, "1-100")
        self.assertEqual(args.state, ["RUNNING"])
        self.assertEqual(args.page, 1)
        self.assertEqual(args.limit, 500)

    def test_combined_general_and_query_options(self):
        """Test combining general and query options."""
        args = self.parse_args([
            "-server", "cuebot.example.com",
            "-facility", "LAX",
            "-verbose",
            "-lf", "test_job",
            "-range", "1-100"
        ])
        self.assertEqual(args.server, ["cuebot.example.com"])
        self.assertEqual(args.facility, "LAX")
        self.assertTrue(args.verbose)
        self.assertEqual(args.lf, "test_job")
        self.assertEqual(args.range, "1-100")

    def test_eat_with_frame_options(self):
        """Test -eat flag with frame query options."""
        args = self.parse_args([
            "-eat", "test_job",
            "-layer", "render",
            "-range", "1-50"
        ])
        self.assertEqual(args.eat, "test_job")
        self.assertEqual(args.layer, ["render"])
        self.assertEqual(args.range, "1-50")

    def test_kill_with_frame_options(self):
        """Test -kill flag with frame query options."""
        args = self.parse_args([
            "-kill", "test_job",
            "-layer", "comp",
            "-state", "RUNNING"
        ])
        self.assertEqual(args.kill, "test_job")
        self.assertEqual(args.layer, ["comp"])
        self.assertEqual(args.state, ["RUNNING"])

    def test_retry_with_frame_options(self):
        """Test -retry flag with frame query options."""
        args = self.parse_args([
            "-retry", "test_job",
            "-range", "10-20",
            "-layer", "render"
        ])
        self.assertEqual(args.retry, "test_job")
        self.assertEqual(args.range, "10-20")
        self.assertEqual(args.layer, ["render"])

    def test_stagger_with_layer_option(self):
        """Test -stagger flag with layer option."""
        args = self.parse_args([
            "-stagger", "test_job", "1-100", "5",
            "-layer", "render"
        ])
        self.assertEqual(args.stagger, ["test_job", "1-100", "5"])
        self.assertEqual(args.layer, ["render"])

    def test_reorder_with_layer_option(self):
        """Test -reorder flag with layer option."""
        args = self.parse_args([
            "-reorder", "test_job", "1-100", "FIRST",
            "-layer", "comp"
        ])
        self.assertEqual(args.reorder, ["test_job", "1-100", "FIRST"])
        self.assertEqual(args.layer, ["comp"])


class TestMainFunction(unittest.TestCase):
    """Test cases for main function argument parsing integration."""

    def test_main_no_args_displays_help(self):
        """Test that main with no args displays help and exits."""
        with mock.patch('sys.stdout', new=io.StringIO()):
            with mock.patch('argparse.ArgumentParser.print_help') as mock_help:
                with self.assertRaises(SystemExit) as cm:
                    main.main(["cueman"])
                self.assertEqual(cm.exception.code, 0)
                mock_help.assert_called_once()

    def test_main_version_flag(self):
        """Test --version flag handling."""
        with self.assertRaises(SystemExit) as cm:
            with mock.patch('sys.stdout', new=io.StringIO()):
                main.main(["cueman", "--version"])
        self.assertEqual(cm.exception.code, 0)

    @mock.patch('opencue.api.findJob')
    @mock.patch('cueadmin.output.displayFrames')
    def test_main_with_verbose_logging(self, mock_display, mock_findJob):
        """Test that -verbose flag enables debug logging."""
        mock_job = mock.Mock()
        mock_job.getFrames.return_value = []
        mock_findJob.return_value = mock_job

        with mock.patch('logging.basicConfig') as mock_logging:
            main.main(["cueman", "-verbose", "-lf", "test_job"])
            mock_logging.assert_called()
            # Check that debug level was set in at least one call
            calls = mock_logging.call_args_list
            self.assertTrue(any('level' in str(call) for call in calls))

    @mock.patch('opencue.api.findJob')
    @mock.patch('cueadmin.output.displayFrames')
    def test_main_server_argument(self, mock_display, mock_findJob):
        """Test -server argument is parsed correctly."""
        mock_job = mock.Mock()
        mock_job.getFrames.return_value = []
        mock_findJob.return_value = mock_job

        # This should not raise an exception
        main.main(["cueman", "-server", "cuebot.example.com", "-lf", "test_job"])
        mock_findJob.assert_called_once_with("test_job")

    @mock.patch('opencue.api.findJob')
    @mock.patch('cueadmin.output.displayFrames')
    def test_main_facility_argument(self, mock_display, mock_findJob):
        """Test -facility argument is parsed correctly."""
        mock_job = mock.Mock()
        mock_job.getFrames.return_value = []
        mock_findJob.return_value = mock_job

        # This should not raise an exception
        main.main(["cueman", "-facility", "LAX", "-lf", "test_job"])
        mock_findJob.assert_called_once_with("test_job")


class TestInvalidArguments(unittest.TestCase):
    """Test cases for invalid argument handling."""

    def test_invalid_flag(self):
        """Test handling of invalid/unknown flag."""
        with self.assertRaises(SystemExit):
            with mock.patch('sys.stderr', new=io.StringIO()):
                main.main(["cueman", "-invalid_flag"])

    def test_stagger_invalid_increment_non_digit(self):
        """Test -stagger with non-digit increment."""
        args = mock.Mock()
        args.stagger = ["test_job", "1-100", "not_a_number"]
        args.force = False
        args.layer = None
        # Set all other command flags to None
        for cmd in ["lf", "lp", "ll", "info", "pause", "resume", "term",
                    "eat", "kill", "retry", "done", "reorder", "retries",
                    "autoeaton", "autoeatoff"]:
            setattr(args, cmd, None)

        with self.assertRaises(SystemExit):
            main.handleArgs(args)

    def test_stagger_invalid_increment_zero(self):
        """Test -stagger with zero increment."""
        args = mock.Mock()
        args.stagger = ["test_job", "1-100", "0"]
        args.force = False
        args.layer = None
        # Set all other command flags to None
        for cmd in ["lf", "lp", "ll", "info", "pause", "resume", "term",
                    "eat", "kill", "retry", "done", "reorder", "retries",
                    "autoeaton", "autoeatoff"]:
            setattr(args, cmd, None)

        with self.assertRaises(SystemExit):
            main.handleArgs(args)

    def test_stagger_invalid_increment_negative(self):
        """Test -stagger with negative increment."""
        args = mock.Mock()
        args.stagger = ["test_job", "1-100", "-5"]
        args.force = False
        args.layer = None
        # Set all other command flags to None
        for cmd in ["lf", "lp", "ll", "info", "pause", "resume", "term",
                    "eat", "kill", "retry", "done", "reorder", "retries",
                    "autoeaton", "autoeatoff"]:
            setattr(args, cmd, None)

        with self.assertRaises(SystemExit):
            main.handleArgs(args)

    def test_reorder_invalid_position(self):
        """Test -reorder with invalid position."""
        args = mock.Mock()
        args.reorder = ["test_job", "1-100", "INVALID"]
        args.force = False
        args.layer = None
        # Set all other command flags to None
        for cmd in ["lf", "lp", "ll", "info", "pause", "resume", "term",
                    "eat", "kill", "retry", "done", "stagger", "retries",
                    "autoeaton", "autoeatoff"]:
            setattr(args, cmd, None)

        with self.assertRaises(SystemExit):
            main.handleArgs(args)

    def test_invalid_range_format_letters(self):
        """Test buildFrameSearch with invalid range format (letters)."""
        args = mock.Mock()
        args.range = "abc"
        args.layer = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        with self.assertRaises(SystemExit):
            main.buildFrameSearch(args)

    def test_invalid_range_format_reversed(self):
        """Test buildFrameSearch with invalid range format (reversed)."""
        args = mock.Mock()
        args.range = "100-1"
        args.layer = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        with self.assertRaises(SystemExit):
            main.buildFrameSearch(args)

    def test_invalid_range_format_special_chars(self):
        """Test buildFrameSearch with invalid range format (special chars)."""
        args = mock.Mock()
        args.range = "1-100-200"
        args.layer = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        with self.assertRaises(SystemExit):
            main.buildFrameSearch(args)

    @mock.patch('opencue.api.findJob')
    def test_nonexistent_job_error(self, mock_findJob):
        """Test error handling for nonexistent job."""
        mock_findJob.side_effect = Exception("Job does not exist")
        args = mock.Mock()
        args.info = "nonexistent_job"
        args.force = False
        # Set all other command flags to None
        for cmd in ["lf", "lp", "ll", "pause", "resume", "term",
                    "eat", "kill", "retry", "done", "stagger", "reorder",
                    "retries", "autoeaton", "autoeatoff"]:
            setattr(args, cmd, None)

        with self.assertRaises(SystemExit):
            main.handleArgs(args)


class TestEdgeCases(unittest.TestCase):
    """Test cases for edge cases in argument parsing."""

    def test_empty_job_name(self):
        """Test handling of empty job name."""
        args = mock.Mock()
        args.info = ""
        args.force = False
        # Set all other command flags to None
        for cmd in ["lf", "lp", "ll", "pause", "resume", "term",
                    "eat", "kill", "retry", "done", "stagger", "reorder",
                    "retries", "autoeaton", "autoeatoff"]:
            setattr(args, cmd, None)

        with mock.patch('opencue.api.findJob') as mock_findJob:
            mock_findJob.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(args)

    def test_range_single_frame(self):
        """Test buildFrameSearch with single frame number."""
        args = mock.Mock()
        args.range = "42"
        args.layer = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        result = main.buildFrameSearch(args)
        self.assertEqual(result["range"], "42")

    def test_range_valid_format(self):
        """Test buildFrameSearch with valid range."""
        args = mock.Mock()
        args.range = "1-1000"
        args.layer = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        result = main.buildFrameSearch(args)
        self.assertEqual(result["range"], "1-1000")

    def test_multiple_layers(self):
        """Test buildFrameSearch with multiple layers."""
        args = mock.Mock()
        args.layer = ["layer1", "layer2", "layer3"]
        args.range = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        result = main.buildFrameSearch(args)
        self.assertEqual(result["layer"], ["layer1", "layer2", "layer3"])

    def test_page_zero(self):
        """Test buildFrameSearch with page zero (not included in result)."""
        args = mock.Mock()
        args.page = 0
        args.layer = None
        args.range = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.limit = 1000

        result = main.buildFrameSearch(args)
        # Page 0 is falsy and won't be included in the result
        self.assertNotIn("page", result)

    def test_large_limit(self):
        """Test buildFrameSearch with large limit value."""
        args = mock.Mock()
        args.limit = 999999
        args.layer = None
        args.range = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = None

        result = main.buildFrameSearch(args)
        self.assertEqual(result["limit"], 999999)

    def test_format_nargs_input_with_trailing_comma(self):
        """Test format_nargs_input with trailing comma."""
        nargs_input = ["job1,job2,"]
        result = main.format_nargs_input(nargs_input)
        self.assertEqual(result, ["job1", "job2", ""])

    def test_format_nargs_input_with_leading_comma(self):
        """Test format_nargs_input with leading comma."""
        nargs_input = [",job1,job2"]
        result = main.format_nargs_input(nargs_input)
        self.assertEqual(result, ["", "job1", "job2"])

    def test_format_nargs_input_multiple_spaces(self):
        """Test format_nargs_input with multiple spaces."""
        nargs_input = ["job1,  job2,   job3"]
        result = main.format_nargs_input(nargs_input)
        self.assertEqual(result, ["job1", "job2", "job3"])


class TestDefaultValues(unittest.TestCase):
    """Test cases for default value application."""

    def test_default_limit_applied(self):
        """Test that default limit is 1000."""
        args = mock.Mock()
        args.limit = 1000
        args.layer = None
        args.range = None
        args.state = None
        args.memory = 0.01
        args.duration = 0.01
        args.page = None

        result = main.buildFrameSearch(args)
        self.assertEqual(result["limit"], 1000)

    def test_default_duration_applied(self):
        """Test that default duration is 0.01."""
        args = mock.Mock()
        args.duration = 0.01
        args.layer = None
        args.range = None
        args.state = None
        args.memory = 0.01
        args.page = None
        args.limit = 1000

        with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
            mock_handle.side_effect = [
                [mock.Mock(value=10485)],  # memory
                [mock.Mock(value=36)],     # duration
            ]
            result = main.buildFrameSearch(args)

        self.assertIn("duration", result)

    def test_default_memory_applied(self):
        """Test that default memory is 0.01."""
        args = mock.Mock()
        args.memory = 0.01
        args.layer = None
        args.range = None
        args.state = None
        args.duration = 0.01
        args.page = None
        args.limit = 1000

        with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
            mock_handle.return_value = [mock.Mock(value=10485)]
            result = main.buildFrameSearch(args)

        self.assertIn("memory", result)

    def test_default_force_false(self):
        """Test that force flag defaults to False."""
        args = mock.Mock()
        args.force = False
        args.info = "test_job"
        # Set all other command flags to None
        for cmd in ["lf", "lp", "ll", "pause", "resume", "term",
                    "eat", "kill", "retry", "done", "stagger", "reorder",
                    "retries", "autoeaton", "autoeatoff"]:
            setattr(args, cmd, None)

        with mock.patch('opencue.api.findJob') as mock_findJob:
            mock_job = mock.Mock()
            mock_findJob.return_value = mock_job
            with mock.patch('cueadmin.output.displayJobInfo'):
                main.handleArgs(args)

        self.assertFalse(args.force)

    def test_default_verbose_false(self):
        """Test that verbose flag defaults to False."""
        with mock.patch('sys.stdout', new=io.StringIO()):
            with self.assertRaises(SystemExit):
                main.main(["cueman"])


class TestHelpText(unittest.TestCase):
    """Test cases for help text generation."""

    def test_help_flag_short(self):
        """Test -h flag displays help."""
        with self.assertRaises(SystemExit) as cm:
            with mock.patch('sys.stdout', new=io.StringIO()):
                main.main(["cueman", "-h"])
        self.assertEqual(cm.exception.code, 0)

    def test_help_flag_long(self):
        """Test --help flag displays help."""
        with self.assertRaises(SystemExit) as cm:
            with mock.patch('sys.stdout', new=io.StringIO()):
                main.main(["cueman", "--help"])
        self.assertEqual(cm.exception.code, 0)

    def test_help_contains_query_options(self):
        """Test that help text contains query option descriptions."""
        with self.assertRaises(SystemExit):
            with mock.patch('sys.stdout', new=io.StringIO()) as fake_out:
                try:
                    main.main(["cueman", "--help"])
                except SystemExit:
                    output = fake_out.getvalue()
                    # Help text should contain some of the main flags
                    self.assertIn("-lf", output)
                    raise


if __name__ == "__main__":
    unittest.main()
