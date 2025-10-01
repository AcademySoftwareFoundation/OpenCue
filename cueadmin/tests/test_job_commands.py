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


"""Tests for cueadmin job management commands."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import unittest
from unittest import mock

try:
    import cueadmin.common
    OPENCUE_AVAILABLE = True
except ImportError:
    # For testing without full OpenCue installation
    OPENCUE_AVAILABLE = False
    cueadmin = mock.MagicMock()


TEST_JOB_NAME = 'testShow-testJob'
TEST_JOB_NAME_2 = 'testShow-testJob2'
TEST_JOB_NAME_3 = 'testShow-testJob3'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class JobCommandTests(unittest.TestCase):
    """Tests for job management commands."""

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    @mock.patch('opencue.search.JobSearch.byMatch')
    def test_lj_lists_jobs_with_no_filter(self, mock_search, getStubMock):
        """-lj: lists all jobs when no filter is provided."""
        job_mock_1 = mock.Mock()
        job_mock_1.name = TEST_JOB_NAME
        job_mock_2 = mock.Mock()
        job_mock_2.name = TEST_JOB_NAME_2
        mock_result = mock.Mock()
        mock_result.jobs.jobs = [job_mock_1, job_mock_2]
        mock_search.return_value = mock_result

        args = self.parser.parse_args(['-lj'])

        with mock.patch('builtins.print') as mock_print:
            cueadmin.common.handleArgs(args)

        mock_search.assert_called_once_with([])
        # Verify both job names were printed
        self.assertEqual(mock_print.call_count, 2)

    @mock.patch('opencue.search.JobSearch.byMatch')
    def test_lj_lists_jobs_with_substring_match(self, mock_search, getStubMock):
        """-lj: lists jobs matching substring filter."""
        job_mock = mock.Mock()
        job_mock.name = TEST_JOB_NAME
        mock_result = mock.Mock()
        mock_result.jobs.jobs = [job_mock]
        mock_search.return_value = mock_result

        args = self.parser.parse_args(['-lj', 'testShow'])

        with mock.patch('builtins.print') as mock_print:
            cueadmin.common.handleArgs(args)

        mock_search.assert_called_once_with(['testShow'])
        mock_print.assert_called_once_with(TEST_JOB_NAME)

    @mock.patch('opencue.search.JobSearch.byMatch')
    def test_lj_lists_jobs_with_multiple_filters(self, mock_search, getStubMock):
        """-lj: lists jobs matching multiple substring filters."""
        job_mock_1 = mock.Mock()
        job_mock_1.name = TEST_JOB_NAME
        job_mock_2 = mock.Mock()
        job_mock_2.name = TEST_JOB_NAME_2
        mock_result = mock.Mock()
        mock_result.jobs.jobs = [job_mock_1, job_mock_2]
        mock_search.return_value = mock_result

        args = self.parser.parse_args(['-lj', 'testShow', 'testJob'])

        with mock.patch('builtins.print'):
            cueadmin.common.handleArgs(args)

        mock_search.assert_called_once_with(['testShow', 'testJob'])

    @mock.patch('cueadmin.output.displayJobs')
    @mock.patch('opencue.search.JobSearch.byMatch')
    def test_lji_displays_job_info(self, mock_search, mock_display, getStubMock):
        """-lji: displays detailed job information."""
        job1 = mock.Mock()
        job2 = mock.Mock()
        mock_result = mock.Mock()
        mock_result.jobs.jobs = [job1, job2]
        mock_search.return_value = mock_result

        args = self.parser.parse_args(['-lji'])
        cueadmin.common.handleArgs(args)

        mock_search.assert_called_once_with([])
        # Verify displayJobs was called with wrapped job objects
        self.assertEqual(mock_display.call_count, 1)
        displayed_jobs = mock_display.call_args[0][0]
        self.assertEqual(len(displayed_jobs), 2)

    @mock.patch('cueadmin.output.displayJobs')
    @mock.patch('opencue.search.JobSearch.byMatch')
    def test_lji_with_filter(self, mock_search, mock_display, getStubMock):
        """-lji: displays job info with filter."""
        job1 = mock.Mock()
        mock_result = mock.Mock()
        mock_result.jobs.jobs = [job1]
        mock_search.return_value = mock_result

        args = self.parser.parse_args(['-lji', 'testShow'])
        cueadmin.common.handleArgs(args)

        mock_search.assert_called_once_with(['testShow'])
        mock_display.assert_called_once()

    @mock.patch('opencue.api.findJob')
    def test_pause_single_job(self, mock_find, getStubMock):
        """-pause: pauses a single job."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-pause', TEST_JOB_NAME])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        job.pause.assert_called_once()

    @mock.patch('opencue.api.findJob')
    def test_pause_multiple_jobs(self, mock_find, getStubMock):
        """-pause: pauses multiple jobs."""
        job1 = mock.Mock()
        job2 = mock.Mock()
        job3 = mock.Mock()
        mock_find.side_effect = [job1, job2, job3]

        args = self.parser.parse_args(['-pause', TEST_JOB_NAME, TEST_JOB_NAME_2, TEST_JOB_NAME_3])
        cueadmin.common.handleArgs(args)

        self.assertEqual(mock_find.call_count, 3)
        job1.pause.assert_called_once()
        job2.pause.assert_called_once()
        job3.pause.assert_called_once()

    @mock.patch('opencue.api.findJob')
    def test_pause_invalid_job_raises_exception(self, mock_find, getStubMock):
        """-pause: raises exception for invalid job name."""
        mock_find.side_effect = Exception("Job not found")

        args = self.parser.parse_args(['-pause', 'invalid-job'])

        with self.assertRaises(Exception):
            cueadmin.common.handleArgs(args)

    @mock.patch('opencue.api.findJob')
    def test_unpause_single_job(self, mock_find, getStubMock):
        """-unpause: unpauses a single job."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-unpause', TEST_JOB_NAME])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        job.resume.assert_called_once()

    @mock.patch('opencue.api.findJob')
    def test_unpause_multiple_jobs(self, mock_find, getStubMock):
        """-unpause: unpauses multiple jobs."""
        job1 = mock.Mock()
        job2 = mock.Mock()
        mock_find.side_effect = [job1, job2]

        args = self.parser.parse_args(['-unpause', TEST_JOB_NAME, TEST_JOB_NAME_2])
        cueadmin.common.handleArgs(args)

        self.assertEqual(mock_find.call_count, 2)
        job1.resume.assert_called_once()
        job2.resume.assert_called_once()

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('opencue.api.findJob')
    def test_kill_single_job_with_confirmation(self, mock_find, mock_prompt, getStubMock):
        """-kill: kills a single job with confirmation."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-kill', TEST_JOB_NAME])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        mock_prompt.assert_called_once()
        job.kill.assert_called_once()

    @mock.patch('opencue.api.findJob')
    def test_kill_with_force_flag(self, mock_find, getStubMock):
        """-kill with -force: kills job without confirmation."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-kill', TEST_JOB_NAME, '-force'])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        job.kill.assert_called_once()

    @mock.patch('cueadmin.util.promptYesNo', return_value=False)
    @mock.patch('opencue.api.findJob')
    def test_kill_cancelled_by_user(self, mock_find, mock_prompt, getStubMock):
        """-kill: does not kill job when user cancels confirmation."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-kill', TEST_JOB_NAME])
        cueadmin.common.handleArgs(args)

        mock_prompt.assert_called_once()
        job.kill.assert_not_called()

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('opencue.api.findJob')
    def test_kill_multiple_jobs(self, mock_find, mock_prompt, getStubMock):
        """-kill: kills multiple jobs with confirmation."""
        job1 = mock.Mock()
        job2 = mock.Mock()
        mock_find.side_effect = [job1, job2]

        args = self.parser.parse_args(['-kill', TEST_JOB_NAME, TEST_JOB_NAME_2])
        cueadmin.common.handleArgs(args)

        self.assertEqual(mock_find.call_count, 2)
        mock_prompt.assert_called_once()
        job1.kill.assert_called_once()
        job2.kill.assert_called_once()

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('opencue.api.getJobs')
    def test_kill_all_jobs(self, mock_get_jobs, mock_prompt, getStubMock):
        """-kill-all: kills all jobs with confirmation."""
        job1 = mock.Mock()
        job2 = mock.Mock()
        job3 = mock.Mock()
        mock_get_jobs.return_value = [job1, job2, job3]

        args = self.parser.parse_args(['-kill-all'])
        cueadmin.common.handleArgs(args)

        mock_get_jobs.assert_called_once()
        mock_prompt.assert_called_once()
        job1.kill.assert_called_once()
        job2.kill.assert_called_once()
        job3.kill.assert_called_once()

    @mock.patch('opencue.api.getJobs')
    def test_kill_all_with_force_flag(self, mock_get_jobs, getStubMock):
        """-kill-all with -force: kills all jobs without confirmation."""
        job1 = mock.Mock()
        job2 = mock.Mock()
        mock_get_jobs.return_value = [job1, job2]

        args = self.parser.parse_args(['-kill-all', '-force'])
        cueadmin.common.handleArgs(args)

        mock_get_jobs.assert_called_once()
        job1.kill.assert_called_once()
        job2.kill.assert_called_once()

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('opencue.api.findJob')
    def test_retry_single_job(self, mock_find, mock_prompt, getStubMock):
        """-retry: retries dead frames for a single job."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-retry', TEST_JOB_NAME])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        mock_prompt.assert_called_once()
        job.retryFrames.assert_called_once()

    @mock.patch('opencue.api.findJob')
    def test_retry_with_force_flag(self, mock_find, getStubMock):
        """-retry with -force: retries without confirmation."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-retry', TEST_JOB_NAME, '-force'])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        job.retryFrames.assert_called_once()

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('opencue.api.findJob')
    def test_retry_multiple_jobs(self, mock_find, mock_prompt, getStubMock):
        """-retry: retries dead frames for multiple jobs."""
        job1 = mock.Mock()
        job2 = mock.Mock()
        mock_find.side_effect = [job1, job2]

        args = self.parser.parse_args(['-retry', TEST_JOB_NAME, TEST_JOB_NAME_2])
        cueadmin.common.handleArgs(args)

        self.assertEqual(mock_find.call_count, 2)
        mock_prompt.assert_called_once()
        job1.retryFrames.assert_called_once()
        job2.retryFrames.assert_called_once()

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('opencue.api.getJobs')
    def test_retry_all_jobs(self, mock_get_jobs, mock_prompt, getStubMock):
        """-retry-all: retries dead frames for all jobs."""
        job1 = mock.Mock()
        job2 = mock.Mock()
        mock_get_jobs.return_value = [job1, job2]

        args = self.parser.parse_args(['-retry-all'])
        cueadmin.common.handleArgs(args)

        mock_get_jobs.assert_called_once()
        mock_prompt.assert_called_once()
        job1.retryFrames.assert_called_once()
        job2.retryFrames.assert_called_once()

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('cueadmin.common.DependUtil.dropAllDepends')
    def test_drop_depends_single_job(self, mock_drop, mock_prompt, getStubMock):
        """-drop-depends: drops all dependencies for a single job."""
        args = self.parser.parse_args(['-drop-depends', TEST_JOB_NAME])
        cueadmin.common.handleArgs(args)

        mock_prompt.assert_called_once()
        mock_drop.assert_called_once_with(TEST_JOB_NAME)

    @mock.patch('cueadmin.common.DependUtil.dropAllDepends')
    def test_drop_depends_with_force_flag(self, mock_drop, getStubMock):
        """-drop-depends with -force: drops dependencies without confirmation."""
        args = self.parser.parse_args(['-drop-depends', TEST_JOB_NAME, '-force'])
        cueadmin.common.handleArgs(args)

        mock_drop.assert_called_once_with(TEST_JOB_NAME)

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('cueadmin.common.DependUtil.dropAllDepends')
    def test_drop_depends_multiple_jobs(self, mock_drop, mock_prompt, getStubMock):
        """-drop-depends: drops dependencies for multiple jobs."""
        args = self.parser.parse_args(['-drop-depends', TEST_JOB_NAME, TEST_JOB_NAME_2])
        cueadmin.common.handleArgs(args)

        mock_prompt.assert_called_once()
        self.assertEqual(mock_drop.call_count, 2)
        mock_drop.assert_any_call(TEST_JOB_NAME)
        mock_drop.assert_any_call(TEST_JOB_NAME_2)

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('opencue.api.findJob')
    def test_set_min_cores_with_confirmation(self, mock_find, mock_prompt, getStubMock):
        """-set-min-cores: sets minimum cores for a job with confirmation."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-set-min-cores', TEST_JOB_NAME, '4.0'])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        mock_prompt.assert_called_once()
        job.setMinCores.assert_called_once_with(4.0)

    @mock.patch('opencue.api.findJob')
    def test_set_min_cores_with_force_flag(self, mock_find, getStubMock):
        """-set-min-cores with -force: sets min cores without confirmation."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-set-min-cores', TEST_JOB_NAME, '2.0', '-force'])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        job.setMinCores.assert_called_once_with(2.0)

    @mock.patch('opencue.api.findJob')
    def test_set_min_cores_with_integer_value(self, mock_find, getStubMock):
        """-set-min-cores: accepts integer values and converts to float."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-set-min-cores', TEST_JOB_NAME, '8', '-force'])
        cueadmin.common.handleArgs(args)

        job.setMinCores.assert_called_once_with(8.0)

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('opencue.api.findJob')
    def test_set_max_cores_with_confirmation(self, mock_find, mock_prompt, getStubMock):
        """-set-max-cores: sets maximum cores for a job with confirmation."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-set-max-cores', TEST_JOB_NAME, '16.0'])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        mock_prompt.assert_called_once()
        job.setMaxCores.assert_called_once_with(16.0)

    @mock.patch('opencue.api.findJob')
    def test_set_max_cores_with_force_flag(self, mock_find, getStubMock):
        """-set-max-cores with -force: sets max cores without confirmation."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-set-max-cores', TEST_JOB_NAME, '32.0', '-force'])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        job.setMaxCores.assert_called_once_with(32.0)

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('opencue.api.findJob')
    def test_priority_with_confirmation(self, mock_find, mock_prompt, getStubMock):
        """-priority: sets job priority with confirmation."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-priority', TEST_JOB_NAME, '200'])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        mock_prompt.assert_called_once()
        job.setPriority.assert_called_once_with(200)

    @mock.patch('opencue.api.findJob')
    def test_priority_with_force_flag(self, mock_find, getStubMock):
        """-priority with -force: sets priority without confirmation."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-priority', TEST_JOB_NAME, '100', '-force'])
        cueadmin.common.handleArgs(args)

        mock_find.assert_called_once_with(TEST_JOB_NAME)
        job.setPriority.assert_called_once_with(100)

    @mock.patch('opencue.api.findJob')
    def test_priority_with_negative_value(self, mock_find, getStubMock):
        """-priority: accepts negative priority values."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-priority', TEST_JOB_NAME, '-50', '-force'])
        cueadmin.common.handleArgs(args)

        job.setPriority.assert_called_once_with(-50)

    @mock.patch('opencue.api.findJob')
    def test_priority_with_zero_value(self, mock_find, getStubMock):
        """-priority: accepts zero as priority value."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-priority', TEST_JOB_NAME, '0', '-force'])
        cueadmin.common.handleArgs(args)

        job.setPriority.assert_called_once_with(0)

    @mock.patch('opencue.api.findJob')
    def test_job_not_found_error_handling(self, mock_find, getStubMock):
        """Test proper error handling when job is not found."""
        mock_find.side_effect = Exception("Job not found: %s" % TEST_JOB_NAME)

        args = self.parser.parse_args(['-pause', TEST_JOB_NAME])

        with self.assertRaises(Exception) as context:
            cueadmin.common.handleArgs(args)

        self.assertIn("Job not found", str(context.exception))

    @mock.patch('opencue.search.JobSearch.byMatch')
    def test_lj_with_no_results(self, mock_search, getStubMock):
        """-lj: handles case with no matching jobs."""
        mock_result = mock.Mock()
        mock_result.jobs.jobs = []
        mock_search.return_value = mock_result

        args = self.parser.parse_args(['-lj', 'nonexistent'])

        with mock.patch('builtins.print') as mock_print:
            cueadmin.common.handleArgs(args)

        mock_search.assert_called_once_with(['nonexistent'])
        # No jobs to print
        mock_print.assert_not_called()

    @mock.patch('cueadmin.output.displayJobs')
    @mock.patch('opencue.search.JobSearch.byMatch')
    def test_lji_with_various_job_states(self, mock_search, mock_display, getStubMock):
        """-lji: displays jobs in various states (running, finished, paused)."""
        running_job = mock.Mock()
        running_job.data.is_paused = False
        running_job.data.state = 'RUNNING'

        paused_job = mock.Mock()
        paused_job.data.is_paused = True
        paused_job.data.state = 'PAUSED'

        finished_job = mock.Mock()
        finished_job.data.is_paused = False
        finished_job.data.state = 'FINISHED'

        mock_result = mock.Mock()
        mock_result.jobs.jobs = [running_job, paused_job, finished_job]
        mock_search.return_value = mock_result

        args = self.parser.parse_args(['-lji'])
        cueadmin.common.handleArgs(args)

        mock_display.assert_called_once()
        displayed_jobs = mock_display.call_args[0][0]
        self.assertEqual(len(displayed_jobs), 3)

    @mock.patch('opencue.api.findJob')
    def test_set_min_cores_invalid_value_raises_error(self, mock_find, getStubMock):
        """-set-min-cores: raises error for invalid core value."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-set-min-cores', TEST_JOB_NAME, 'invalid', '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

    @mock.patch('opencue.api.findJob')
    def test_set_max_cores_invalid_value_raises_error(self, mock_find, getStubMock):
        """-set-max-cores: raises error for invalid core value."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-set-max-cores', TEST_JOB_NAME, 'invalid', '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

    @mock.patch('opencue.api.findJob')
    def test_priority_invalid_value_raises_error(self, mock_find, getStubMock):
        """-priority: raises error for invalid priority value."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-priority', TEST_JOB_NAME, 'invalid', '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

    @mock.patch('opencue.api.findJob')
    def test_multiple_job_operations_sequentially(self, mock_find, getStubMock):
        """Test that multiple jobs can be processed in sequence for pause."""
        job1 = mock.Mock()
        job2 = mock.Mock()
        job3 = mock.Mock()

        mock_find.side_effect = [job1, job2, job3]

        args = self.parser.parse_args(['-pause', TEST_JOB_NAME, TEST_JOB_NAME_2, TEST_JOB_NAME_3])
        cueadmin.common.handleArgs(args)

        # Verify all three jobs were found and paused
        self.assertEqual(mock_find.call_count, 3)
        mock_find.assert_any_call(TEST_JOB_NAME)
        mock_find.assert_any_call(TEST_JOB_NAME_2)
        mock_find.assert_any_call(TEST_JOB_NAME_3)

        job1.pause.assert_called_once()
        job2.pause.assert_called_once()
        job3.pause.assert_called_once()

    @mock.patch('opencue.api.findJob')
    def test_set_min_cores_with_fractional_cores(self, mock_find, getStubMock):
        """-set-min-cores: accepts fractional core values."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-set-min-cores', TEST_JOB_NAME, '0.5', '-force'])
        cueadmin.common.handleArgs(args)

        job.setMinCores.assert_called_once_with(0.5)

    @mock.patch('opencue.api.findJob')
    def test_set_max_cores_with_large_value(self, mock_find, getStubMock):
        """-set-max-cores: accepts large core values."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-set-max-cores', TEST_JOB_NAME, '1000.0', '-force'])
        cueadmin.common.handleArgs(args)

        job.setMaxCores.assert_called_once_with(1000.0)

    @mock.patch('opencue.api.findJob')
    def test_priority_with_large_value(self, mock_find, getStubMock):
        """-priority: accepts large priority values."""
        job = mock.Mock()
        mock_find.return_value = job

        args = self.parser.parse_args(['-priority', TEST_JOB_NAME, '10000', '-force'])
        cueadmin.common.handleArgs(args)

        job.setPriority.assert_called_once_with(10000)


if __name__ == '__main__':
    unittest.main()
