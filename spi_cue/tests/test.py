#!/usr/local/bin/python

# Copyright (c) 2017 Sony Pictures Imageworks Inc. All rights reserved.
# consolidated api_test, search_test, and util tests

import os
import unittest
import os.path
import sys
# print __file__
# print os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
# sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
modulePath = os.path.abspath(os.path.join(__file__, "../.."))
sys.path.append(modulePath)

import Cue3 as cue3
import utils
import constants

TEST_SHOW_NAME = "pipe"
TEST_GROUP_NAME = "pipe"
TEST_GROUP_ID = "A0000000-0000-0000-0000-000000000000"
TEST_JOB_NAME = "pipe-dev.cue-chambers_shell_v6";
TEST_LAYER_NAME = "depend_er"
TEST_HOST_NAME = "wolf1001"
TEST_SUB_NAME = "spi.general.pipe"

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
            s.proxy.delete()
        except cue3.EntityNotFoundException,e:
            pass
        finally:
            s = cue3.createShow("cue3")
            s.proxy.delete()

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
        self.assertTrue(len(cue3.getJobs(name=[TEST_JOB_NAME],show=[TEST_SHOW_NAME])) == 1)

    def testGetJob(self):
        job1 = cue3.findJob(TEST_JOB_NAME)
        job2 = cue3.getJob(cue3.id(job1))

    def testGetJobNames(self):
        self.assertTrue(len(cue3.getJobNames(show=[TEST_SHOW_NAME])) > 0)

class LayerTests(unittest.TestCase):

    def testFindLayer(self):
        cue3.findLayer(TEST_JOB_NAME,TEST_LAYER_NAME)

    def testGetLayer(self):
        layer1 = cue3.findLayer(TEST_JOB_NAME,TEST_LAYER_NAME)
        layer2 = cue3.getLayer(cue3.id(layer1))

class FrameTests(unittest.TestCase):

    def testFindFrame(self):
        cue3.findFrame(TEST_JOB_NAME,TEST_LAYER_NAME, 1)

    def testGetFrame(self):
        frame1 = cue3.findFrame(TEST_JOB_NAME,TEST_LAYER_NAME, 1)
        frame2 = cue3.getFrame(cue3.id(frame1))
        self.assertEqual(frame1.data.number,frame2.data.number)

    def testGetFrames(self):
        self.assertTrue(cue3.getFrames(TEST_JOB_NAME,range="1-5") > 0)

class SubscriptionTests(unittest.TestCase):

    def testFindSubscription(self):
        cue3.findSubscription(TEST_SUB_NAME)

    def testGetSubscription(self):
        sub1 = cue3.findSubscription(TEST_SUB_NAME)
        sub2 = cue3.getSubscription(cue3.id(sub1))
        self.assertEqual(cue3.id(sub1),cue3.id(sub2))

class HostTests(unittest.TestCase):

    def testGetHosts(self):
        self.assertTrue(len(cue3.getHosts(name=[TEST_HOST_NAME])) == 1)

    # this is failing all the time
    # def testGetHostWhiteboard(self):
    #     cue3.get_host_whiteboard()

    def testFindHost(self):
        h = cue3.findHost(TEST_HOST_NAME)
        self.assertEquals(h.data.name,TEST_HOST_NAME)

    def testGetHost(self):
        h = cue3.findHost(TEST_HOST_NAME)
        self.assertEquals(h.data.name, TEST_HOST_NAME)
        h2 = cue3.getHost(cue3.id(h))
        self.assertEquals(h.data.name,h2.data.name)

class JobSearchTests(unittest.TestCase):

    def testByOptions(self):
        # job1 = cue3.JobSearch(show=["pipe"],match=["v6"]).find()
        job1 = cue3.JobSearch.byOptions(show=["pipe"],match=["v6"])
        job2 = cue3.JobSearch.byOptions(ids=[job1])
        self.assertTrue(job1[0].data.name,job2[0].data.name)

class ProxyTests(unittest.TestCase):
    """proxy converts different types of entities to usable Ice proxies"""

    def testProxyUniqueId(self):
        """convert a string and class name to proxy"""
        id = "A0000000-0000-0000-0000-000000000000"
        self.assertEquals(str(cue3.proxy(id, "Group")),
            "manageGroup/%s -t -e 1.0:tcp -h localhost -p 9019 -t 10000" % id)

    def testProxyUniqueIdArray(self):
        """convert a list of strings and a class name to a proxy"""
        ids = ["A0000000-0000-0000-0000-000000000000","B0000000-0000-0000-0000-000000000000"]
        self.assertTrue(len(cue3.proxy(ids, "Group")), 2)

    def testProxyEntity(self):
        """convert an entity to a proxy"""
        job = cue3.getJobs()[0]
        self.assertEquals(job.proxy, cue3.proxy(job))

    def testProxyProxy(self):
        """convert a proxy to a proxy"""
        job = cue3.getJobs()[0]
        proxy = job.proxy
        self.assertEquals(proxy, cue3.proxy(proxy))

    def testProxyEntityList(self):
        """convert a list of entities to a list of proxies"""
        jobs = cue3.getJobs()
        self.assertEquals(len(jobs), len(cue3.proxy(jobs)))
        proxies  = cue3.proxy(jobs)
        for i in range(0,len(proxies)):
            self.assertEqual(proxies[i], jobs[i].proxy)

    def testProxyProxyList(self):
        """convert a list of proxies to a list of proxies"""
        proxiesA = [job.proxy for job in cue3.getJobs()]
        proxiesB = cue3.proxy(proxiesA)
        self.assertEquals(len(proxiesA), len(proxiesB))
        for i in range(0,len(proxiesA)):
            self.assertEqual(proxiesA[i], proxiesB[i])

class IdTests(unittest.TestCase):
    """id() takes a proxy or entity and returns the unique id"""

    def testIdOnEntity(self):
        job = cue3.getJobs()[0]
        self.assertEquals(job.proxy.ice_getIdentity().name, cue3.id(job))

    def testIdOnProxy(self):
        proxy = cue3.getJobs()[0].proxy
        self.assertEquals(proxy.ice_getIdentity().name, cue3.id(proxy))

    def testIdOnEntityList(self):
        jobs = cue3.getJobs()
        ids = cue3.id(jobs)
        self.assertEquals(len(jobs), len(ids))
        for i in range(0,len(jobs)):
            self.assertEquals(jobs[i].proxy.ice_getIdentity().name, ids[i])

    def testIdOnEntityList(self):
        jobs = cue3.getJobs()
        ids = cue3.id(jobs)
        self.assertEquals(len(jobs), len(ids))
        for i in range(0,len(jobs)):
            self.assertEquals(jobs[i].proxy.ice_getIdentity().name, ids[i])


if __name__ == '__main__':
    unittest.main()


# Copyright (c) 2017 Sony Pictures Imageworks Inc. All rights reserved.
