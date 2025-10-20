"""Integration tests for complete cuecmd workflows."""

import io
import os
import sys
import tempfile
import unittest
from unittest import mock

from cuecmd import main


class TestCuecmdIntegrationWorkflows(unittest.TestCase):
    """Integration tests for complete cuecmd workflows."""

    @mock.patch("outline.cuerun.launch")
    def test_basic_command_execution_workflow(self, mock_launch):
        """Test basic workflow: command file -> outline -> submission."""
        mock_launch.return_value = ["mock_job"]

        # Create a temporary command file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'command 1'\n")
            f.write("echo 'command 2'\n")
            f.write("echo 'command 3'\n")
            temp_file = f.name

        try:
            sys.argv = ["cuecmd", temp_file]
            result = main.main(sys.argv)

            # Verify successful execution
            self.assertEqual(result, 0)
            mock_launch.assert_called_once()

            # Verify outline was created with correct parameters
            call_args = mock_launch.call_args
            outline = call_args[0][0]
            self.assertIsNotNone(outline)

        finally:
            os.unlink(temp_file)

    @mock.patch("outline.cuerun.launch")
    def test_chunked_execution_workflow(self, mock_launch):
        """Test chunked execution workflow."""
        mock_launch.return_value = ["mock_job"]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            for i in range(1, 21):
                f.write(f"echo 'command {i}'\n")
            temp_file = f.name

        try:
            # Submit with chunk size of 5 (should create 4 frames)
            sys.argv = ["cuecmd", temp_file, "--chunk", "5"]
            result = main.main(sys.argv)

            self.assertEqual(result, 0)
            mock_launch.assert_called_once()

            # Verify the outline
            outline = mock_launch.call_args[0][0]
            layers = outline.get_layers()
            self.assertEqual(len(layers), 1)
            # Frame range should be 1-4 (20 commands / 5 per chunk)
            self.assertIn("1-4", layers[0].get_arg("range"))

        finally:
            os.unlink(temp_file)

    @mock.patch("outline.cuerun.launch")
    def test_resource_specification_workflow(self, mock_launch):
        """Test workflow with custom resource specifications."""
        mock_launch.return_value = ["mock_job"]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'resource intensive command'\n")
            temp_file = f.name

        try:
            sys.argv = ["cuecmd", temp_file, "--cores", "8", "--memory", "16"]
            result = main.main(sys.argv)

            self.assertEqual(result, 0)
            mock_launch.assert_called_once()

            # Verify resources were set correctly
            outline = mock_launch.call_args[0][0]
            layer = outline.get_layers()[0]
            self.assertEqual(layer.get_arg("threads"), 8.0)
            self.assertEqual(layer.get_arg("memory"), "16384MB")

        finally:
            os.unlink(temp_file)

    def test_pretend_mode_workflow(self):
        """Test pretend mode doesn't submit job."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            with mock.patch("outline.cuerun.launch") as mock_launch:
                sys.argv = ["cuecmd", temp_file, "--pretend"]

                with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                    result = main.main(sys.argv)

                    self.assertEqual(result, 0)
                    # launch should not be called in pretend mode
                    mock_launch.assert_not_called()

                    # Verify output contains pretend mode information
                    output = mock_stdout.getvalue()
                    self.assertIn("Pretend Mode", output)
                    self.assertIn("Frame range", output)

        finally:
            os.unlink(temp_file)

    @mock.patch("outline.cuerun.launch")
    def test_pause_mode_workflow(self, mock_launch):
        """Test launching job in paused state."""
        mock_launch.return_value = ["mock_job"]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            sys.argv = ["cuecmd", temp_file, "--pause"]
            result = main.main(sys.argv)

            self.assertEqual(result, 0)
            mock_launch.assert_called_once()

            # Verify pause parameter was passed
            call_kwargs = mock_launch.call_args[1]
            self.assertTrue(call_kwargs.get("pause"))

        finally:
            os.unlink(temp_file)

    @mock.patch("outline.cuerun.launch")
    def test_custom_job_metadata_workflow(self, mock_launch):
        """Test workflow with custom job metadata."""
        mock_launch.return_value = ["mock_job"]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            sys.argv = [
                "cuecmd",
                temp_file,
                "--show",
                "test_show",
                "--shot",
                "test_shot",
                "--user",
                "test_user",
                "--job-name",
                "custom_job",
            ]
            result = main.main(sys.argv)

            self.assertEqual(result, 0)
            mock_launch.assert_called_once()

            # Verify metadata was set correctly
            outline = mock_launch.call_args[0][0]
            self.assertEqual(outline.get_show(), "test_show")
            self.assertEqual(outline.get_shot(), "test_shot")
            self.assertEqual(outline.get_user(), "test_user")
            self.assertEqual(outline.get_name(), "custom_job")

        finally:
            os.unlink(temp_file)

    def test_file_not_found_error_workflow(self):
        """Test error handling when command file doesn't exist."""
        sys.argv = ["cuecmd", "/nonexistent/file.txt"]

        with self.assertRaises(SystemExit) as cm:
            main.main(sys.argv)

        self.assertEqual(cm.exception.code, 1)

    def test_empty_file_error_workflow(self):
        """Test error handling for empty command file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            sys.argv = ["cuecmd", temp_file]

            with self.assertRaises(SystemExit) as cm:
                main.main(sys.argv)

            self.assertEqual(cm.exception.code, 1)

        finally:
            os.unlink(temp_file)

    @mock.patch("outline.cuerun.launch")
    def test_launch_failure_workflow(self, mock_launch):
        """Test handling of launch failures."""
        mock_launch.return_value = None

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            sys.argv = ["cuecmd", temp_file]

            with self.assertRaises(SystemExit) as cm:
                main.main(sys.argv)

            self.assertEqual(cm.exception.code, 1)

        finally:
            os.unlink(temp_file)

    @mock.patch("outline.cuerun.launch")
    def test_launch_exception_workflow(self, mock_launch):
        """Test handling of exceptions during launch."""
        mock_launch.side_effect = Exception("Launch failed")

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            sys.argv = ["cuecmd", temp_file]

            with self.assertRaises(SystemExit) as cm:
                main.main(sys.argv)

            self.assertEqual(cm.exception.code, 1)

        finally:
            os.unlink(temp_file)

    def test_help_text_display(self):
        """Test help text is displayed correctly."""
        sys.argv = ["cuecmd", "--help"]

        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit):
                main.main(sys.argv)

            output = mock_stdout.getvalue()
            self.assertIn("usage", output.lower())
            self.assertIn("command_file", output)
            self.assertIn("--chunk", output)

    @mock.patch("outline.cuerun.launch")
    def test_large_command_file_workflow(self, mock_launch):
        """Test handling of large command files."""
        mock_launch.return_value = ["mock_job"]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            # Create 1000 commands
            for i in range(1, 1001):
                f.write(f"echo 'command {i}'\n")
            temp_file = f.name

        try:
            sys.argv = ["cuecmd", temp_file, "--chunk", "10"]
            result = main.main(sys.argv)

            self.assertEqual(result, 0)
            mock_launch.assert_called_once()

            # Verify frame range (1000 commands / 10 per chunk = 100 frames)
            outline = mock_launch.call_args[0][0]
            layer = outline.get_layers()[0]
            self.assertIn("1-100", layer.get_arg("range"))

        finally:
            os.unlink(temp_file)

    @mock.patch("outline.cuerun.launch")
    def test_uneven_chunking_workflow(self, mock_launch):
        """Test chunking when commands don't divide evenly."""
        mock_launch.return_value = ["mock_job"]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            # 23 commands with chunk size 5 should create 5 frames
            for i in range(1, 24):
                f.write(f"echo 'command {i}'\n")
            temp_file = f.name

        try:
            sys.argv = ["cuecmd", temp_file, "--chunk", "5"]
            result = main.main(sys.argv)

            self.assertEqual(result, 0)

            # Verify frame range (23 commands / 5 per chunk = 5 frames)
            outline = mock_launch.call_args[0][0]
            layer = outline.get_layers()[0]
            self.assertIn("1-5", layer.get_arg("range"))

        finally:
            os.unlink(temp_file)

    @mock.patch("outline.cuerun.launch")
    def test_command_file_with_blank_lines_workflow(self, mock_launch):
        """Test handling of command files with blank lines."""
        mock_launch.return_value = ["mock_job"]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'command 1'\n")
            f.write("\n")
            f.write("   \n")
            f.write("echo 'command 2'\n")
            f.write("\n")
            temp_file = f.name

        try:
            sys.argv = ["cuecmd", temp_file]
            result = main.main(sys.argv)

            self.assertEqual(result, 0)

            # Should only count non-blank lines (2 commands)
            outline = mock_launch.call_args[0][0]
            layer = outline.get_layers()[0]
            self.assertIn("1-2", layer.get_arg("range"))

        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    unittest.main()
