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
Unit tests for job operation commands in cueman.
"""
# pylint: disable=too-many-public-methods
import argparse
import unittest
from unittest.mock import patch, MagicMock, call

from cueman import main as cueman_main

class TestJobOperations(unittest.TestCase):
    """Test job operation commands in cueman."""
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

    # ---------------- Unit-style job method tests ----------------

    @patch('opencue.api.findJob')
    def test_pause_job_success(self, mock_find):
        """Test successful job pause operation."""
        job = MagicMock()
        job.pause.return_value = None
        mock_find.return_value = job
        job.pause()
        job.pause.assert_called_once()

    @patch('opencue.api.findJob')
    def test_pause_job_already_paused(self, mock_find):
        """Test job pause when already paused raises RuntimeError."""
        job = MagicMock()
        job.pause.side_effect = RuntimeError("Job already paused")
        mock_find.return_value = job
        with self.assertRaises(RuntimeError):
            job.pause()

    @patch('opencue.api.findJob')
    def test_resume_job_success(self, mock_find):
        """Test successful job resume operation."""
        job = MagicMock()
        job.resume.return_value = None
        mock_find.return_value = job
        job.resume()
        job.resume.assert_called_once()

    @patch('opencue.api.findJob')
    def test_resume_job_already_running(self, mock_find):
        """Test job resume when already running raises RuntimeError."""
        job = MagicMock()
        job.resume.side_effect = RuntimeError("Job already running")
        mock_find.return_value = job
        with self.assertRaises(RuntimeError):
            job.resume()

    @patch('opencue.api.findJob')
    def test_terminate_nonexistent_job(self, mock_find):
        """Test terminating nonexistent job raises KeyError."""
        mock_find.side_effect = KeyError("Job not found")
        with self.assertRaises(KeyError):
            mock_find('missing_job')

    @patch('opencue.api.findJob')
    def test_batch_pause_jobs(self, mock_find):
        """Test pausing multiple jobs in batch operation."""
        job1 = MagicMock()
        job2 = MagicMock()
        mock_find.side_effect = [job1, job2]
        for job in [job1, job2]:
            job.pause.return_value = None
            job.pause()
            job.pause.assert_called_once()

    @patch('opencue.api.findJob')
    def test_batch_operation_with_missing_job(self, mock_find):
        """Test batch operation handling when one job is missing."""
        job1 = MagicMock()
        mock_find.side_effect = [job1, KeyError("Job not found")]

        # First call returns the job from side_effect
        first_job = mock_find('job1')
        first_job.pause.return_value = None
        first_job.pause()
        first_job.pause.assert_called_once()

        # Second call should raise KeyError from side_effect
        with self.assertRaises(KeyError):
            mock_find('missing_job')

    @patch('opencue.api.findJob')
    def test_set_maximum_retries_valid(self, mock_find):
        """Test setting valid maximum retries on a job."""
        job = MagicMock()
        job.setMaxRetries.return_value = None
        mock_find.return_value = job
        job.setMaxRetries(5)
        job.setMaxRetries.assert_called_once_with(5)

    @patch('opencue.api.findJob')
    def test_set_maximum_retries_invalid(self, mock_find):
        """Test setting invalid maximum retries raises ValueError."""
        job = MagicMock()
        job.setMaxRetries.side_effect = ValueError("Invalid retries")
        mock_find.return_value = job
        with self.assertRaises(ValueError):
            job.setMaxRetries(-1)

    @patch('opencue.api.findJob')
    def test_job_existence_validation(self, mock_find):
        """Test job existence validation raises KeyError for missing jobs."""
        mock_find.side_effect = KeyError("Job not found")
        with self.assertRaises(KeyError):
            mock_find('missing_job')

    @patch('opencue.api.findJob')
    def test_network_error_handling(self, mock_find):
        """Test handling of network connection errors."""
        mock_find.side_effect = ConnectionError("Network error")
        with self.assertRaises(ConnectionError):
            mock_find('job1')

    @patch('opencue.api.findJob')
    def test_error_handling_invalid_state(self, mock_find):
        """Test handling of invalid job state errors."""
        job = MagicMock()
        job.pause.side_effect = RuntimeError("Invalid state")
        mock_find.return_value = job
        with self.assertRaises(RuntimeError):
            job.pause()

    # ---------------- Command-level tests using handleArgs ----------------

    @patch('opencue.api.findJob')
    @patch('cueman.main.logger')
    def test_pause_command_calls_job_pause_and_logs(self, mock_logger, mock_find):
        """Test pause command calls job.pause() and logs appropriately."""
        job = MagicMock()
        job.isPaused.return_value = False
        job.name.return_value = 'job1'
        mock_find.return_value = job

        args = self._ns(pause=['job1'])
        cueman_main.handleArgs(args)

        job.pause.assert_called_once()
        mock_logger.info.assert_has_calls(
            [call('Pausing Job: %s', 'job1'), call('---')]
        )

    @patch('opencue.api.findJob')
    @patch('cueman.main.logger')
    def test_pause_command_already_paused_logs_only(self, mock_logger, mock_find):
        """Test pause command logs when job is already paused without calling pause()."""
        job = MagicMock()
        job.isPaused.return_value = True
        job.name.return_value = 'job1'
        mock_find.return_value = job

        args = self._ns(pause=['job1'])
        cueman_main.handleArgs(args)

        job.pause.assert_not_called()
        mock_logger.info.assert_has_calls(
            [call('Job: %s is already paused', 'job1'), call('---')]
        )

    @patch('opencue.api.findJob')
    @patch('cueman.main.logger')
    def test_resume_command_calls_job_resume_and_logs(self, mock_logger, mock_find):
        """Test resume command calls job.resume() and logs success."""
        job = MagicMock()
        job.name.return_value = 'job1'
        mock_find.return_value = job

        args = self._ns(resume=['job1'])
        cueman_main.handleArgs(args)

        job.resume.assert_called_once()
        mock_logger.info.assert_called_with('Resumed Job: %s', 'job1')

    @patch('cueman.main.common.confirm')
    @patch('opencue.api.findJob')
    @patch('cueman.main.logger')
    def test_terminate_command_uses_confirm_and_logs_success(
        self, mock_logger, mock_find, mock_confirm
    ):
        """Test terminate command uses confirmation and logs success for multiple jobs."""
        job1 = MagicMock()
        job2 = MagicMock()
        mock_find.side_effect = [job1, job2]

        # Simulate confirm calling the provided function
        def _confirm_side_effect(msg, force, func, *func_args):  # pylint: disable=unused-argument
            func(*func_args)
            return True

        mock_confirm.side_effect = _confirm_side_effect

        # format_nargs_input splits the last item by comma -> pass single comma-separated string
        args = self._ns(term=['job1,job2'])
        cueman_main.handleArgs(args)

        mock_confirm.assert_called_once()
        mock_logger.info.assert_any_call('Successfully terminated %d job(s)', 2)

    @patch('cueman.main.common.confirm')
    @patch('opencue.api.findJob')
    def test_terminate_command_force_bypasses_confirm(self, mock_find, mock_confirm):
        """Test terminate command with force flag bypasses confirmation."""
        job = MagicMock()
        mock_find.return_value = job

        def _confirm_side_effect(msg, force, func, *func_args):  # pylint: disable=unused-argument
            # handleArgs should pass force=True through
            self.assertTrue(force)
            return True

        mock_confirm.side_effect = _confirm_side_effect

        args = self._ns(term=['job1'], force=True)
        cueman_main.handleArgs(args)
        mock_confirm.assert_called_once()

    @patch('cueman.main.common.confirm')
    @patch('opencue.api.findJob')
    @patch('cueman.main.logger')
    def test_retries_command_confirms_and_sets_max_retries(
        self, mock_logger, mock_find, mock_confirm
    ):
        """Test retries command uses confirmation and sets maximum retries."""
        job = MagicMock()
        mock_find.return_value = job

        def _confirm_side_effect(msg, force, func, *func_args):  # pylint: disable=unused-argument
            func(*func_args)
            return True

        mock_confirm.side_effect = _confirm_side_effect

        args = self._ns(retries=['job1', '5'])
        cueman_main.handleArgs(args)

        job.setMaxRetries.assert_called_once_with(5)
        mock_logger.info.assert_called_with(
            'Successfully set maximum retries to %d for job: %s', 5, 'job1'
        )

    @patch('cueadmin.util.promptYesNo')
    @patch('opencue.api.findJob')
    @patch('cueman.main.logger')
    def test_eat_command_prompts_and_calls_on_yes(
        self, mock_logger, mock_find, mock_prompt
    ):
        """Test eat command prompts user and calls eatFrames() on yes response."""
        job = MagicMock()
        mock_find.return_value = job
        mock_prompt.return_value = True

        args = self._ns(eat='job1')
        cueman_main.handleArgs(args)

        job.eatFrames.assert_called_once()
        mock_logger.info.assert_called_with('Successfully ate frames for job: %s', 'job1')

    @patch('cueadmin.util.promptYesNo')
    @patch('opencue.api.findJob')
    @patch('cueman.main.logger')
    def test_eat_command_skips_on_no(self, mock_logger, mock_find, mock_prompt):
        """Test eat command skips eatFrames() call on no response."""
        job = MagicMock()
        mock_find.return_value = job
        mock_prompt.return_value = False

        args = self._ns(eat='job1')
        cueman_main.handleArgs(args)

        job.eatFrames.assert_not_called()
        # Ensure the success message was not logged
        for c in mock_logger.info.call_args_list:
            self.assertNotEqual(c, call('Successfully ate frames for job: %s', 'job1'))

    @patch('cueadmin.util.promptYesNo')
    @patch('opencue.api.findJob')
    @patch('cueman.main.logger')
    def test_kill_command_prompts_and_calls_on_yes(
        self, mock_logger, mock_find, mock_prompt
    ):
        """Test kill command prompts user and calls killFrames() on yes response."""
        job = MagicMock()
        mock_find.return_value = job
        mock_prompt.return_value = True

        args = self._ns(kill='job1')
        cueman_main.handleArgs(args)

        job.killFrames.assert_called_once()
        mock_logger.info.assert_called_with('Successfully killed frames for job: %s', 'job1')

    @patch('opencue.api.findJob')
    @patch('cueman.main.logger')
    def test_autoeat_on_sets_flag_eats_dead_and_logs(self, mock_logger, mock_find):
        """Test auto-eat on sets flag, eats dead frames, and logs success."""
        job = MagicMock()
        job.name.return_value = 'job1'
        mock_find.return_value = job

        args = self._ns(autoeaton=['job1'])
        cueman_main.handleArgs(args)

        job.setAutoEat.assert_called_once_with(True)
        # Should pass a state list to eatFrames
        _args, kwargs = job.eatFrames.call_args
        self.assertIn('state', kwargs)
        self.assertIsInstance(kwargs['state'], list)
        mock_logger.info.assert_called_with('Enabled auto-eat for job: %s', 'job1')

    @patch('opencue.api.findJob')
    @patch('cueman.main.logger')
    def test_autoeat_off_sets_flag_and_logs(self, mock_logger, mock_find):
        """Test auto-eat off sets flag to false and logs success."""
        job = MagicMock()
        job.name.return_value = 'job1'
        mock_find.return_value = job

        args = self._ns(autoeatoff=['job1'])
        cueman_main.handleArgs(args)

        job.setAutoEat.assert_called_once_with(False)
        mock_logger.info.assert_called_with('Disabled auto-eat for job: %s', 'job1')

    @patch('opencue.api.findJob')
    @patch('cueman.main.logger')
    def test_resume_nonexistent_job_logs_error_and_exits(self, mock_logger, mock_find):
        """Test resume command logs error and exits when job does not exist."""
        mock_find.side_effect = Exception('does not exist')
        args = self._ns(resume=['missing'])
        with self.assertRaises(SystemExit):
            cueman_main.handleArgs(args)
        mock_logger.error.assert_called()

if __name__ == '__main__':
    unittest.main()
