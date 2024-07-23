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


"""Modules for executing arbitrary shell commands."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import logging
import os

import outline.layer
import outline.util


logger = logging.getLogger("outline.modules.shell")

__all__ = ["Shell",
           "ShellSequence",
           "ShellCommand",
           "ShellScript",
           "shell",
           "PyEval"]


class PyEval(outline.layer.Layer):
    """
    Arbitrary python code execution.
    """
    def __init__(self, name, code, **args):
        super(PyEval, self).__init__(name, **args)

        self.__code = code

    def _setup(self):
        with open(f"{self.get_path()}/script", "w", encoding="utf-8") as fp:
            fp.write(self.__code)

        self.__code = None

    def _execute(self, frames):
        path = self.get_file("script")
        with open(path, encoding="utf-8") as fp:
            code = compile(fp.read(), path, 'exec')
            exec(code)  # pylint: disable=exec-used


class Shell(outline.layer.Layer):
    """
    Provides a method of executing a shell command over an
    arbitrary frame range.
    """
    def __init__(self, name, **args):
        super(Shell, self).__init__(name, **args)

        self.require_arg("command")
        self.set_arg("proxy_enable", False)

    def _execute(self, frames):
        """Execute the shell command."""
        for frame in frames:
            self.system(self.get_arg("command"), frame=frame)


class ShellSequence(outline.layer.Layer):
    """
    A module for executing an array of shell commands.
    """
    def __init__(self, name, **args):
        super(ShellSequence, self).__init__(name, **args)

        self.require_arg("commands")
        self.set_frame_range("1-%d" % len(self.get_arg("commands")))
        self.set_arg("proxy_enable", False)

    def _execute(self, frames):
        for cmd in outline.util.get_slice(self.get_frame_range(), frames, self.get_arg("commands")):
            self.system(cmd)


class ShellCommand(outline.layer.Frame):
    """
    Provides a method of executing a single shell command.  All
    instances of this class will result in a layer with a single
    frame regardless of what frame range the outline is launched
    to the cue with.
    """
    def __init__(self, name, **args):
        super(ShellCommand, self).__init__(name, **args)

        self.require_arg("command")
        self.set_arg("proxy_enable", False)

    def _execute(self, frames):
        """Execute the shell command."""
        self.system(self.get_arg("command"), frame=frames[0])


class ShellScript(outline.layer.Frame):
    """Copies the given script into frame's session folder and executes it as a frame."""
    def __init__(self, name, **args):
        super(ShellScript, self).__init__(name, **args)
        self.require_arg("script")

    def _setup(self):
        s_path = self.put_file(self.get_arg("script"), "script")
        os.chmod(s_path, 0o755)

    def _execute(self, frames):
        self.system(self.get_file("script"), frame=frames[0])


def shell(name, command, **args):
    """A factory method for building instances of Shell."""
    args["command"] = command
    return Shell(name, **args)
