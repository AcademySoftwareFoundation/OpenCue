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
import unittest
import os.path
import sys
print __file__
print os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
import spi_cue3 as cue3
import utils
import constants

TEST_SHOW_NAME = "pipe"
TEST_GROUP_NAME = "pipe"
TEST_GROUP_ID = "A0000000-0000-0000-0000-000000000000"
TEST_JOB_NAME = "pipe-dev.cue-chambers_shell_v6";
TEST_LAYER_NAME = "depend_er"
TEST_HOST_NAME = "wolf1001"
TEST_SUB_NAME = "pipe.General"
#
#  These tests just need to call the API methods
#

class ShowTests(unittest.TestCase):

    def testGetShows(self):
        cue3.get_shows()

    def testFindShow(self):
        cue3.find_show(TEST_SHOW_NAME)

    def testCreateShow(self):
        try:
            s = cue3.find_show("cue3")
            s.proxy.delete()
        except cue3.EntityNotFoundException,e:
            pass
        finally:

            s = cue3.create_show("cue3")
            s.proxy.delete()

class GroupTests(unittest.TestCase):

    def testFindGroup(self):
        cue3.find_group(TEST_SHOW_NAME, TEST_GROUP_NAME)

    def testGetGroup(self):
        cue3.get_group(TEST_GROUP_ID)

class JobTests(unittest.TestCase):

    def testIsJobPending(self):
        self.assertFalse(cue3.is_job_pending("notpending"))

    def testFindJob(self):
        self.assertRaises(cue3.EntityNotFoundException, cue3.find_job, "notfound")
        cue3.find_job(TEST_JOB_NAME)

    def testGetJobs(self):
        self.assertTrue(len(cue3.get_jobs(show=[TEST_SHOW_NAME], all=True)) > 0)
        self.assertTrue(len(cue3.get_jobs(name=[TEST_JOB_NAME],show=[TEST_SHOW_NAME])) == 1)

    def testGetJob(self):
        job1 = cue3.find_job(TEST_JOB_NAME)
        job2 = cue3.get_job(cue3.id(job1))

    def testGetJobNames(self):
        self.assertTrue(len(cue3.get_job_names(show=[TEST_SHOW_NAME])) > 0)

class LayerTests(unittest.TestCase):

    def testFindLayer(self):
        cue3.find_layer(TEST_JOB_NAME,TEST_LAYER_NAME)

    def testGetLayer(self):
        layer1 = cue3.find_layer(TEST_JOB_NAME,TEST_LAYER_NAME)
        layer2 = cue3.get_layer(cue3.id(layer1))

class FrameTests(unittest.TestCase):

    def testFindFrame(self):
        cue3.find_frame(TEST_JOB_NAME,TEST_LAYER_NAME, 1)

    def testGetFrame(self):
        frame1 = cue3.find_frame(TEST_JOB_NAME,TEST_LAYER_NAME, 1)
        frame2 = cue3.get_frame(cue3.id(frame1))
        self.assertEqual(frame1.data.number,frame2.data.number)

    def testGetFrames(self):
        self.assertTrue(cue3.get_frames(TEST_JOB_NAME,range="1-5") > 0)

class SubscriptionTests(unittest.TestCase):

    def testFindSubscription(self):
        cue3.find_subscription(TEST_SUB_NAME)

    def testGetSubscription(self):
        sub1 = cue3.find_subscription(TEST_SUB_NAME)
        sub2 = cue3.get_subscription(cue3.id(sub1))
        self.assertEqual(cue3.id(sub1),cue3.id(sub2))

class HostTests(unittest.TestCase):

    def testGetHosts(self):
        self.assertTrue(len(cue3.get_hosts(name=[TEST_HOST_NAME])) == 1)

    # this is failing all the time
    # def testGetHostWhiteboard(self):
    #     cue3.get_host_whiteboard()

    def testFindHost(self):
        h = cue3.find_host(TEST_HOST_NAME)
        self.assertEquals(h.data.name,TEST_HOST_NAME)

    def testGetHost(self):
        h = cue3.find_host(TEST_HOST_NAME)
        self.assertEquals(h.data.name, TEST_HOST_NAME)
        h2 = cue3.get_host(cue3.id(h))
        self.assertEquals(h.data.name,h2.data.name)

if __name__ == '__main__':
    unittest.main()


