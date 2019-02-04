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

import grpc

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
import opencue

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
        opencue.api.getShows()

    def testFindShow(self):
        opencue.api.findShow(TEST_SHOW_NAME)

    def testCreateShow(self):
        try:
            s = opencue.api.findShow("cue")
            opencue.api.deleteShow(s.id())
        except opencue.EntityNotFoundException:
            pass
        finally:
            s = opencue.api.createShow("cue")
            opencue.api.deleteShow(s.id())


class GroupTests(unittest.TestCase):

    def testFindGroup(self):
        opencue.api.findGroup(TEST_SHOW_NAME, TEST_GROUP_NAME)

    def testGetGroup(self):
        opencue.api.getGroup(TEST_GROUP_ID)


class JobTests(unittest.TestCase):

    def testIsJobPending(self):
        self.assertFalse(opencue.api.isJobPending("notpending"))

    def testFindJob(self):
        self.assertRaises(opencue.EntityNotFoundException, opencue.api.findJob, "notfound")
        opencue.api.findJob(TEST_JOB_NAME)

    def testGetJobs(self):
        self.assertTrue(len(opencue.api.getJobs(show=[TEST_SHOW_NAME], all=True)) > 0)
        self.assertTrue(len(opencue.api.getJobs(name=[TEST_JOB_NAME], show=[TEST_SHOW_NAME])) == 1)

    def testGetJob(self):
        job1 = opencue.api.findJob(TEST_JOB_NAME)
        job2 = opencue.api.getJob(opencue.id(job1))

    def testGetJobNames(self):
        self.assertTrue(len(opencue.api.getJobNames(show=[TEST_SHOW_NAME])) > 0)


class LayerTests(unittest.TestCase):

    def testFindLayer(self):
        opencue.api.findLayer(TEST_JOB_NAME, TEST_LAYER_NAME)

    def testGetLayer(self):
        layer1 = opencue.api.findLayer(TEST_JOB_NAME, TEST_LAYER_NAME)
        layer2 = opencue.api.getLayer(opencue.id(layer1))


class FrameTests(unittest.TestCase):

    def testFindFrame(self):
        opencue.api.findFrame(TEST_JOB_NAME, TEST_LAYER_NAME, 1)

    def testGetFrame(self):
        frame1 = opencue.api.findFrame(TEST_JOB_NAME, TEST_LAYER_NAME, 1)
        frame2 = opencue.api.getFrame(opencue.id(frame1))
        self.assertEqual(frame1.number(), frame2.number())

    def testGetFrames(self):
        self.assertTrue(opencue.api.getFrames(TEST_JOB_NAME, range="1-5") > 0)


class CreateServiceTests(unittest.TestCase):

    testName = 'unittestingcreate'
    testTags = ['playblast', 'util']
    testThreadable = False
    testMinCores = 1000
    testMaxCores = 2000

    def setUp(self):
        self.service = opencue.wrappers.service.Service()
        self.service.setName(self.testName)
        self.service.setTags(self.testTags)
        self.service.setThreadable(self.testThreadable)
        self.service.setMinCores(self.testMinCores)
        self.service.setMaxCores(self.testMaxCores)
        existing = opencue.wrappers.service.Service.getService(self.testName)
        if existing:
            existing.delete()

    def tearDown(self):
        existing = opencue.wrappers.service.Service.getService(self.testName)
        if existing:
            existing.delete()

    def testCreate(self):
        newService = self.service.create()
        self.assertTrue(newService.id())
        self.assertTrue(self.service.name() == newService.name())
        self.assertTrue(self.service.tags() == newService.tags())
        self.assertTrue(self.service.threadable() == newService.threadable())
        self.assertTrue(self.service.minCores() == newService.minCores())
        self.assertTrue(self.service.maxCores() == newService.maxCores())


class DeleteServiceTests(unittest.TestCase):

    testName = 'unittestingdelete'
    testTags = ['playblast', 'util']
    testThreadable = False
    testMinCores = 1000
    testMaxCores = 2000

    def setUp(self):
        self.service = opencue.wrappers.service.Service()
        self.service.setName(self.testName)
        self.service.setTags(self.testTags)
        self.service.setThreadable(self.testThreadable)
        self.service.setMinCores(self.testMinCores)
        self.service.setMaxCores(self.testMaxCores)
        self.service.create()

    def tearDown(self):
        existing = opencue.api.getService(self.testName)
        if existing:
            existing.delete()

    def testDelete(self):
        existing = opencue.api.getService(self.testName)
        existing.delete()
        self.assertIsNone(opencue.api.getService(self.testName))


class ServiceTests(unittest.TestCase):

    testName = 'unittesting'
    testTags = ['playblast', 'util']
    testThreadable = False
    testMinCores = 1000
    testMaxCores = 2000
    testMinGpu = 10
    testMinMemory = 4000

    @classmethod
    def setUpClass(cls):
        service = opencue.wrappers.service.Service()
        service.setName(cls.testName)
        service.setTags(cls.testTags)
        service.setThreadable(cls.testThreadable)
        service.setMinCores(cls.testMinCores)
        service.setMaxCores(cls.testMaxCores)
        service.create()

    @classmethod
    def tearDownClass(cls):
        service = opencue.wrappers.service.Service.getService(cls.testName)
        if service:
            service.delete()

    def testGet(self):
        service = opencue.api.getService(self.testName)
        self.assertEqual(self.testName, service.name())

    def testUpdate(self):
        updatedTags = ['util']
        service = opencue.api.getService(self.testName)
        service.setTags(updatedTags)
        service.update()
        updated = opencue.api.getService(self.testName)
        self.assertEqual(updatedTags, updated.tags())


class SubscriptionTests(unittest.TestCase):

    def testFindSubscription(self):
        opencue.api.findSubscription(TEST_SUB_NAME)

    def testGetSubscription(self):
        sub1 = opencue.api.findSubscription(TEST_SUB_NAME)
        sub2 = opencue.api.getSubscription(opencue.id(sub1))
        self.assertEqual(opencue.id(sub1), opencue.id(sub2))


class HostTests(unittest.TestCase):

    def testGetHosts(self):
        self.assertTrue(len(opencue.api.getHosts(name=[TEST_HOST_NAME])) == 1)

    # this is failing all the time
    # def testGetHostWhiteboard(self):
    #     opencue.get_host_whiteboard()

    def testFindHost(self):
        h = opencue.api.findHost(TEST_HOST_NAME)
        self.assertEquals(h.name(), TEST_HOST_NAME)

    def testGetHost(self):
        h = opencue.api.findHost(TEST_HOST_NAME)
        self.assertEquals(h.name(), TEST_HOST_NAME)
        h2 = opencue.api.getHost(opencue.id(h))
        self.assertEquals(h.name(), h2.name())


if __name__ == '__main__':
    unittest.main()
