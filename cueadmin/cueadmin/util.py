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


"""Utility functions for CueAdmin"""


from __future__ import absolute_import, division, print_function

import logging
import sys
import time
from builtins import input

import opencue

__ALL__ = ["enableDebugLogging", "promptYesNo", "waitOnJobName"]


def enableDebugLogging():
    """Enables debug logging for opencue and opencue tools."""
    logger = logging.getLogger("opencue")
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logger.addHandler(console)
    logger.setLevel(logging.DEBUG)


def promptYesNo(prompt, force=False):
    """Asks the user to confirm or deny the prompted question.

    @type  prompt: string
    @param prompt: The question that the user can see
    @type  force: boolean
    @param force: (Optional) If true, skips the prompt and returns true
    @rtype:  bool
    @return: The user's response"""
    result = force or input("%s [y/n] " % prompt) in ("y", "Y")
    if not result:
        print("Canceled")
    return result


def waitOnJobName(jobName, maxWaitForLaunch=None):
    """Waits on the given job name to enter and then leave the queue.

    @type  jobName: str
    @param jobName: Full name of the job
    @type  maxWaitForLaunch: int
    @param maxWaitForLaunch: (Optional) The maximum number of seconds to wait
                             for the job to launch.
    @rtype:  bool
    @return: Returns True if the job was found and is now Finished, False if
             the job was not found before maxWaitForLaunch was reached"""
    isLocated = False
    isPending = False
    delay = 10
    waited = 0
    time.sleep(4)
    while True:
        try:
            isPending = opencue.api.isJobPending(jobName.lower())
            isLocated = isLocated or isPending

            if isLocated:
                if isPending:
                    delay = 15
                else:
                    return True
            else:
                waited += delay
                if maxWaitForLaunch and waited >= maxWaitForLaunch:
                    return False
        except opencue.CueException as e:
            print("Error: %s" % e, file=sys.stderr)

        time.sleep(delay)
