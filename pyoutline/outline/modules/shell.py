#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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

from past.builtins import execfile
import logging
import os

from outline import util
from outline.layer import Layer, Frame


logger = logging.getLogger("outline.modules.shell")

__all__ = ["Shell",
           "ShellSequence",
           "ShellCommand",
           "ShellScript",
           "shell",
           "PyEval"]


class PyEval(Layer):
    """
    Arbitrary python code execution.
    """
    def __init__(self, name, code, **args):
        Layer.__init__(self, name, **args)
        self.__code = code

    def _setup(self):
        fp = open("%s/script" % self.get_path(), "w")
        try:
            fp.write(self.__code)
        finally:
            fp.close()
        self.__code = None

    def _execute(self, frames):
        execfile(self.get_file("script"))


class Shell(Layer):
    """
    Provides a method of executing a shell command over an
    arbitrary frame range.
    """
    def __init__(self, name, **args):
        Layer.__init__(self, name, **args)

        ## require the cmd argument
        self.require_arg("command")
        self.set_arg("proxy_enable", False)

    def _execute(self, frame_set):
        """Execute the shell command."""
        for frame in frame_set:
            self.system(self.get_arg("command"), frame=frame)


class ShellSequence(Layer):
    """
    A module for executing an array of shell commands.
    """
    def __init__(self, name, **args):
        Layer.__init__(self, name, **args)
        self.require_arg("commands")
        self.set_frame_range("1-%d" % len(self.get_arg("commands")))
        self.set_arg("proxy_enable", False)

    def _execute(self, frames):
        for cmd in util.get_slice(self.get_frame_range(),
                                  frames, self.get_arg("commands")):
            self.system(cmd)


class ShellCommand(Frame):
    """
    Provides a method of executing a single shell command.  All
    instances of this class will result in a layer with a single
    frame regaurdless of what frame range the outline is launched
    to the cue with.
    """
    def __init__(self, name, **args):
        Frame.__init__(self, name, **args)

        ## require the cmd argument
        self.require_arg("command")
        self.set_arg("proxy_enable", False)

    def _execute(self, frame_set):
        """Execute the shell command."""
        self.system(self.get_arg("command"), frame=frame_set[0])

class ShellScript(Frame):
    """
    Copies the given script into frame's session 
    folder and executes it as a frame. 
    """
    def __init__(self, name, **args):
        Frame.__init__(self, name, **args)
        self.require_arg("script")

    def _setup(self):
        s_path = self.put_file(self.get_arg("script"), "script")
        os.chmod(s_path, 0o755)        

    def _execute(self, frames):
        self.system(self.get_file("script"), frame=frames[0])

def shell(name, command, **args):
    """
    A factory method for building instances of Shell.
    """
    args["command"] = command
    return Shell(name, **args)


