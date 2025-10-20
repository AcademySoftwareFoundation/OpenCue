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


"""Entrypoint for CueAdmin tool."""


from __future__ import absolute_import, division, print_function

import logging

import cueadmin.common

logger = logging.getLogger("opencue.tools.cueadmin")


# pylint: disable=broad-except
def main():
    """Starts the CueAdmin tool."""

    parser = cueadmin.common.getParser()
    args = parser.parse_args()

    try:
        cueadmin.common.handleArgs(args)
    except Exception as e:
        cueadmin.common.handleParserException(args, e)


if __name__ == "__main__":
    main()
