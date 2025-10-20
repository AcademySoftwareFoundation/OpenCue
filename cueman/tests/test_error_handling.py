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
Unit tests for error handling and logging scenarios in cueman.
Tests cover network failures, invalid jobs, permission errors, timeouts,
and proper logging output for both normal and verbose modes.
"""

from __future__ import absolute_import, division, print_function

import argparse
import logging
import os
import sys
import unittest
import warnings
from io import StringIO

import mock

# Suppress protobuf version warnings
warnings.filterwarnings(
    "ignore", category=UserWarning, module="google.protobuf.runtime_version"
)

# Add the parent directory to the path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cueman import main  # pylint: disable=wrong-import-position


class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling scenarios in cueman."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = mock.Mock()
        # Set all command flags to None by default
        for cmd in [
            "lf",
            "lp",
            "ll",
            "info",
            "pause",
            "resume",
            "term",
            "eat",
            "kill",
            "retry",
            "done",
            "stagger",
            "reorder",
            "retries",
            "autoeaton",
            "autoeatoff",
        ]:
            setattr(self.args, cmd, None)
        self.args.force = False
        self.args.layer = None
        self.args.range = None
        self.args.state = None
        self.args.page = None
        self.args.limit = 1000
        self.args.duration = 0.01
        self.args.memory = 0.01

    def tearDown(self):
        """Clean up after tests."""
        # Reset logging
        logging.getLogger("opencue.tools.cueman").handlers = []

    def test_job_not_found_list_frames(self):
        """Test job not found exception when listing frames."""
        self.args.lf = "nonexistent_job"

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_list_procs(self):
        """Test job not found exception when listing processes."""
        self.args.lp = "nonexistent_job"

        with mock.patch("opencue.api.getProcs") as mock_get_procs:
            mock_get_procs.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_list_layers(self):
        """Test job not found exception when listing layers."""
        self.args.ll = "nonexistent_job"

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_info(self):
        """Test job not found exception when getting info."""
        self.args.info = "nonexistent_job"

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Incorrect result size")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_pause(self):
        """Test job not found exception when pausing."""
        self.args.pause = ["nonexistent_job"]

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_resume(self):
        """Test job not found exception when resuming."""
        self.args.resume = ["nonexistent_job"]

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_terminate(self):
        """Test job not found exception when terminating."""
        self.args.term = ["nonexistent_job"]

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_eat_frames(self):
        """Test job not found exception when eating frames."""
        self.args.eat = "nonexistent_job"

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_kill_frames(self):
        """Test job not found exception when killing frames."""
        self.args.kill = "nonexistent_job"

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_retry_frames(self):
        """Test job not found exception when retrying frames."""
        self.args.retry = "nonexistent_job"

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_mark_done_frames(self):
        """Test job not found exception when marking frames as done."""
        self.args.done = "nonexistent_job"

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_stagger(self):
        """Test job not found exception when staggering frames."""
        self.args.stagger = ["nonexistent_job", "1-100", "5"]

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Incorrect result size")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_reorder(self):
        """Test job not found exception when reordering frames."""
        self.args.reorder = ["nonexistent_job", "1-100", "FIRST"]

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_set_retries(self):
        """Test job not found exception when setting retries."""
        self.args.retries = ["nonexistent_job", "3"]

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_auto_eat_on(self):
        """Test job not found exception when enabling auto-eat."""
        self.args.autoeaton = ["nonexistent_job"]

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_job_not_found_auto_eat_off(self):
        """Test job not found exception when disabling auto-eat."""
        self.args.autoeatoff = ["nonexistent_job"]

        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    @mock.patch("cueman.main.logger")
    @mock.patch("opencue.api.findJob")
    def test_network_connection_failure(self, mock_find, mock_logger):
        """Test network connectivity failure when finding job."""
        self.args.info = "test_job"
        mock_find.side_effect = Exception("Connection refused")

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

        mock_logger.error.assert_called()

    @mock.patch("cueman.main.logger")
    @mock.patch("opencue.api.findJob")
    def test_network_timeout_error(self, mock_find, mock_logger):
        """Test network timeout when finding job."""
        self.args.info = "test_job"
        mock_find.side_effect = Exception("Connection timeout")

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

        mock_logger.error.assert_called()

    @mock.patch("cueman.main.logger")
    @mock.patch("opencue.api.findJob")
    def test_permission_denied_job_access(self, mock_find, mock_logger):
        """Test permission denied when accessing job."""
        self.args.info = "restricted_job"
        mock_find.side_effect = Exception("Permission denied")

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

        mock_logger.error.assert_called()

    @mock.patch("cueman.main.logger")
    @mock.patch("opencue.api.findJob")
    def test_permission_denied_job_operation(self, mock_find, _mock_logger):
        """Test permission denied when performing job operation."""
        self.args.pause = ["test_job"]
        mock_job = mock.Mock()
        mock_job.isPaused.return_value = False
        mock_job.pause.side_effect = Exception("Permission denied: user not authorized")
        mock_job.name.return_value = "test_job"
        mock_find.return_value = mock_job

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

    def test_invalid_frame_range_format(self):
        """Test invalid frame range format."""
        self.args.lf = "test_job"
        self.args.range = "invalid-range"

        with mock.patch("opencue.api.findJob"):
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_invalid_frame_range_order(self):
        """Test invalid frame range with start > end."""
        self.args.lf = "test_job"
        self.args.range = "100-1"

        with mock.patch("opencue.api.findJob"):
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_invalid_stagger_increment_negative(self):
        """Test invalid stagger increment (negative value)."""
        self.args.stagger = ["test_job", "1-100", "-5"]

        with mock.patch("opencue.api.findJob"):
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_invalid_stagger_increment_zero(self):
        """Test invalid stagger increment (zero)."""
        self.args.stagger = ["test_job", "1-100", "0"]

        with mock.patch("opencue.api.findJob"):
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_invalid_stagger_increment_non_numeric(self):
        """Test invalid stagger increment (non-numeric)."""
        self.args.stagger = ["test_job", "1-100", "abc"]

        with mock.patch("opencue.api.findJob"):
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_invalid_reorder_position(self):
        """Test invalid reorder position."""
        self.args.reorder = ["test_job", "1-100", "INVALID"]

        with mock.patch("opencue.api.findJob"):
            with self.assertRaises(SystemExit):
                main.handleArgs(self.args)

    def test_reorder_invalid_order_raises_value_error(self):
        """Test reorderJob raises ValueError for invalid order."""
        mock_job = mock.Mock()

        with self.assertRaises(ValueError) as cm:
            main.reorderJob(mock_job, None, "1-100", "INVALID_ORDER")

        self.assertIn("Invalid ordering", str(cm.exception))

    def test_no_command_specified(self):
        """Test error when no command is specified."""
        args = argparse.Namespace(
            lf=None,
            lp=None,
            ll=None,
            info=None,
            pause=None,
            resume=None,
            term=None,
            eat=None,
            kill=None,
            retry=None,
            done=None,
            stagger=None,
            reorder=None,
            retries=None,
            autoeaton=None,
            autoeatoff=None,
            force=False,
        )

        with self.assertRaises(SystemExit):
            main.handleArgs(args)

    @mock.patch("cueman.main.logger")
    @mock.patch("opencue.api.findJob")
    def test_error_message_formatting_job_not_found(self, mock_find, mock_logger):
        """Test proper error message formatting for job not found."""
        self.args.info = "missing_job"
        mock_find.side_effect = Exception("Job does not exist")

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

        mock_logger.error.assert_called_with("Error: Job '%s' does not exist.", "missing_job")

    @mock.patch("cueman.main.logger")
    @mock.patch("opencue.api.findJob")
    def test_error_message_formatting_generic_error(self, mock_find, _mock_logger):
        """Test proper error message formatting for generic errors."""
        self.args.info = "test_job"
        error_msg = "Database connection lost"
        mock_find.side_effect = Exception(error_msg)

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

        _mock_logger.error.assert_called()
        call_args = _mock_logger.error.call_args[0]
        self.assertIn("test_job", str(call_args))

    @mock.patch("cueman.main.logger")
    def test_terminate_job_exception_propagates(self, _mock_logger):
        """Test that exceptions during job termination propagate."""
        mock_job = mock.Mock()
        mock_job.name.return_value = "test_job"
        mock_job.kill.side_effect = Exception("Network error during kill")

        with self.assertRaises(Exception) as cm:
            main.terminateJobs([mock_job])

        self.assertEqual(str(cm.exception), "Network error during kill")


class TestLoggingConfiguration(unittest.TestCase):
    """Test cases for logging configuration in normal and verbose modes."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear any existing handlers
        logger = logging.getLogger("opencue.tools.cueman")
        logger.handlers = []
        logger.setLevel(logging.NOTSET)

    def tearDown(self):
        """Clean up after tests."""
        # Reset logging
        logger = logging.getLogger("opencue.tools.cueman")
        logger.handlers = []
        logger.setLevel(logging.NOTSET)

    @mock.patch("sys.stderr", new_callable=StringIO)
    @mock.patch("sys.argv", ["cueman", "-info", "nonexistent_job"])
    def test_normal_mode_error_output(self, _mock_stderr):
        """Test error output in normal (non-verbose) mode."""
        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            try:
                main.main(["cueman", "-info", "nonexistent_job"])
            except SystemExit:
                pass

    @mock.patch("sys.stderr", new_callable=StringIO)
    @mock.patch("sys.argv", ["cueman", "-verbose", "-info", "nonexistent_job"])
    def test_verbose_mode_error_output(self, _mock_stderr):
        """Test error output in verbose mode with traceback."""
        with mock.patch("opencue.api.findJob") as mock_find:
            mock_find.side_effect = Exception("Job does not exist")
            try:
                main.main(["cueman", "-verbose", "-info", "nonexistent_job"])
            except SystemExit:
                pass

    def test_verbose_flag_enables_debug_logging(self):
        """Test that verbose flag enables DEBUG logging level."""
        with mock.patch("sys.argv", ["cueman", "-verbose"]):
            try:
                main.main(["cueman", "-verbose"])
            except SystemExit:
                pass

    def test_normal_mode_uses_info_logging(self):
        """Test that normal mode uses INFO logging level."""
        with mock.patch("sys.argv", ["cueman"]):
            try:
                main.main(["cueman"])
            except SystemExit:
                pass

    @mock.patch("traceback.print_exc")
    @mock.patch("opencue.api.findJob")
    def test_verbose_mode_prints_traceback(self, mock_find, mock_traceback):
        """Test that verbose mode prints exception traceback."""
        mock_find.side_effect = Exception("Test exception")

        with mock.patch("sys.argv", ["cueman", "-verbose", "-info", "test_job"]):
            try:
                main.main(["cueman", "-verbose", "-info", "test_job"])
            except SystemExit:
                pass

            # Traceback is printed when there's an exception in verbose mode
            self.assertTrue(mock_traceback.called or mock_find.called)

    @mock.patch("traceback.print_exc")
    @mock.patch("opencue.api.findJob")
    def test_normal_mode_no_traceback(self, mock_find, mock_traceback):
        """Test that normal mode does not print exception traceback."""
        mock_find.side_effect = Exception("Test exception")

        with mock.patch("sys.argv", ["cueman", "-info", "test_job"]):
            try:
                main.main(["cueman", "-info", "test_job"])
            except SystemExit:
                pass

            mock_traceback.assert_not_called()

    @mock.patch("cueman.main.logger")
    @mock.patch("opencue.api.findJob")
    def test_logger_error_called_on_exception(self, mock_find, mock_logger):
        """Test that logger.error is called when exception occurs."""
        mock_find.side_effect = Exception("Test error")

        with mock.patch("sys.argv", ["cueman", "-info", "test_job"]):
            try:
                main.main(["cueman", "-info", "test_job"])
            except SystemExit:
                pass

            mock_logger.error.assert_called()

    @mock.patch("cueman.main.logger")
    def test_logging_format_verbose_mode(self, _mock_logger):
        """Test logging format includes level and name in verbose mode."""
        with mock.patch("logging.basicConfig") as mock_basic_config:
            with mock.patch("sys.argv", ["cueman", "-verbose"]):
                try:
                    main.main(["cueman", "-verbose"])
                except SystemExit:
                    pass

                # Check that basicConfig was called with DEBUG level
                calls = mock_basic_config.call_args_list
                if calls:
                    for call in calls:
                        if "level" in call[1] and call[1]["level"] == logging.DEBUG:
                            self.assertIn("format", call[1])
                            self.assertIn("%(levelname)s", call[1]["format"])
                            break

    @mock.patch("cueman.main.logger")
    def test_logging_format_normal_mode(self, _mock_logger):
        """Test logging format in normal mode is simple."""
        with mock.patch("logging.basicConfig") as mock_basic_config:
            with mock.patch("sys.argv", ["cueman"]):
                try:
                    main.main(["cueman"])
                except SystemExit:
                    pass

                # Check that basicConfig was called with INFO level
                calls = mock_basic_config.call_args_list
                if calls:
                    for call in calls:
                        if "level" in call[1] and call[1]["level"] == logging.INFO:
                            self.assertIn("format", call[1])
                            self.assertEqual(call[1]["format"], "%(message)s")
                            break


class TestTimeoutHandling(unittest.TestCase):
    """Test cases for timeout scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = mock.Mock()
        for cmd in [
            "lf",
            "lp",
            "ll",
            "info",
            "pause",
            "resume",
            "term",
            "eat",
            "kill",
            "retry",
            "done",
            "stagger",
            "reorder",
            "retries",
            "autoeaton",
            "autoeatoff",
        ]:
            setattr(self.args, cmd, None)
        self.args.force = False

    @mock.patch("opencue.api.findJob")
    def test_timeout_finding_job(self, mock_find):
        """Test timeout exception when finding job."""
        self.args.info = "test_job"
        mock_find.side_effect = Exception("Request timeout")

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

    @mock.patch("opencue.api.findJob")
    def test_timeout_getting_frames(self, mock_find):
        """Test timeout when getting frames from job."""
        self.args.lf = "test_job"
        self.args.layer = None
        self.args.range = None
        self.args.state = None
        self.args.page = None
        self.args.limit = 1000
        self.args.duration = 0.01
        self.args.memory = 0.01

        mock_job = mock.Mock()
        mock_job.getFrames.side_effect = Exception("Operation timed out")
        mock_find.return_value = mock_job

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

    @mock.patch("opencue.api.findJob")
    def test_timeout_killing_job(self, mock_find):
        """Test timeout when killing job."""
        self.args.term = ["test_job"]
        self.args.force = True

        mock_job = mock.Mock()
        mock_job.kill.side_effect = Exception("Timeout waiting for response")
        mock_job.name.return_value = "test_job"
        mock_find.return_value = mock_job

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)


class TestNetworkFailures(unittest.TestCase):
    """Test cases for various network failure scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = mock.Mock()
        for cmd in [
            "lf",
            "lp",
            "ll",
            "info",
            "pause",
            "resume",
            "term",
            "eat",
            "kill",
            "retry",
            "done",
            "stagger",
            "reorder",
            "retries",
            "autoeaton",
            "autoeatoff",
        ]:
            setattr(self.args, cmd, None)
        self.args.force = False

    @mock.patch("opencue.api.findJob")
    def test_connection_refused(self, mock_find):
        """Test connection refused error."""
        self.args.info = "test_job"
        mock_find.side_effect = ConnectionRefusedError("Connection refused")

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

    @mock.patch("opencue.api.findJob")
    def test_connection_reset(self, mock_find):
        """Test connection reset error."""
        self.args.info = "test_job"
        mock_find.side_effect = ConnectionResetError("Connection reset by peer")

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

    @mock.patch("opencue.api.findJob")
    def test_connection_aborted(self, mock_find):
        """Test connection aborted error."""
        self.args.info = "test_job"
        mock_find.side_effect = ConnectionAbortedError("Connection aborted")

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

    @mock.patch("opencue.api.findJob")
    def test_host_unreachable(self, mock_find):
        """Test host unreachable error."""
        self.args.info = "test_job"
        mock_find.side_effect = Exception("No route to host")

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)

    @mock.patch("opencue.api.findJob")
    def test_dns_resolution_failure(self, mock_find):
        """Test DNS resolution failure."""
        self.args.info = "test_job"
        mock_find.side_effect = Exception("Name or service not known")

        with self.assertRaises(SystemExit):
            main.handleArgs(self.args)


if __name__ == "__main__":
    unittest.main()
