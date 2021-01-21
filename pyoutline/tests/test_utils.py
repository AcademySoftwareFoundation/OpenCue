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
Common classes and functions used throughout the outline module test code.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import object
import shutil
import tempfile

import outline


class TemporarySessionDirectory(object):
    def __init__(self):
        self.originalSessionDir = None
        self.tempSessionDir = None

    def __enter__(self):
        self.originalSessionDir = outline.config.get('outline', 'session_dir')
        self.tempSessionDir = tempfile.mkdtemp()
        outline.config.set('outline', 'session_dir', self.tempSessionDir)
        return self.tempSessionDir

    def __exit__(self, *args):
        outline.config.set('outline', 'session_dir', self.originalSessionDir)
        shutil.rmtree(self.tempSessionDir)
