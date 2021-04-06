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


"""Common utility functions."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str

import getpass
import os
import platform

import FileSequence

from .config import config


def disaggregate_frame_set(frameset):
    """Disaggregates a FileSequence.FrameSet into its individual frames
    and removes duplicates.  FrameSet objects can have duplicates if
    the user specifies duplicates, which they tend to do even though
    they don't want duplicates.

    :type    frameset: FileSequence.FrameSet
    :param   frameset: The frameset to disaggregate
    :rtype:            List
    :return:           The list of disaggregated frames.
    """
    # This is not a Set because sets are unordered.

    found = []
    for frame in frameset:
        if frame in found:
            continue
        found.append(frame)
    return found

def intersect_frame_set(range1, range2, normalize=True):
    """
    Return the intersection of two FileSequence.FrameSet objects
    as a FileSequence.FrameSet.  By default, the net frameset is
    normalized and duplicates are removed.  If no intersection
    can be found then None is returned.
    """
    found = []
    for frame in range1:
        if range2.index(frame) > -1 and frame not in found:
            found.append(frame)
    if not found:
        return None
    fs = make_frame_set(found, normalize)
    return fs

def make_frame_set(frames, normalize=True):
    """
    Takes an array of integers and makes a normalized
    FrameSet object.

    :type  frames: List<int>
    :param frames: The frame list to change into a FrameSet

    :rtype: FrameSet
    :return: a normalized FileSequence.FrameSet
    """
    fs = FileSequence.FrameSet(",".join([str(f) for f in frames]))
    if normalize:
        fs.normalize()
    return fs

def get_slice(frame_range, frames, items):
    """
    Given the full frame range, local frame range, and a array items,
    return the slice of the items array.
    """
    frame_set = FileSequence.FrameSet(frame_range)
    return [items[frame_set.index(frame)] for frame in frames]

def get_show():
    """A shortcut for getting the show from the environment.

    Raises an Exception if the shot environment is not found
    alluding to a setshot error.
    """
    return os.environ.get('SHOW', config.get('outline', 'default_show'))


def get_shot():
    """A shortcut for getting the shot from the environment.

    Raises an Exception if the shot environment is not found
    alluding to a setshot error.
    """
    return os.environ.get('SHOT', config.get('outline', 'default_shot'))


def get_user():
    """
    Returns the current username
    """
    if platform.system() == 'Windows':
        domain = os.environ.get('USERDOMAIN', None)
        user = getpass.getuser()
        return '{}\\{}'.format(domain, user) if domain else user

    return os.environ.get('USER', getpass.getuser())


def get_uid():
    """
    Return the current users id
    """
    if platform.system() == 'Windows':
        return 1

    return os.getuid()
