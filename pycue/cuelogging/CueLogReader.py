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

"""Module for reading files"""

import os

class CueLogReader(object):
    """Class to abstract file log reading, this class tries to act as a file object"""

    filepath = None

    def __init__(self, filepath):
        """CueLogWriter class initialization
           @type    filepath: string
           @param   filepath: The filepath to log to
        """
        self.filepath = filepath

    def size(self):
        """Return the size of the file"""
        return int(os.stat(self.filepath).st_size)

    def getMtime(self):
        """Return modification time of the file"""
        return os.path.getmtime(self.filepath)

    def exists(self):
        """Check if the file exists"""
        return os.path.exists(self.filepath)

    def read(self):
        """Read the data from the backend"""

        content = None
        if self.exists() is True:
            with open(self.filepath, "r", encoding='utf-8') as fp:
                content = fp.read()
        else:
            raise IOError("Failed to open %s" % self.filepath)

        return content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
