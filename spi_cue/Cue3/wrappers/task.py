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



"""
Project: Cue3 Library

Module: task.py - Cue3 Library implementation of a task

Created: Dec 15, 2008

Contact: Middle-Tier Group 

SVN: $Id
"""

import cue.CueClientIce as CueClientIce

class Task(CueClientIce.Task):
    """This class contains the ice implementation related to a Task."""
    def __init__(self):
        """_Task class initialization"""
        CueClientIce.Task.__init__(self)

    def id(self):
        """Returns the task's unique id"""
        self.proxy.ice_getIdentity().name

    def setMinCores(self, minCores):
        """Sets the minimum amount of cores for the task
        @type  minCores: int
        @param minCores: the minimum number of cores the task needs"""
        self.proxy.setMinCores(minCores)

    def delete():
        """Deletes this task"""
        self.proxy.delete()


