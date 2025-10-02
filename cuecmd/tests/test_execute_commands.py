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

"""Unit tests for execute_commands module."""

import os
import subprocess
import tempfile
import unittest


class TestExecuteCommands(unittest.TestCase):
    """Test execute_commands module."""

    def test_basic_execution(self):
        """Test basic command execution."""
        # Create a temp file with commands
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'command 1'\n")
            f.write("echo 'command 2'\n")
            f.write("echo 'command 3'\n")
            temp_file = f.name

        try:
            # Execute frame 1 with chunk size 1 (should execute command 1)
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "cuecmd.execute_commands",
                    temp_file,
                    "1",
                    "--frame",
                    "1",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("command 1", result.stdout)
            self.assertEqual(result.returncode, 0)

        finally:
            os.unlink(temp_file)

    def test_chunked_execution(self):
        """Test executing multiple commands per frame."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'cmd1'\n")
            f.write("echo 'cmd2'\n")
            f.write("echo 'cmd3'\n")
            f.write("echo 'cmd4'\n")
            temp_file = f.name

        try:
            # Execute frame 1 with chunk size 2 (should execute commands 1-2)
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "cuecmd.execute_commands",
                    temp_file,
                    "2",
                    "--frame",
                    "1",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("cmd1", result.stdout)
            self.assertIn("cmd2", result.stdout)
            self.assertEqual(result.returncode, 0)

            # Execute frame 2 with chunk size 2 (should execute commands 3-4)
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "cuecmd.execute_commands",
                    temp_file,
                    "2",
                    "--frame",
                    "2",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("cmd3", result.stdout)
            self.assertIn("cmd4", result.stdout)
            self.assertEqual(result.returncode, 0)

        finally:
            os.unlink(temp_file)

    def test_frame_beyond_range(self):
        """Test executing a frame beyond available commands."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("echo 'cmd1'\n")
            temp_file = f.name

        try:
            # Execute frame 5 when only 1 command exists
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "cuecmd.execute_commands",
                    temp_file,
                    "1",
                    "--frame",
                    "5",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("beyond", result.stdout.lower())
            self.assertEqual(result.returncode, 0)

        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    unittest.main()
