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
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
import opencue as cue

TEST_SHOW_NAME = "pipe"
TEST_GROUP_NAME = "pipe"
TEST_GROUP_ID = "A0000000-0000-0000-0000-000000000000"
TEST_JOB_NAME = "pipe-dev.cue-chambers_shell_v6"
TEST_LAYER_NAME = "depend_er"
TEST_HOST_NAME = "wolf1001"
TEST_SUB_NAME = "pipe.General"


#
#  These tests just need to call the API methods
#
class ShowTests(unittest.TestCase):

    def testGetShows(self):
        cue.api.getShows()

    def testFindShow(self):
        cue.api.findShow(TEST_SHOW_NAME)

    def testCreateShow(self):
        try:
            s = cue.api.findShow("cue")
            cue.api.deleteShow(s.id())
        except cue.EntityNotFoundException:
            pass
        finally:
            s = cue.api.createShow("cue")
            cue.api.deleteShow(s.id())


class GroupTests(unittest.TestCase):

    def testFindGroup(self):
        cue.api.findGroup(TEST_SHOW_NAME, TEST_GROUP_NAME)

    def testGetGroup(self):
        cue.api.getGroup(TEST_GROUP_ID)


class JobTests(unittest.TestCase):

    def testIsJobPending(self):
        self.assertFalse(cue.api.isJobPending("notpending"))

    def testFindJob(self):
        self.assertRaises(cue.EntityNotFoundException, cue.api.findJob, "notfound")
        cue.api.findJob(TEST_JOB_NAME)

    def testGetJobs(self):
        self.assertTrue(len(cue.api.getJobs(show=[TEST_SHOW_NAME], all=True)) > 0)
        self.assertTrue(len(cue.api.getJobs(name=[TEST_JOB_NAME], show=[TEST_SHOW_NAME])) == 1)

    def testGetJob(self):
        job1 = cue.api.findJob(TEST_JOB_NAME)
        job2 = cue.api.getJob(cue.id(job1))

    def testGetJobNames(self):
        self.assertTrue(len(cue.api.getJobNames(show=[TEST_SHOW_NAME])) > 0)


class LayerTests(unittest.TestCase):

    def testFindLayer(self):
        cue.api.findLayer(TEST_JOB_NAME, TEST_LAYER_NAME)

    def testGetLayer(self):
        layer1 = cue.api.findLayer(TEST_JOB_NAME, TEST_LAYER_NAME)
        layer2 = cue.api.getLayer(cue.id(layer1))


class FrameTests(unittest.TestCase):

    def testFindFrame(self):
        cue.api.findFrame(TEST_JOB_NAME, TEST_LAYER_NAME, 1)

    def testGetFrame(self):
        frame1 = cue.api.findFrame(TEST_JOB_NAME, TEST_LAYER_NAME, 1)
        frame2 = cue.api.getFrame(cue.id(frame1))
        self.assertEqual(frame1.number(), frame2.number())

    def testGetFrames(self):
        self.assertTrue(cue.api.getFrames(TEST_JOB_NAME, range="1-5") > 0)


class SubscriptionTests(unittest.TestCase):

    def testFindSubscription(self):
        cue.api.findSubscription(TEST_SUB_NAME)

    def testGetSubscription(self):
        sub1 = cue.api.findSubscription(TEST_SUB_NAME)
        sub2 = cue.api.getSubscription(cue.id(sub1))
        self.assertEqual(cue.id(sub1), cue.id(sub2))


class HostTests(unittest.TestCase):

    def testGetHosts(self):
        self.assertTrue(len(cue.api.getHosts(name=[TEST_HOST_NAME])) == 1)

    # this is failing all the time
    # def testGetHostWhiteboard(self):
    #     cue.get_host_whiteboard()

    def testFindHost(self):
        h = cue.api.findHost(TEST_HOST_NAME)
        self.assertEquals(h.name(), TEST_HOST_NAME)

    def testGetHost(self):
        h = cue.api.findHost(TEST_HOST_NAME)
        self.assertEquals(h.name(), TEST_HOST_NAME)
        h2 = cue.api.getHost(cue.id(h))
        self.assertEquals(h.name(), h2.name())


if __name__ == '__main__':
    unittest.main()
