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

import os
import subprocess

import nuke

"""CueNukeSubmitLauncher.py
Nuke uses an older version of gRPC for the Frame Server.
This requires us to run the OpenCue submission plugin from a Python session outside of Nuke.
While not ideal, this script allows us to gather up Nuke info and feed it to the submission GUI.
"""

NUKE_SUBMIT_UI_PY = 'CueNukeSubmit.py'
PYTHON_BIN = os.environ.get('CUE_PYTHON_BIN', 'python')

def getAllWrites():
    """Return all the write nodes in the Nuke file. Recursively descend into groups."""
    root = nuke.toNode("root")
    writes = _getAllWritesRec(group=root, writes=[])
    if not writes:
        raise CueNukeFileException('Your Nuke file contains no Write nodes! Cannot launch a render job.')
    return writes

def _getAllWritesRec(group, writes):
    """Recursively look for Write nodes within Groups"""
    writes.extend(nuke.allNodes(filter="Write", group=group))
    for group in nuke.allNodes(filter="Group", group=group):
        writes = _getAllWritesRec(group=group, writes=writes)
    return writes


def getFilename():
    """Return the current Nuke filename."""
    filename = nuke.root().name()
    if filename == 'Root':
        raise CueNukeFileException('File is not saved! Please save the file before submitting.')
    return filename


def launchSubmitter():
    """Gather Nuke data and shell out to a new session to launch the submission ui"""
    filename = getFilename()
    writeNodes = getAllWrites()
    submitScript = os.path.join(os.path.dirname(__file__), NUKE_SUBMIT_UI_PY)
    writeNodeNames = ' '.join([node.fullName() for node in writeNodes])
    cmd = '{} {} --file {} --nodes {}'.format(PYTHON_BIN, submitScript, filename, writeNodeNames)
    result = subprocess.Popen(cmd.split(), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = result.communicate()
    if result.returncode != 0:
        nuke.message('Failed to submit job!\n{}\n\n{}'.format(out, err))


class CueNukeFileException(Exception):
    pass
