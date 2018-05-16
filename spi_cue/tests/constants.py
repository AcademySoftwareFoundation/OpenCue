#!/usr/local/bin/python

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




import os
import re
import time
import unittest
import commands

from Manifest import Cue3

USERNAME = os.getenv("USER")
ID_LENGTH = 36
UNITTEST_ALLOCATION = "unittest"
TEST_SUBSCRIPTION = "pipe.Playblast"

CHECK_FOR_ID = re.compile("[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", re.IGNORECASE)

class Job:
    """Base assumptions about resulting data"""
    layerCount = 3
    isBookable = False
    percentCompleted = 0.0
    pendingFrames = 150

    state = Cue3.JobState.Pending
    name = "pipe-dev.cue-%s_jobtest" % USERNAME
    shot = "dev.cue"
    show = "pipe"
    # uid > 0
    user = USERNAME
    group = "pipe"
    #minProcs > 0
    #maxProcs > 0
    logDir = "/shots/pipe/dev.cue/logs/pipe-dev.cue-%s_jobtest" % USERNAME
    isPaused = True
    hasComment = False
    autoEat = False
    #startTime > 0
    stopTime = 0
    totalFrames = 150
    waitingFrames = 150
    runningFrames = 0
    deadFrames = 0
    eatenFrames = 0
    dependFrames = 0
    succeededFrames = 0
    runningProcs = 0
    bookedProcs = 0
    reservedCores = 0
    avgFrameTimeSeconds = 0
    procSecondsSucceeded = 0
    procSecondsFailed = 0
    reservedMemoryKb = 0
    usedMemoryKb = 0

job = Cue3

