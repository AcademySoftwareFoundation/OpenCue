#!/usr/bin/env python3

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

"""Unit tests for cuecmd main module."""

import os
import tempfile
import unittest
from unittest import mock

from cuecmd import main


class TestParseArguments(unittest.TestCase):
    """Test argument parsing."""

    def test_basic_arguments(self):
        """Test basic command-line argument parsing."""
        args = main.parse_arguments(["cuecmd", "test.txt"])
        self.assertEqual(args.command_file, "test.txt")
        self.assertEqual(args.chunk, 1)
        self.assertEqual(args.cores, 1.0)
        self.assertEqual(args.memory, 1.0)
        self.assertFalse(args.pause)
        self.assertFalse(args.pretend)

    def test_chunk_argument(self):
        """Test chunk size argument."""
        args = main.parse_arguments(["cuecmd", "test.txt", "--chunk", "5"])
        self.assertEqual(args.chunk, 5)

        args = main.parse_arguments(["cuecmd", "test.txt", "-c", "10"])
        self.assertEqual(args.chunk, 10)

    def test_cores_argument(self):
        """Test cores argument."""
        args = main.parse_arguments(["cuecmd", "test.txt", "--cores", "2.5"])
        self.assertEqual(args.cores, 2.5)

    def test_memory_argument(self):
        """Test memory argument."""
        args = main.parse_arguments(["cuecmd", "test.txt", "--memory", "4.0"])
        self.assertEqual(args.memory, 4.0)

    def test_pause_argument(self):
        """Test pause argument."""
        args = main.parse_arguments(["cuecmd", "test.txt", "--pause"])
        self.assertTrue(args.pause)

        args = main.parse_arguments(["cuecmd", "test.txt", "-p"])
        self.assertTrue(args.pause)

    def test_pretend_argument(self):
        """Test pretend argument."""
        args = main.parse_arguments(["cuecmd", "test.txt", "--pretend"])
        self.assertTrue(args.pretend)

    def test_shot_show_user_arguments(self):
        """Test shot, show, and user arguments."""
        args = main.parse_arguments(
            [
                "cuecmd",
                "test.txt",
                "--shot",
                "sh010",
                "--show",
                "myshow",
                "--user",
                "testuser",
            ]
        )
        self.assertEqual(args.shot, "sh010")
        self.assertEqual(args.show, "myshow")
        self.assertEqual(args.user, "testuser")

    def test_job_name_argument(self):
        """Test custom job name argument."""
        args = main.parse_arguments(
            ["cuecmd", "test.txt", "--job-name", "my_custom_job"]
        )
        self.assertEqual(args.job_name, "my_custom_job")


class TestCountCommands(unittest.TestCase):
    """Test command counting."""

    def test_count_commands(self):
        """Test counting commands in a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'command 1'\n")
            f.write("echo 'command 2'\n")
            f.write("echo 'command 3'\n")
            f.write("\n")  # Empty line
            f.write("echo 'command 4'\n")
            temp_file = f.name

        try:
            count = main.count_commands(temp_file)
            self.assertEqual(count, 4)
        finally:
            os.unlink(temp_file)

    def test_count_commands_empty_file(self):
        """Test counting commands in an empty file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            count = main.count_commands(temp_file)
            self.assertEqual(count, 0)
        finally:
            os.unlink(temp_file)


class TestGetFrameRange(unittest.TestCase):
    """Test frame range calculation."""

    def test_exact_division(self):
        """Test frame range when commands divide evenly."""
        frame_range = main.get_frame_range(10, 2)
        self.assertEqual(frame_range, "1-5")

    def test_uneven_division(self):
        """Test frame range when commands don't divide evenly."""
        frame_range = main.get_frame_range(11, 2)
        self.assertEqual(frame_range, "1-6")

    def test_single_chunk(self):
        """Test frame range with chunk size of 1."""
        frame_range = main.get_frame_range(5, 1)
        self.assertEqual(frame_range, "1-5")

    def test_large_chunk(self):
        """Test frame range with chunk larger than command count."""
        frame_range = main.get_frame_range(3, 10)
        self.assertEqual(frame_range, "1-1")


class TestCopyToTemp(unittest.TestCase):
    """Test copying command file to temp."""

    def test_copy_to_temp(self):
        """Test copying a file to temp location."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            source_file = f.name

        try:
            temp_file = main.copy_to_temp(source_file)
            self.assertTrue(os.path.exists(temp_file))
            self.assertTrue(temp_file.endswith(".cmds"))

            # Verify content was copied
            with open(temp_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, "echo 'test'\n")

            # Clean up temp file
            os.unlink(temp_file)
            os.rmdir(os.path.dirname(temp_file))
        finally:
            os.unlink(source_file)


class TestCreateOutline(unittest.TestCase):
    """Test outline creation."""

    def test_create_outline_basic(self):
        """Test creating a basic outline."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            args = main.parse_arguments(
                [
                    "cuecmd",
                    temp_file,
                    "--shot",
                    "sh010",
                    "--show",
                    "testshow",
                    "--user",
                    "testuser",
                ]
            )

            ol = main.create_outline(args, temp_file, "1-5")

            self.assertEqual(ol.get_shot(), "sh010")
            self.assertEqual(ol.get_show(), "testshow")
            self.assertEqual(ol.get_user(), "testuser")
            self.assertIn("testshow_sh010_testuser", ol.get_name())

        finally:
            os.unlink(temp_file)

    def test_create_outline_custom_job_name(self):
        """Test creating outline with custom job name."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            args = main.parse_arguments(
                ["cuecmd", temp_file, "--job-name", "my_custom_job"]
            )

            ol = main.create_outline(args, temp_file, "1-5")
            self.assertEqual(ol.get_name(), "my_custom_job")

        finally:
            os.unlink(temp_file)


class TestMainFunction(unittest.TestCase):
    """Test main function."""

    def test_main_file_not_found(self):
        """Test main with non-existent file."""
        with self.assertRaises(SystemExit) as cm:
            main.main(["cuecmd", "nonexistent.txt"])
        self.assertEqual(cm.exception.code, 1)

    def test_main_empty_file(self):
        """Test main with empty command file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            with self.assertRaises(SystemExit) as cm:
                main.main(["cuecmd", temp_file])
            self.assertEqual(cm.exception.code, 1)
        finally:
            os.unlink(temp_file)

    @mock.patch("outline.cuerun.launch")
    def test_main_pretend_mode(self, mock_launch):
        """Test main in pretend mode."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            result = main.main(["cuecmd", temp_file, "--pretend"])
            self.assertEqual(result, 0)
            # launch should not be called in pretend mode
            mock_launch.assert_not_called()
        finally:
            os.unlink(temp_file)

    @mock.patch("outline.cuerun.launch")
    def test_main_launch_success(self, mock_launch):
        """Test successful job launch."""
        mock_launch.return_value = ["mock_job"]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            result = main.main(["cuecmd", temp_file])
            self.assertEqual(result, 0)
            mock_launch.assert_called_once()
        finally:
            os.unlink(temp_file)

    @mock.patch("outline.cuerun.launch")
    def test_main_launch_failure(self, mock_launch):
        """Test failed job launch."""
        mock_launch.return_value = None

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'test'\n")
            temp_file = f.name

        try:
            with self.assertRaises(SystemExit) as cm:
                main.main(["cuecmd", temp_file])
            self.assertEqual(cm.exception.code, 1)
        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    unittest.main()
