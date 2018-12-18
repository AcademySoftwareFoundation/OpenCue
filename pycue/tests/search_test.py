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


from Manifest import os, unittest, Cue3


TEST_SHOW_NAME = "pipe"
TEST_GROUP_NAME = "pipe"
TEST_GROUP_ID = "A0000000-0000-0000-0000-000000000000"
TEST_JOB_NAME = "pipe-dev.cue-chambers_shell_v6"
TEST_LAYER_NAME = "depend_er"
TEST_HOST_NAME = "genosis"


class JobSearchTests(unittest.TestCase):

    def testByOptions(self):
        job1 = Cue3.search.JobSearch.byOptions(show=["pipe"], match=["v6"]).jobs.jobs[0]
        job2 = Cue3.search.JobSearch.byOptions(ids=[job1.id]).jobs.jobs[0]
        self.assertTrue(job1.name, job2.name)


if __name__ == '__main__':
    unittest.main()
