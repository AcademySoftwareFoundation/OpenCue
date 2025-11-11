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


"""Outline constants and enumerations."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import


# Init mode is during the parsing of the outline
# script.  Nothing can really be done in this phase
# besides adding layers or frames.
OUTLINE_MODE_INIT =  1

# Setup mode is the phase when the outline is being setup
# to launch.  This phase runs in serial on the machine
# that is launching the job.  It creates the job session
# and copies the outline to the cue_archive location.
OUTLINE_MODE_SETUP = 2

# The ready mode is set right after setup is complete.
# This means the outline is now ready to be launched
# to the cue, or for frames to be run locally.
OUTLINE_MODE_READY = 3

# Special frame range constants.
# Default to the first frame in the frame range.
FRAME_RANGE_FIRST = 1

# Default to the last frame in the frame range.
FRAME_RANGE_LAST = 2

# The allowed layer types.
# Render = a general rendering layer
# Util = setup or cleanup layer
# Post = A post job layer
LAYER_TYPES = ("Render", "Util", "Post")
