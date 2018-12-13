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


"""Utility functions for Cue3Tools"""
import logging
import sys
import time

from Manifest import Cue3

__ALL__ = ["enableDebugLogging",
           "promptYesNo",
           "waitOnJobName"]


def enableDebugLogging():
    """enables debug logging for cue3 and cue3 tools"""
    logger = logging.getLogger("cue3")
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logger.addHandler(console)
    logger.setLevel(logging.DEBUG)


def promptYesNo(prompt, force=False):
    """Asks the user the supplied question and returns with a boolean to
    indicate the users input.
    @type  prompt: string
    @param prompt: The question that the user can see
    @type  force: boolean
    @param force: (Optional) If true, skips the prompt and returns true
    @rtype:  bool
    @return: The users response"""
    try:
        result = force or raw_input("%s [y/n] " % prompt) in ("y", "Y")
    except KeyboardInterrupt:
        raise
    if not result:
        print "Canceled"
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
            isPending = Cue3.api.isJobPending(jobName.lower())
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
        except Cue3.CueException, e:
            print >>sys.stderr, "Error: %s" % e
        except Exception, e:
            print >>sys.stderr, "Error: %s" % e

        time.sleep(delay)
