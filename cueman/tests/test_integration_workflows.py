import unittest
from unittest import mock
import sys
import io

import cueman.main as main

class TestCuemanIntegrationWorkflows(unittest.TestCase):
    """Integration tests for complete cueman workflows."""

    @mock.patch('opencue.api.findJob')
    @mock.patch('opencue.api.pauseJob')
    @mock.patch('opencue.api.modifyJob')
    @mock.patch('opencue.api.resumeJob')
    def test_complete_job_management_workflow(self, mock_resume, mock_modify, mock_pause, mock_find):
        # Simulate finding, pausing, modifying, and resuming a job
        mock_find.return_value = mock.Mock(name='job1')
        sys.argv = ['cueman', 'pause', 'job1']
        main.main(sys.argv)
        mock_pause.assert_called_once()
        sys.argv = ['cueman', 'modify', 'job1', '--priority', '100']
        main.main(sys.argv)
        mock_modify.assert_called_once()
        sys.argv = ['cueman', 'resume', 'job1']
        main.main(sys.argv)
        mock_resume.assert_called_once()

    @mock.patch('opencue.api.findFrame')
    @mock.patch('opencue.api.retryFrame')
    @mock.patch('opencue.api.killFrame')
    def test_frame_management_workflow(self, mock_kill, mock_retry, mock_find):
        # Simulate querying, filtering, retrying, and killing frames
        mock_find.return_value = [mock.Mock(name='frame1'), mock.Mock(name='frame2')]
        sys.argv = ['cueman', 'frames', 'job1', '--filter', 'state=DEAD']
        main.main(sys.argv)
        sys.argv = ['cueman', 'retry', 'frame1']
        main.main(sys.argv)
        mock_retry.assert_called_once()
        sys.argv = ['cueman', 'kill', 'frame2']
        main.main(sys.argv)
        mock_kill.assert_called_once()

    @mock.patch('opencue.api.findJob')
    @mock.patch('cueman.main.confirm_termination', return_value=True)
    @mock.patch('opencue.api.killJob')
    def test_batch_operation_workflow(self, mock_kill, mock_confirm, mock_find):
        # Simulate batch operation with confirmation
        mock_find.return_value = [mock.Mock(name='job1'), mock.Mock(name='job2')]
        sys.argv = ['cueman', 'kill', 'job1', 'job2']
        main.main(sys.argv)
        mock_confirm.assert_called_once()
        mock_kill.assert_called()

    @mock.patch('opencue.api.findJob', side_effect=Exception("API failure"))
    def test_error_recovery_scenarios(self, mock_find):
        # Simulate API failure and verify error handling
        sys.argv = ['cueman', 'pause', 'job1']
        with self.assertRaises(Exception):
            main.main(sys.argv)

    @mock.patch('opencue.api.findFrame')
    def test_complex_filter_combination_workflows(self, mock_find):
        # Simulate multiple filters
        mock_find.return_value = [mock.Mock(name='frame1')]
        sys.argv = ['cueman', 'frames', 'job1', '--filter', 'state=DEAD', '--filter', 'layer=layer1']
        main.main(sys.argv)
        mock_find.assert_called()

    def test_help_text_and_version_display(self):
        # Simulate --help and --version
        sys.argv = ['cueman', '--help']
        with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit):
                main.main(sys.argv)
            self.assertIn('usage', mock_stdout.getvalue())
        sys.argv = ['cueman', '--version']
        with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit):
                main.main(sys.argv)
            self.assertIn('version', mock_stdout.getvalue())

    def test_invalid_command_handling(self):
        # Simulate invalid command
        sys.argv = ['cueman', 'invalidcmd']
        with mock.patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            with self.assertRaises(SystemExit):
                main.main(sys.argv)
            self.assertIn('error', mock_stderr.getvalue())

if __name__ == '__main__':
    unittest.main()