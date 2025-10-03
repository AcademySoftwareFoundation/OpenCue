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


"""Unit tests for frame operations cueman"""

#pylint: disable=invalid-name
#pylint: disable=too-many-public-methods
import unittest
from unittest.mock import MagicMock, patch
import argparse
from cueman import main as cuemain

class TestFrameOperations (unittest.TestCase):
    """Test cases for cueman frame operations"""

    def _ns(self, **overrides):
        """Build a minimal argparse.Namespace matching cueman.main expectations."""
        base = {
            "lf": None,
            "lp": None,
            "ll": None,
            "info": None,
            "pause": None,
            "resume": None,
            "term": None,
            "eat": None,
            "kill": None,
            "retry": None,
            "done": None,
            "stagger": None,
            "reorder": None,
            "retries": None,
            "autoeaton": None,
            "autoeatoff": None,
            "layer": None,
            "range": None,
            "state": None,
            "page": None,
            "limit": None,
            "duration": None,
            "memory": None,
            "force": False,
        }
        base.update(overrides)
        return argparse.Namespace(**base)

    # ------------- Frame eat/kill/retry operations with layer and range filters tests -------------

    @patch("opencue.api.findJob")
    def test_eatFrames_with_valid_layer(self, mock_findJob):
        """Test eatFrames with valid layer and range filters."""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(eat="test_job", layer=["render_layer"], range="1-10", force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.eatFrames.assert_called_once_with(layer=["render_layer"], range="1-10")


    @patch("opencue.api.findJob")
    def test_killFrames_with_valid_layer(self, mock_findJob):
        """Test killFrames with valid layer and range filters."""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(kill="test_job", layer=["render_layer"], range="1-10", force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.killFrames.assert_called_once_with(layer=["render_layer"], range="1-10")


    @patch("opencue.api.findJob")
    def test_retryFrames_with_valid_layer(self, mock_findJob):
        """Test retryFrames with valid layer and range filters."""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(retry="test_job", layer=["render_layer"], range="1-10", force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.retryFrames.assert_called_once_with(layer=["render_layer"], range="1-10")


    # -------------- eatFrame state filtering tests --------------

    @patch("opencue.api.findJob")
    def test_eatFrames_with_waiting_state_filter(self, mock_findJob):
        """Test eatFrames with waiting state filter"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(eat="test_job", state=["waiting"], force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.eatFrames.assert_called_once_with(state=[0])


    @patch("opencue.api.findJob")
    def test_eatFrames_with_running_state_filter(self, mock_findJob):
        """Test eatFrames with running state filter"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(eat="test_job", state=["running"], force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.eatFrames.assert_called_once_with(state=[2])


    @patch("opencue.api.findJob")
    def test_eatFrames_with_succeeded_state_filter(self, mock_findJob):
        """Test eatFrames with succeeded state filter"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(eat="test_job", state=["succeeded"], force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.eatFrames.assert_called_once_with(state=[3])


    @patch("opencue.api.findJob")
    def test_eatFrames_with_dead_state_filter(self, mock_findJob):
        """Test eatFrames with dead state filter"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(eat="test_job", state=["dead"], force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.eatFrames.assert_called_once_with(state=[5])


    # -------------- eatFrame range parsing and validation tests --------------

    @patch("opencue.api.findJob")
    def test_valid_range_inputs(self, mock_findJob):
        """Test eatFrame with valid range input"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(eat="test_job", range="1-10", force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.eatFrames.assert_called_once_with(range="1-10")


    @patch("opencue.api.findJob")
    def test_valid_single_range_inputs(self, mock_findJob):
        """Test eatFrame with single frame input"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(eat="test_job", range="1", force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.eatFrames.assert_called_once_with(range="1")


    @patch("opencue.api.findJob")
    def test_invalid_nonnumeric_range_inputs(self, mock_findJob):
        """Test eatFrame with invalid range input (non numeric)"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(eat="test_job", range="1-a", force=True)
        with self.assertRaises(SystemExit) as e:
            cuemain.handleArgs(args)

        self.assertEqual(e.exception.code, 1)


    @patch("opencue.api.findJob")
    def test_invalid_reverse_range_inputs(self, mock_findJob):
        """Test eatFrame with invalid range inputs (reverse)"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(eat="test_job", range="10-1", force=True)
        with self.assertRaises(SystemExit) as e:
            cuemain.handleArgs(args)

        self.assertEqual(e.exception.code, 1)


    # -------------- Mark done functionality test --------------

    @patch("opencue.api.findJob")
    def test_done_functionality(self, mock_findJob):
        """Test mark done functionality"""
        mock_job = MagicMock()
        mock_job.markdoneFrames = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(done="test_job", force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.markdoneFrames.assert_called_once()


    # -------------- Stagger Operation test --------------

    @patch("opencue.api.findJob")
    def test_stagger_increments(self, mock_findJob):
        """Test stagger operations with increment validation"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(stagger=["test_job", "1-10", "2"], force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.staggerFrames.assert_called_once_with("1-10", 2)


    @patch("opencue.api.findJob")
    def test_stagger_zero_increments(self, mock_findJob):
        """Test stagger operations with zero increment validation"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(stagger=["test_job", "1-10", "0"], force=True)
        with self.assertRaises(SystemExit) as e:
            cuemain.handleArgs(args)

        self.assertEqual(e.exception.code, 1)


    @patch("opencue.api.findJob")
    def test_stagger_negative_increments(self, mock_findJob):
        """Test stagger operations with negative increment validation"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(stagger=["test_job", "1-10", "-1"], force=True)
        with self.assertRaises(SystemExit) as e:
            cuemain.handleArgs(args)

        self.assertEqual(e.exception.code, 1)


    @patch("opencue.api.findJob")
    def test_stagger_nonnumeric_increments(self, mock_findJob):
        """Test stagger operations with non numeric increment validation"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(stagger=["test_job", "1-10", "a"], force=True)
        with self.assertRaises(SystemExit) as e:
            cuemain.handleArgs(args)

        self.assertEqual(e.exception.code, 1)


    # -------------- Reorder operations with position valdiation test --------------

    @patch("opencue.api.findJob")
    def test_reorder_first_operation(self, mock_findJob):
        """Test reorder operation to first position"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(reorder=["test_job", "1-10", "FIRST"], force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.reorderFrames.assert_called_once_with("1-10", "FIRST")


    @patch("opencue.api.findJob")
    def test_reorder_last_operation(self, mock_findJob):
        """Test reorder operation to last position"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(reorder=["test_job", "1-10", "LAST"], force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.reorderFrames.assert_called_once_with("1-10", "LAST")


    @patch("opencue.api.findJob")
    def test_reorder_reverse_operation(self, mock_findJob):
        """Test reorder operation to reverse position"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(reorder=["test_job", "1-10", "REVERSE"], force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.reorderFrames.assert_called_once_with("1-10", "REVERSE")


    @patch("opencue.api.findJob")
    def test_reorder_invalid_operation(self, mock_findJob):
        """Test reorder operation to invalid position"""
        mock_job = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(reorder=["test_job", "1-10", "ab"], force=True)
        with self.assertRaises(SystemExit) as e:
            cuemain.handleArgs(args)

        self.assertEqual(e.exception.code, 1)


    # -------------- Reorder operations with position valdiation test --------------

    @patch("opencue.api.findJob")
    @patch("cueadmin.util.promptYesNo")
    def test_eat_confirmation_prompt(self, mock_promptYesNo, mock_findJob):
        """Test prompt confirmation for eatFrames operation"""
        mock_job = MagicMock()
        mock_job.eatFrames = MagicMock()
        mock_findJob.return_value = mock_job
        mock_promptYesNo.return_value = True

        args = self._ns(eat="test_job", layer=["render_layer"], range="1-10", force=False)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_promptYesNo.assert_called_once_with("Eat specified frames on job test_job", False)
        mock_job.eatFrames.assert_called_once_with(layer=["render_layer"], range="1-10")


    @patch("opencue.api.findJob")
    @patch("cueadmin.util.promptYesNo")
    def test_kill_confirmation_prompt(self, mock_promptYesNo, mock_findJob):
        """Test prompt confirmation for killFrames operation"""
        mock_job = MagicMock()
        mock_job.killFrames = MagicMock()
        mock_findJob.return_value = mock_job
        mock_promptYesNo.return_value = True

        args = self._ns(kill="test_job", layer=["render_layer"], range="1-10", force=False)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_promptYesNo.assert_called_once_with("Kill specified frames on job test_job", False)
        mock_job.killFrames.assert_called_once_with(layer=["render_layer"], range="1-10")


    @patch("opencue.api.findJob")
    @patch("cueadmin.util.promptYesNo")
    def test_retry_confirmation_prompt(self, mock_promptYesNo, mock_findJob):
        """Test prompt confirmation for retryFrames operation"""
        mock_job = MagicMock()
        mock_job.retryFrames = MagicMock()
        mock_findJob.return_value = mock_job
        mock_promptYesNo.return_value = True

        args = self._ns(retry="test_job", layer=["render_layer"], range="1-10", force=False)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_promptYesNo.assert_called_once_with("Retry specified frames on job test_job", False)
        mock_job.retryFrames.assert_called_once_with(layer=["render_layer"], range="1-10")


    @patch("opencue.api.findJob")
    @patch("cueadmin.util.promptYesNo")
    def test_done_confirmation_prompt(self, mock_promptYesNo, mock_findJob):
        """Test prompt confirmation for done Frames operation"""
        mock_job = MagicMock()
        mock_job.markdoneFrames = MagicMock()
        mock_findJob.return_value = mock_job
        mock_promptYesNo.return_value = True

        args = self._ns(done="test_job", layer=["render_layer"], range="1-10", force=False)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_promptYesNo.assert_called_once_with("Mark done specified frames on job test_job",
                                                 False)
        mock_job.markdoneFrames.assert_called_once_with(layer=["render_layer"], range="1-10")


if __name__ == '__main__':
    unittest.main()
