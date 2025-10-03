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


"""Integration tests for cuecmd workflows.

This module tests end-to-end workflows for command execution on the render farm,
verifying that command batching, chunking, and resource allocation work correctly.
"""


from __future__ import absolute_import, division, print_function

import os
import tempfile
import unittest
from unittest import mock

from cuecmd import main


TEST_SHOW = "test_show"
TEST_SHOT = "test_shot"
TEST_USER = "test_user"


class CommandFileProcessingWorkflowTest(unittest.TestCase):
    """Test command file processing workflow.

    This test class verifies that command files are read, parsed,
    and processed correctly for submission.
    """

    def test_single_command_workflow(self):
        """Test processing a file with a single command."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'single command'\n")
            temp_file = f.name

        try:
            count = main.count_commands(temp_file)
            self.assertEqual(count, 1)

            frame_range = main.get_frame_range(count, 1)
            self.assertEqual(frame_range, "1-1")

        finally:
            os.unlink(temp_file)

    def test_multiple_commands_workflow(self):
        """Test processing a file with multiple commands."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            for i in range(1, 11):
                f.write(f"echo 'command {i}'\n")
            temp_file = f.name

        try:
            count = main.count_commands(temp_file)
            self.assertEqual(count, 10)

            frame_range = main.get_frame_range(count, 1)
            self.assertEqual(frame_range, "1-10")

        finally:
            os.unlink(temp_file)

    def test_command_file_with_whitespace(self):
        """Test command file with various whitespace patterns."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("  echo 'command with leading space'\n")
            f.write("echo 'command with trailing space'  \n")
            f.write("\n")
            f.write("   \n")
            f.write("\t\n")
            temp_file = f.name

        try:
            count = main.count_commands(temp_file)
            self.assertEqual(count, 2)

        finally:
            os.unlink(temp_file)

    def test_copy_command_file_workflow(self):
        """Test copying command file to temp location."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            source_file = f.name

        try:
            temp_copy = main.copy_to_temp(source_file)

            # Verify file was copied
            self.assertTrue(os.path.exists(temp_copy))
            self.assertTrue(temp_copy.endswith(".cmds"))

            # Verify content matches
            with open(temp_copy, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, "echo 'test'\n")

            # Clean up
            os.unlink(temp_copy)
            os.rmdir(os.path.dirname(temp_copy))

        finally:
            os.unlink(source_file)


class ChunkingWorkflowTest(unittest.TestCase):
    """Test chunking workflow.

    This test class verifies that commands are chunked correctly
    to create appropriate frame ranges.
    """

    def test_even_chunking(self):
        """Test chunking when commands divide evenly."""
        # 10 commands, chunk size 2 = 5 frames
        frame_range = main.get_frame_range(10, 2)
        self.assertEqual(frame_range, "1-5")

        # 100 commands, chunk size 10 = 10 frames
        frame_range = main.get_frame_range(100, 10)
        self.assertEqual(frame_range, "1-10")

    def test_uneven_chunking(self):
        """Test chunking when commands don't divide evenly."""
        # 11 commands, chunk size 2 = 6 frames (last frame has 1 command)
        frame_range = main.get_frame_range(11, 2)
        self.assertEqual(frame_range, "1-6")

        # 23 commands, chunk size 5 = 5 frames
        frame_range = main.get_frame_range(23, 5)
        self.assertEqual(frame_range, "1-5")

    def test_large_chunk_size(self):
        """Test chunk size larger than command count."""
        # 3 commands, chunk size 10 = 1 frame
        frame_range = main.get_frame_range(3, 10)
        self.assertEqual(frame_range, "1-1")

    def test_chunk_size_one(self):
        """Test chunk size of 1 (one command per frame)."""
        frame_range = main.get_frame_range(5, 1)
        self.assertEqual(frame_range, "1-5")

    def test_large_command_count(self):
        """Test chunking with large command counts."""
        # 10000 commands, chunk size 100 = 100 frames
        frame_range = main.get_frame_range(10000, 100)
        self.assertEqual(frame_range, "1-100")


class OutlineCreationWorkflowTest(unittest.TestCase):
    """Test outline creation workflow.

    This test class verifies that outlines are created correctly
    with proper job metadata and resource specifications.
    """

    def test_basic_outline_creation(self):
        """Test creating a basic outline."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            args = main.parse_arguments(
                ["cuecmd", temp_file, "--show", TEST_SHOW, "--shot", TEST_SHOT]
            )

            outline = main.create_outline(args, temp_file, "1-5")

            self.assertEqual(outline.get_show(), TEST_SHOW)
            self.assertEqual(outline.get_shot(), TEST_SHOT)
            self.assertEqual(len(outline.get_layers()), 1)

        finally:
            os.unlink(temp_file)

    def test_outline_with_custom_job_name(self):
        """Test outline creation with custom job name."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            args = main.parse_arguments(
                ["cuecmd", temp_file, "--job-name", "custom_job_name"]
            )

            outline = main.create_outline(args, temp_file, "1-5")

            self.assertEqual(outline.get_name(), "custom_job_name")

        finally:
            os.unlink(temp_file)

    def test_outline_with_auto_generated_name(self):
        """Test outline creation with auto-generated job name."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt", prefix="my_batch_"
        ) as f:
            temp_file = f.name

        try:
            args = main.parse_arguments(
                [
                    "cuecmd",
                    temp_file,
                    "--show",
                    "myshow",
                    "--shot",
                    "sh010",
                    "--user",
                    "artist",
                ]
            )

            outline = main.create_outline(args, temp_file, "1-5")

            # Name should contain show, shot, user, and file basename
            name = outline.get_name()
            self.assertIn("myshow", name)
            self.assertIn("sh010", name)
            self.assertIn("artist", name)

        finally:
            os.unlink(temp_file)

    def test_outline_resource_specifications(self):
        """Test outline creation with resource specifications."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            args = main.parse_arguments(
                ["cuecmd", temp_file, "--cores", "4", "--memory", "8"]
            )

            outline = main.create_outline(args, temp_file, "1-5")
            layer = outline.get_layers()[0]

            self.assertEqual(layer.get_arg("threads"), 4.0)
            self.assertEqual(layer.get_arg("memory"), "8192MB")

        finally:
            os.unlink(temp_file)

    def test_outline_layer_configuration(self):
        """Test outline layer is configured correctly."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            args = main.parse_arguments(["cuecmd", temp_file, "--chunk", "5"])

            outline = main.create_outline(args, temp_file, "1-10")
            layer = outline.get_layers()[0]

            self.assertEqual(layer.get_name(), "cuecmd")
            self.assertEqual(layer.get_arg("range"), "1-10")
            self.assertEqual(layer.get_arg("chunk"), 1)

        finally:
            os.unlink(temp_file)


class ResourceAllocationWorkflowTest(unittest.TestCase):
    """Test resource allocation workflow.

    This test class verifies that resource specifications are
    applied correctly to jobs.
    """

    def test_default_resources(self):
        """Test default resource allocation."""
        args = main.parse_arguments(["cuecmd", "test.txt"])

        self.assertEqual(args.cores, 1.0)
        self.assertEqual(args.memory, 1.0)

    def test_custom_cores(self):
        """Test custom core allocation."""
        args = main.parse_arguments(["cuecmd", "test.txt", "--cores", "8"])

        self.assertEqual(args.cores, 8.0)

    def test_custom_memory(self):
        """Test custom memory allocation."""
        args = main.parse_arguments(["cuecmd", "test.txt", "--memory", "16"])

        self.assertEqual(args.memory, 16.0)

    def test_fractional_cores(self):
        """Test fractional core allocation."""
        args = main.parse_arguments(["cuecmd", "test.txt", "--cores", "2.5"])

        self.assertEqual(args.cores, 2.5)

    def test_memory_conversion_to_mb(self):
        """Test memory is converted from GB to MB correctly."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            args = main.parse_arguments(["cuecmd", temp_file, "--memory", "4"])

            outline = main.create_outline(args, temp_file, "1-1")
            layer = outline.get_layers()[0]

            # 4GB should be converted to 4096MB
            self.assertEqual(layer.get_arg("memory"), "4096MB")

        finally:
            os.unlink(temp_file)


class JobMetadataWorkflowTest(unittest.TestCase):
    """Test job metadata workflow.

    This test class verifies that job metadata (show, shot, user)
    is handled correctly.
    """

    def test_default_metadata_from_environment(self):
        """Test metadata defaults from environment variables."""
        with mock.patch.dict(
            os.environ, {"SHOW": "env_show", "SHOT": "env_shot", "USER": "env_user"}
        ):
            args = main.parse_arguments(["cuecmd", "test.txt"])

            self.assertEqual(args.show, "env_show")
            self.assertEqual(args.shot, "env_shot")
            self.assertEqual(args.user, "env_user")

    def test_override_metadata_from_args(self):
        """Test metadata can be overridden via command line."""
        with mock.patch.dict(
            os.environ, {"SHOW": "env_show", "SHOT": "env_shot", "USER": "env_user"}
        ):
            args = main.parse_arguments(
                [
                    "cuecmd",
                    "test.txt",
                    "--show",
                    "arg_show",
                    "--shot",
                    "arg_shot",
                    "--user",
                    "arg_user",
                ]
            )

            self.assertEqual(args.show, "arg_show")
            self.assertEqual(args.shot, "arg_shot")
            self.assertEqual(args.user, "arg_user")

    def test_default_metadata_when_no_environment(self):
        """Test metadata defaults when environment variables not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            # Set USER only to avoid issues with getting default user
            os.environ["USER"] = "testuser"
            args = main.parse_arguments(["cuecmd", "test.txt"])

            self.assertEqual(args.show, "default")
            self.assertEqual(args.shot, "default")
            self.assertEqual(args.user, "testuser")


class ErrorHandlingWorkflowTest(unittest.TestCase):
    """Test error handling workflow.

    This test class verifies that errors are handled gracefully
    and provide useful feedback.
    """

    def test_nonexistent_file_error(self):
        """Test error when command file doesn't exist."""
        with self.assertRaises(SystemExit):
            main.main(["cuecmd", "/nonexistent/path/to/file.txt"])

    def test_empty_file_error(self):
        """Test error when command file is empty."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            with self.assertRaises(SystemExit):
                main.main(["cuecmd", temp_file])

        finally:
            os.unlink(temp_file)

    def test_invalid_chunk_size(self):
        """Test error handling for invalid chunk size."""
        with self.assertRaises(SystemExit):
            main.parse_arguments(["cuecmd", "test.txt", "--chunk", "invalid"])

    def test_invalid_cores_value(self):
        """Test error handling for invalid cores value."""
        with self.assertRaises(SystemExit):
            main.parse_arguments(["cuecmd", "test.txt", "--cores", "invalid"])

    def test_invalid_memory_value(self):
        """Test error handling for invalid memory value."""
        with self.assertRaises(SystemExit):
            main.parse_arguments(["cuecmd", "test.txt", "--memory", "invalid"])


class PretendModeWorkflowTest(unittest.TestCase):
    """Test pretend mode workflow.

    This test class verifies that pretend mode displays information
    without actually submitting jobs.
    """

    @mock.patch("outline.cuerun.launch")
    def test_pretend_mode_no_submission(self, mock_launch):
        """Test pretend mode doesn't submit jobs."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            result = main.main(["cuecmd", temp_file, "--pretend"])

            self.assertEqual(result, 0)
            mock_launch.assert_not_called()

        finally:
            os.unlink(temp_file)

    def test_pretend_mode_validates_inputs(self):
        """Test pretend mode still validates inputs."""
        # Nonexistent file should still error in pretend mode
        with self.assertRaises(SystemExit):
            main.main(["cuecmd", "/nonexistent/file.txt", "--pretend"])


class PauseModeWorkflowTest(unittest.TestCase):
    """Test pause mode workflow.

    This test class verifies that jobs can be submitted in paused state.
    """

    @mock.patch("outline.cuerun.launch")
    def test_pause_mode_submission(self, mock_launch):
        """Test submitting job in paused state."""
        mock_launch.return_value = ["mock_job"]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            result = main.main(["cuecmd", temp_file, "--pause"])

            self.assertEqual(result, 0)
            mock_launch.assert_called_once()

            # Verify pause parameter was passed
            call_kwargs = mock_launch.call_args[1]
            self.assertTrue(call_kwargs.get("pause"))

        finally:
            os.unlink(temp_file)


class CommandExecutionWorkflowTest(unittest.TestCase):
    """Test command execution workflow.

    This test class verifies that the execute_commands helper
    script is configured correctly.
    """

    def test_execute_script_path(self):
        """Test execute_commands.py script path is correct."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            args = main.parse_arguments(["cuecmd", temp_file])
            outline = main.create_outline(args, temp_file, "1-5")
            layer = outline.get_layers()[0]

            command = layer.get_arg("command")

            # Command should reference execute_commands.py
            self.assertIn("execute_commands.py", command)
            self.assertIn("python3", command)

        finally:
            os.unlink(temp_file)

    def test_execute_script_arguments(self):
        """Test execute_commands.py receives correct arguments."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            args = main.parse_arguments(["cuecmd", temp_file, "--chunk", "5"])
            temp_copy = main.copy_to_temp(temp_file)
            outline = main.create_outline(args, temp_copy, "1-10")
            layer = outline.get_layers()[0]

            command = layer.get_arg("command")

            # Command should include chunk size and frame placeholder
            self.assertIn("5", command)
            self.assertIn("#IFRAME#", command)

            # Clean up
            os.unlink(temp_copy)
            os.rmdir(os.path.dirname(temp_copy))

        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    unittest.main()
