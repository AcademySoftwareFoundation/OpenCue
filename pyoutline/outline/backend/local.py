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

"""
Local backend module.

Runs the given job on the local machine, using a SQLite database to store state.

See outline.backend.__init__.py for a description of the PyOutline backend system.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import object
import subprocess

import sqlite3

import FileSequence

import outline
import outline.versions


def build_command(ol, layer, frame):
    """
    Build and return a pycurun shell command for the given layer frame.

    :type  layer : Layer
    :param layer : The layer to build a command for.

    :rtype: string
    :return: The shell command to run for a the given layer.
    """
    command = []
    command.append("%s/local_wrap_frame" % outline.config.get("outline","wrapper_dir"))
    command.append(outline.config.get("outline", "user_dir"))
    command.append(ol.get_show())
    command.append(ol.get_shot())
    command.append("%s/pycuerun" % outline.config.get("outline", "bin_dir"))
    command.append("%s -e  %d-%s" % (ol.get_path(),  frame, layer.get_name()))
    command.append(" -v %s" % outline.versions.get_version("outline"))
    command.append(" -r %s" % outline.versions.get_repos())
    command.append("-D")

    return command


def launch(launcher, use_pycuerun=None):
    """
    Start the local dispatcher.
    """
    # pycuerun is not used in this backend, but we keep it as a parameter for compatibility
    # with other backends.
    del use_pycuerun

    dispatcher = serialize(launcher)
    dispatcher.dispatch()


def serialize(launcher):
    """
    Create a local dispatcher object.
    """
    return Dispatcher(launcher.get_outline())


def serialize_simple(launcher):
    """
    For local we can call the regular serialize function.
    """
    return serialize(launcher)


def build_frame_range(frame_range, chunk_size):
    """
    Return an array of frames with no duplicates and chunking applied.
    """
    frame_set = FileSequence.FrameSet(frame_range)
    frames = []
    if chunk_size > 1:
        if chunk_size >= len(frame_set):
            frames.append(frame_set[0])
        else:
            unique_frames = list(set(frame_set))
            for i, unique_frame in enumerate(unique_frames):
                if i % chunk_size == 0:
                    frames.append(unique_frame)
    else:
        frames = list(FileSequence.FrameSet(frame_range))
    return frames


class LocalFrameError(Exception):
    """
    Raised when a locally run frame has failed.
    """


class Dispatcher(object):
    """
    Local version of a job dispatcher, responsible for launching each frame, monitoring the
    result, and updating the local state.
    """

    def __init__(self, ol):
        self.__ol = ol

        self.__conn = sqlite3.connect(":memory:")
        self.__create_dispatch_list()

    def dispatch(self):
        """
        Run the frames of the job in sequence and record the result.
        """
        try:
            while True:
                l, f = self.__get_next_frame()
                if l is None and f is None:
                    break

                layer = self.__ol.get_layer(l)

                command = build_command(self.__ol, layer, f)
                try:
                    retcode = subprocess.call(command, shell=False)
                    if retcode != 0:
                        raise LocalFrameError("frame failed")
                except LocalFrameError:
                    # Failed to run frame
                    # Set frame to dead
                    c = self.__conn.cursor()
                    c.execute("UPDATE frames SET state=? WHERE layer=? AND frame=?",
                              ('DEAD', l, f))
                    self.__conn.commit()
        finally:
            print("Job is done")
            self.__conn.close()

    def __create_dispatch_list(self):
        """
        Creates a list of dispatchable frames.
        """
        c = self.__conn.cursor()
        c.execute(
            'create table frames '
            '(layer text, frame int, state string, layer_order int, frame_order int)')

        for layer in self.__ol.get_layers():

            frames = build_frame_range(layer.get_frame_range(),
                                       layer.get_chunk_size())
            for frame in frames:
                c.execute(
                    'insert into frames values (?,?,?,?,?)',
                    (layer.get_name(), frame, 'WAITING', self.__ol.get_layers().index(layer),
                     int(frame)))
        self.__conn.commit()

    def __get_next_frame(self):
        c = self.__conn.cursor()
        c.execute(
            "SELECT layer, frame, state FROM frames WHERE state='WAITING' "
            "ORDER BY frame_order,layer_order LIMIT 1")
        result = c.fetchone()

        if result:
            c.execute("UPDATE frames SET state=? WHERE layer=? AND frame=?",
                      ('RUNNING', result[0], result[1]))
            self.__conn.commit()
            return result[0], result[1]

        return None, None
