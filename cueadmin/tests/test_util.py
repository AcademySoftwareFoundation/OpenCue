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


"""Tests for cueadmin.util."""


from __future__ import absolute_import, division, print_function

import logging
import unittest

import mock
import opencue

import cueadmin.util


class EnableDebugLoggingTests(unittest.TestCase):
    """Tests for enableDebugLogging() function."""

    def setUp(self):
        # Get the opencue logger for testing
        self.logger = logging.getLogger("opencue")
        # Store original handlers to restore after test
        self.original_handlers = self.logger.handlers[:]
        self.original_level = self.logger.level
        # Clear handlers before each test
        self.logger.handlers = []

    def tearDown(self):
        # Restore original logger state
        self.logger.handlers = self.original_handlers
        self.logger.level = self.original_level

    def testEnableDebugLoggingAddsHandler(self):
        """Test that enableDebugLogging adds a StreamHandler to the logger."""
        cueadmin.util.enableDebugLogging()

        self.assertEqual(len(self.logger.handlers), 1)
        self.assertIsInstance(self.logger.handlers[0], logging.StreamHandler)

    def testEnableDebugLoggingSetsLogLevel(self):
        """Test that enableDebugLogging sets the logger level to DEBUG."""
        cueadmin.util.enableDebugLogging()

        self.assertEqual(self.logger.level, logging.DEBUG)

    def testEnableDebugLoggingSetsHandlerLevel(self):
        """Test that enableDebugLogging sets the handler level to DEBUG."""
        cueadmin.util.enableDebugLogging()

        handler = self.logger.handlers[0]
        self.assertEqual(handler.level, logging.DEBUG)

    def testEnableDebugLoggingSetsFormatter(self):
        """Test that enableDebugLogging sets the correct formatter."""
        cueadmin.util.enableDebugLogging()

        handler = self.logger.handlers[0]
        formatter = handler.formatter
        self.assertIsNotNone(formatter)
        # Test the formatter by formatting a test record
        test_record = logging.LogRecord(
            name="opencue",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None
        )
        formatted = formatter.format(test_record)
        self.assertEqual(formatted, "DEBUG opencue test message")


class PromptYesNoTests(unittest.TestCase):
    """Tests for promptYesNo() function."""

    @mock.patch("cueadmin.util.input")
    @mock.patch("builtins.print")
    def testPromptYesNoAcceptsLowercaseY(self, printMock, inputMock):
        """Test that promptYesNo returns True for lowercase 'y' input."""
        inputMock.return_value = "y"

        result = cueadmin.util.promptYesNo("Continue?")

        self.assertTrue(result)
        inputMock.assert_called_once_with("Continue? [y/n] ")
        printMock.assert_not_called()

    @mock.patch("cueadmin.util.input")
    @mock.patch("builtins.print")
    def testPromptYesNoAcceptsUppercaseY(self, printMock, inputMock):
        """Test that promptYesNo returns True for uppercase 'Y' input."""
        inputMock.return_value = "Y"

        result = cueadmin.util.promptYesNo("Continue?")

        self.assertTrue(result)
        inputMock.assert_called_once_with("Continue? [y/n] ")
        printMock.assert_not_called()

    @mock.patch("cueadmin.util.input")
    @mock.patch("builtins.print")
    def testPromptYesNoRejectsLowercaseN(self, printMock, inputMock):
        """Test that promptYesNo returns False for lowercase 'n' input."""
        inputMock.return_value = "n"

        result = cueadmin.util.promptYesNo("Continue?")

        self.assertFalse(result)
        inputMock.assert_called_once_with("Continue? [y/n] ")
        printMock.assert_called_once_with("Canceled")

    @mock.patch("cueadmin.util.input")
    @mock.patch("builtins.print")
    def testPromptYesNoRejectsUppercaseN(self, printMock, inputMock):
        """Test that promptYesNo returns False for uppercase 'N' input."""
        inputMock.return_value = "N"

        result = cueadmin.util.promptYesNo("Continue?")

        self.assertFalse(result)
        inputMock.assert_called_once_with("Continue? [y/n] ")
        printMock.assert_called_once_with("Canceled")

    @mock.patch("cueadmin.util.input")
    @mock.patch("builtins.print")
    def testPromptYesNoRejectsInvalidInput(self, printMock, inputMock):
        """Test that promptYesNo returns False for invalid input."""
        inputMock.return_value = "invalid"

        result = cueadmin.util.promptYesNo("Continue?")

        self.assertFalse(result)
        inputMock.assert_called_once_with("Continue? [y/n] ")
        printMock.assert_called_once_with("Canceled")

    @mock.patch("cueadmin.util.input")
    @mock.patch("builtins.print")
    def testPromptYesNoRejectsEmptyInput(self, printMock, inputMock):
        """Test that promptYesNo returns False for empty input."""
        inputMock.return_value = ""

        result = cueadmin.util.promptYesNo("Continue?")

        self.assertFalse(result)
        inputMock.assert_called_once_with("Continue? [y/n] ")
        printMock.assert_called_once_with("Canceled")

    @mock.patch("cueadmin.util.input")
    @mock.patch("builtins.print")
    def testPromptYesNoRejectsYes(self, printMock, inputMock):
        """Test that promptYesNo returns False for 'yes' input."""
        inputMock.return_value = "yes"

        result = cueadmin.util.promptYesNo("Continue?")

        self.assertFalse(result)
        inputMock.assert_called_once_with("Continue? [y/n] ")
        printMock.assert_called_once_with("Canceled")

    @mock.patch("cueadmin.util.input")
    @mock.patch("builtins.print")
    def testPromptYesNoWithForceFlagBypassesPrompt(self, printMock, inputMock):
        """Test that promptYesNo bypasses prompt when force=True."""
        result = cueadmin.util.promptYesNo("Continue?", force=True)

        self.assertTrue(result)
        inputMock.assert_not_called()
        printMock.assert_not_called()

    @mock.patch("cueadmin.util.input")
    @mock.patch("builtins.print")
    def testPromptYesNoWithForceFalseStillPrompts(self, printMock, inputMock):
        """Test that promptYesNo still prompts when force=False."""
        inputMock.return_value = "y"

        result = cueadmin.util.promptYesNo("Continue?", force=False)

        self.assertTrue(result)
        inputMock.assert_called_once_with("Continue? [y/n] ")


@mock.patch("time.sleep")
@mock.patch("opencue.api.isJobPending")
class WaitOnJobNameTests(unittest.TestCase):
    """Tests for waitOnJobName() function."""

    def testWaitOnJobNameFindsAndCompletesJob(self, isJobPendingMock, sleepMock):
        """Test that waitOnJobName returns True when job is found and completes."""
        # Simulate job found (pending) then completed (not pending)
        isJobPendingMock.side_effect = [True, True, False]
        jobName = "test-job-name"

        result = cueadmin.util.waitOnJobName(jobName)

        self.assertTrue(result)
        # Should be called 3 times: once while locating, twice while pending, third shows complete
        self.assertEqual(isJobPendingMock.call_count, 3)
        isJobPendingMock.assert_called_with(jobName.lower())

    def testWaitOnJobNameImmediateCompletion(self, isJobPendingMock, sleepMock):
        """Test that waitOnJobName handles immediate job completion."""
        # Job is already found and immediately completes
        isJobPendingMock.side_effect = [True, False]
        jobName = "quick-job"

        result = cueadmin.util.waitOnJobName(jobName)

        self.assertTrue(result)
        self.assertEqual(isJobPendingMock.call_count, 2)

    def testWaitOnJobNameConvertsToLowercase(self, isJobPendingMock, sleepMock):
        """Test that waitOnJobName converts job name to lowercase."""
        isJobPendingMock.side_effect = [True, False]
        jobName = "TEST-JOB-NAME"

        result = cueadmin.util.waitOnJobName(jobName)

        self.assertTrue(result)
        isJobPendingMock.assert_called_with(jobName.lower())

    def testWaitOnJobNameTimeoutNotFound(self, isJobPendingMock, sleepMock):
        """Test that waitOnJobName returns False when job not found before timeout."""
        # Job never found (isJobPending returns False)
        isJobPendingMock.return_value = False
        jobName = "nonexistent-job"
        maxWait = 30

        result = cueadmin.util.waitOnJobName(jobName, maxWaitForLaunch=maxWait)

        self.assertFalse(result)
        # Should eventually timeout
        self.assertGreater(isJobPendingMock.call_count, 1)

    def testWaitOnJobNameNoTimeoutWaitsIndefinitely(self, isJobPendingMock, sleepMock):
        """Test that waitOnJobName continues indefinitely without maxWaitForLaunch."""
        # Job found after several attempts
        isJobPendingMock.side_effect = [False, False, False, True, True, False]
        jobName = "late-job"

        result = cueadmin.util.waitOnJobName(jobName)

        self.assertTrue(result)
        self.assertEqual(isJobPendingMock.call_count, 6)

    def testWaitOnJobNameDelayChangesAfterJobFound(self, isJobPendingMock, sleepMock):
        """Test that waitOnJobName increases delay after job is found."""
        isJobPendingMock.side_effect = [False, True, True, False]
        jobName = "test-job"

        result = cueadmin.util.waitOnJobName(jobName)

        self.assertTrue(result)
        # First sleep is 4 seconds (initial delay)
        # Then 10 seconds while searching (first False)
        # Then 15 seconds after found (True, True)
        sleep_calls = [call[0][0] for call in sleepMock.call_args_list]
        self.assertEqual(sleep_calls[0], 4)  # Initial sleep
        self.assertEqual(sleep_calls[1], 10)  # Search delay
        self.assertEqual(sleep_calls[2], 15)  # After job found
        self.assertEqual(sleep_calls[3], 15)  # Still pending

    @mock.patch("sys.stderr")
    @mock.patch("builtins.print")
    def testWaitOnJobNameHandlesCueException(
        self, printMock, stderrMock, isJobPendingMock, sleepMock
    ):
        """Test that waitOnJobName handles CueException and continues."""
        error_msg = "Connection error"
        isJobPendingMock.side_effect = [
            opencue.CueException(error_msg),
            True,
            False
        ]
        jobName = "test-job"

        result = cueadmin.util.waitOnJobName(jobName)

        self.assertTrue(result)
        printMock.assert_called_once()
        call_args = printMock.call_args
        self.assertIn("Error:", call_args[0][0])
        self.assertEqual(call_args[1]["file"], stderrMock)

    @mock.patch("sys.stderr")
    @mock.patch("builtins.print")
    def testWaitOnJobNameHandlesMultipleExceptions(
        self, printMock, stderrMock, isJobPendingMock, sleepMock
    ):
        """Test that waitOnJobName handles multiple exceptions."""
        isJobPendingMock.side_effect = [
            opencue.CueException("Error 1"),
            opencue.CueException("Error 2"),
            True,
            False
        ]
        jobName = "test-job"

        result = cueadmin.util.waitOnJobName(jobName)

        self.assertTrue(result)
        self.assertEqual(printMock.call_count, 2)

    def testWaitOnJobNameTimeoutAfterExceptions(self, isJobPendingMock, sleepMock):
        """Test that waitOnJobName times out correctly even with exceptions."""
        # Multiple exceptions, job never found, should timeout
        # Need enough False values to exceed maxWait (25 seconds)
        # Initial sleep is 4s, then 10s per iteration
        # 4 + 10 + 10 + 10 = 34s (will timeout after 3rd iteration)
        isJobPendingMock.side_effect = [
            opencue.CueException("Error"),
            False,
            opencue.CueException("Error"),
            False,
            False,
            False
        ]
        jobName = "problem-job"
        maxWait = 25

        result = cueadmin.util.waitOnJobName(jobName, maxWaitForLaunch=maxWait)

        self.assertFalse(result)

    def testWaitOnJobNameJobStateTransition(self, isJobPendingMock, sleepMock):
        """Test waitOnJobName through complete job lifecycle."""
        # Job not found -> found and pending -> still pending -> completed
        isJobPendingMock.side_effect = [
            False,  # Not found yet
            False,  # Still not found
            True,   # Found! Now pending
            True,   # Still pending
            True,   # Still pending
            False   # Completed
        ]
        jobName = "lifecycle-job"

        result = cueadmin.util.waitOnJobName(jobName)

        self.assertTrue(result)
        self.assertEqual(isJobPendingMock.call_count, 6)

    def testWaitOnJobNameTimeoutCalculation(self, isJobPendingMock, sleepMock):
        """Test that waitOnJobName calculates timeout correctly."""
        # Job never found, should respect timeout
        isJobPendingMock.return_value = False
        jobName = "timeout-job"
        maxWait = 35  # Should allow 3-4 iterations at 10 second delay

        result = cueadmin.util.waitOnJobName(jobName, maxWaitForLaunch=maxWait)

        self.assertFalse(result)
        # Initial 4 second sleep, then delays of 10 seconds
        # Should timeout after around 40 seconds (4 + 10 + 10 + 10...)
        call_count = isJobPendingMock.call_count
        self.assertGreaterEqual(call_count, 3)
        self.assertLessEqual(call_count, 5)


if __name__ == "__main__":
    unittest.main()
