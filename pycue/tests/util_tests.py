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


from Manifest import opencue as cue
from Manifest import unittest


class ProxyTests(unittest.TestCase):
    """proxy converts different types of entities to usable Ice proxies"""

    def testProxyUniqueId(self):
        """convert a string and class name to proxy"""
        id = "A0000000-0000-0000-0000-000000000000"
        self.assertEquals(str(cue.proxy(id, "Group")),
                          "manageGroup/%s -t -e 1.0:tcp -h localhost -p 9019 -t 10000" % id)

    def testProxyUniqueIdArray(self):
        """convert a list of strings and a class name to a proxy"""
        ids = ["A0000000-0000-0000-0000-000000000000","B0000000-0000-0000-0000-000000000000"]
        self.assertTrue(len(cue.proxy(ids, "Group")), 2)

    def testProxyEntity(self):
        """convert an entity to a proxy"""
        job = cue.api.getJobs()[0]
        self.assertEquals(job, cue.proxy(job))

    def testProxyEntityList(self):
        """convert a list of entities to a list of proxies"""
        jobs = cue.api.getJobs()
        self.assertEquals(len(jobs), len(cue.proxy(jobs, 'Job')))
        proxies = cue.proxy(jobs)
        for i in range(0, len(proxies)):
            self.assertEqual(proxies[i], jobs[i])

    def testProxyProxyList(self):
        """convert a list of proxies to a list of proxies"""
        proxiesA = [job.proxy for job in cue.api.getJobs()]
        proxiesB = cue.proxy(proxiesA)
        self.assertEquals(len(proxiesA), len(proxiesB))
        for i in range(0, len(proxiesA)):
            self.assertEqual(proxiesA[i], proxiesB[i])


class IdTests(unittest.TestCase):
    """id() takes an entity and returns the unique id"""

    def testIdOnEntity(self):
        job = cue.api.getJobs()[0]
        self.assertEquals(job.name, cue.id(job))

    def testIdOnEntityList(self):
        jobs = cue.api.getJobs()
        ids = cue.id(jobs)
        self.assertEquals(len(jobs), len(ids))
        for i in range(0,len(jobs)):
            self.assertEquals(jobs[i].name, ids[i])


if __name__ == '__main__':
    unittest.main()
