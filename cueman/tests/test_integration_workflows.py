"""Integration tests for complete cueman workflows."""

import io
import sys
import unittest
from unittest import mock

from cueman import main


class TestCuemanIntegrationWorkflows(unittest.TestCase):
    """Integration tests for complete cueman workflows."""

    @mock.patch("opencue.cuebot.Cuebot.getStub")
    @mock.patch("opencue.api.findJob")
    def test_batch_operation_workflow(self, mock_find, mock_stub):
        """Test batch operations on multiple jobs."""
        mock_stub.return_value = mock.Mock()
        mock_job1 = mock.Mock()
        mock_job1.name.return_value = "job1"
        mock_job1.isPaused.return_value = False
        mock_job2 = mock.Mock()
        mock_job2.name.return_value = "job2"
        mock_job2.isPaused.return_value = False

        # Test pausing multiple jobs (comma-separated format)
        mock_find.side_effect = [mock_job1, mock_job2]
        sys.argv = ["cueman", "-pause", "job1,job2"]

        # The main function should complete without raising SystemExit
        main.main(sys.argv)

        # Check that both jobs were paused
        mock_job1.pause.assert_called_once()
        mock_job2.pause.assert_called_once()
        # Verify findJob was called for both jobs
        self.assertEqual(mock_find.call_count, 2)

    @mock.patch("opencue.cuebot.Cuebot.getStub")
    @mock.patch("cueman.main.displayLayers")
    @mock.patch("opencue.api.findJob")
    def test_frame_management_workflow(
        self, mock_find_job, mock_display_layers, mock_stub
    ):
        """Test frame management operations."""
        mock_stub.return_value = mock.Mock()
        mock_job = mock.Mock()
        mock_find_job.return_value = mock_job

        # Test listing layers with state filter
        sys.argv = ["cueman", "-ll", "job1", "-state", "DEAD"]

        # The main function should complete successfully
        main.main(sys.argv)

        # Verify displayLayers was called with the job
        mock_display_layers.assert_called_once_with(mock_job)

    @mock.patch("opencue.api.findJob", side_effect=Exception("API failure"))
    def test_error_recovery_scenarios(self, mock_find):
        sys.argv = ["cueman", "-pause", "job1"]
        with self.assertRaises(SystemExit):
            main.main(sys.argv)

    @mock.patch("opencue.cuebot.Cuebot.getStub")
    @mock.patch("cueman.main.displayLayers")
    @mock.patch("opencue.api.findJob")
    def test_complex_filter_combination_workflows(
        self, mock_find_job, mock_display_layers, mock_stub
    ):
        """Test complex filter combinations."""
        mock_stub.return_value = mock.Mock()
        mock_job = mock.Mock()
        mock_find_job.return_value = mock_job

        sys.argv = ["cueman", "-ll", "job1", "-state", "DEAD", "-layer", "layer1"]

        # The main function should complete successfully
        main.main(sys.argv)

        # Verify displayLayers was called
        mock_display_layers.assert_called_once_with(mock_job)

    def test_help_text_and_version_display(self):
        sys.argv = ["cueman", "--help"]
        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit):
                main.main(sys.argv)
            self.assertIn("usage", mock_stdout.getvalue())
        sys.argv = ["cueman", "--version"]
        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit):
                main.main(sys.argv)
            self.assertIn("cueman", mock_stdout.getvalue())

    def test_invalid_command_handling(self):
        # Simulate invalid command
        sys.argv = ["cueman", "invalidcmd"]
        with mock.patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            with self.assertRaises(SystemExit):
                main.main(sys.argv)
            self.assertIn("error", mock_stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
