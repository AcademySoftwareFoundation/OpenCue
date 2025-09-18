import unittest
from unittest import mock
import sys
import io

import cueman.main as main

class TestCuemanIntegrationWorkflows(unittest.TestCase):
    """Integration tests for complete cueman workflows."""
    
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    @mock.patch('opencue.api.findJob')
    def test_batch_operation_workflow(self, mock_find, mock_stub):
        mock_stub.return_value = mock.Mock()
        mock_job1 = mock.Mock()
        mock_job2 = mock.Mock()
        mock_find.return_value = [mock_job1, mock_job2]
        sys.argv = ['cueman', '-kill', 'job1', 'job2']
        main.main(sys.argv)
        mock_job1.kill.assert_called_once()
        mock_job2.kill.assert_called_once()
    
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    @mock.patch('opencue.api.findFrame')
    def test_frame_management_workflow(self, mock_find, mock_stub):
        mock_stub.return_value = mock.Mock()
        mock_frame1 = mock.Mock()
        mock_frame2 = mock.Mock()
        mock_find.return_value = [mock_frame1, mock_frame2]
        sys.argv = ['cueman', '-ll', 'job1', '-state', 'DEAD']
        main.main(sys.argv)
        sys.argv = ['cueman', '-retry', 'frame1']
        main.main(sys.argv)
        mock_frame1.retry.assert_called_once()
        sys.argv = ['cueman', '-kill', 'frame2']
        main.main(sys.argv)
        mock_frame2.kill.assert_called_once()

    @mock.patch('opencue.api.findJob', side_effect=Exception("API failure"))
    def test_error_recovery_scenarios(self, mock_find):
        sys.argv = ['cueman', '-pause', 'job1']
        with self.assertRaises(SystemExit):
            main.main(sys.argv)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    @mock.patch('opencue.api.findFrame')
    def test_complex_filter_combination_workflows(self, mock_find, mock_stub):
        # Simulate multiple filters
        mock_stub.return_value = mock.Mock()
        mock_find.return_value = [mock.Mock(name='frame1')]
        sys.argv = ['cueman', '-ll', 'job1', '-state', 'DEAD', '-layer', 'layer1']
        main.main(sys.argv)
        mock_find.assert_called()

    def test_help_text_and_version_display(self):
        sys.argv = ['cueman', '--help']
        with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit):
                main.main(sys.argv)
            self.assertIn('usage', mock_stdout.getvalue())
        sys.argv = ['cueman', '--version']
        with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit):
                main.main(sys.argv)
            self.assertIn('cueman', mock_stdout.getvalue())

    def test_invalid_command_handling(self):
        # Simulate invalid command
        sys.argv = ['cueman', 'invalidcmd']
        with mock.patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            with self.assertRaises(SystemExit):
                main.main(sys.argv)
            self.assertIn('error', mock_stderr.getvalue())

if __name__ == '__main__':
    unittest.main()
