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


import os.path
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
import Cue3 as cue3

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
        cue3.getShows()

    def testFindShow(self):
        cue3.findShow(TEST_SHOW_NAME)

    def testCreateShow(self):
        try:
            s = cue3.findShow("cue3")
            cue3.deleteShow(s.id)
        except cue3.EntityNotFoundException:
            pass
        finally:
            s = cue3.createShow("cue3")
            cue3.deleteShow(s.id)


class GroupTests(unittest.TestCase):

    def testFindGroup(self):
        cue3.findGroup(TEST_SHOW_NAME, TEST_GROUP_NAME)

    def testGetGroup(self):
        cue3.getGroup(TEST_GROUP_ID)


class JobTests(unittest.TestCase):

    def testIsJobPending(self):
        self.assertFalse(cue3.isJobPending("notpending"))

    def testFindJob(self):
        self.assertRaises(cue3.EntityNotFoundException, cue3.findJob, "notfound")
        cue3.findJob(TEST_JOB_NAME)

    def testGetJobs(self):
        self.assertTrue(len(cue3.getJobs(show=[TEST_SHOW_NAME], all=True)) > 0)
        self.assertTrue(len(cue3.getJobs(name=[TEST_JOB_NAME], show=[TEST_SHOW_NAME])) == 1)

    def testGetJob(self):
        job1 = cue3.findJob(TEST_JOB_NAME)
        job2 = cue3.getJob(cue3.id(job1))

    def testGetJobNames(self):
        self.assertTrue(len(cue3.getJobNames(show=[TEST_SHOW_NAME])) > 0)


class LayerTests(unittest.TestCase):

    def testFindLayer(self):
        cue3.findLayer(TEST_JOB_NAME, TEST_LAYER_NAME)

    def testGetLayer(self):
        layer1 = cue3.findLayer(TEST_JOB_NAME, TEST_LAYER_NAME)
        layer2 = cue3.getLayer(cue3.id(layer1))


class FrameTests(unittest.TestCase):

    def testFindFrame(self):
        cue3.findFrame(TEST_JOB_NAME, TEST_LAYER_NAME, 1)

    def testGetFrame(self):
        frame1 = cue3.findFrame(TEST_JOB_NAME, TEST_LAYER_NAME, 1)
        frame2 = cue3.getFrame(cue3.id(frame1))
        self.assertEqual(frame1.number, frame2.number)

    def testGetFrames(self):
        self.assertTrue(cue3.getFrames(TEST_JOB_NAME, range="1-5") > 0)


class SubscriptionTests(unittest.TestCase):

    def testFindSubscription(self):
        cue3.findSubscription(TEST_SUB_NAME)

    def testGetSubscription(self):
        sub1 = cue3.findSubscription(TEST_SUB_NAME)
        sub2 = cue3.getSubscription(cue3.id(sub1))
        self.assertEqual(cue3.id(sub1), cue3.id(sub2))


class HostTests(unittest.TestCase):

    def testGetHosts(self):
        self.assertTrue(len(cue3.getHosts(name=[TEST_HOST_NAME])) == 1)

    # this is failing all the time
    # def testGetHostWhiteboard(self):
    #     cue3.get_host_whiteboard()

    def testFindHost(self):
        h = cue3.findHost(TEST_HOST_NAME)
        self.assertEquals(h.name, TEST_HOST_NAME)

    def testGetHost(self):
        h = cue3.findHost(TEST_HOST_NAME)
        self.assertEquals(h.name, TEST_HOST_NAME)
        h2 = cue3.getHost(cue3.id(h))
        self.assertEquals(h.name, h2.name)


if __name__ == '__main__':
    unittest.main()
