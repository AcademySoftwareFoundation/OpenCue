#!/usr/bin/env python

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


import mock
import unittest

import opencue.compiled_proto.show_pb2
import opencue.wrappers.show
import cueadmin.common


TEST_SHOW = 'test_show'
TEST_FACILITY = 'some-non-default-facility'
TEST_ALLOC = 'test_alloc'
TEST_HOST = 'some_host'
TEST_JOB = 'my_random_job_name'


@mock.patch('opencue.api.findShow')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class ShowTests(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    @mock.patch('opencue.api.createShow')
    def testCreateShow(self, createShowMock, getStubMock, findShowMock):
        args = self.parser.parse_args(['-create-show', TEST_SHOW, '-force'])

        cueadmin.common.handleArgs(args)

        createShowMock.assert_called_with(TEST_SHOW)

    def testDeleteShow(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-delete-show', TEST_SHOW, '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.delete.assert_called_with()

    def testEnableBooking(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-booking', TEST_SHOW, 'on', '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.enableBooking.assert_called_with(True)

    def testDisableBooking(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-booking', TEST_SHOW, 'off', '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.enableBooking.assert_called_with(False)

    def testEnableDispatch(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-dispatching', TEST_SHOW, 'on', '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.enableDispatching.assert_called_with(True)

    def testDisableDispatch(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-dispatching', TEST_SHOW, 'off', '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.enableDispatching.assert_called_with(False)

    def testDefaultMinCores(self, getStubMock, findShowMock):
        arbitraryCoreCount = 873
        args = self.parser.parse_args(
            ['-default-min-cores', TEST_SHOW, str(arbitraryCoreCount), '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.setDefaultMinCores.assert_called_with(arbitraryCoreCount)

    def testDefaultMaxCores(self, getStubMock, findShowMock):
        arbitraryCoreCount = 9349
        args = self.parser.parse_args(
            ['-default-max-cores', TEST_SHOW, str(arbitraryCoreCount), '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.setDefaultMaxCores.assert_called_with(arbitraryCoreCount)


@mock.patch('opencue.api.findAllocation')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class AllocTests(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    @mock.patch('opencue.api.createAllocation')
    @mock.patch('opencue.api.getFacility')
    def testCreateAlloc(self, getFacilityMock, createAllocMock, getStubMock, findAllocMock):
        tagName = 'random-tag'
        args = self.parser.parse_args(
            ['-create-alloc', TEST_FACILITY, TEST_ALLOC, tagName, '-force'])
        facMock = mock.Mock()
        getFacilityMock.return_value = facMock

        cueadmin.common.handleArgs(args)

        getFacilityMock.assert_called_with(TEST_FACILITY)
        createAllocMock.assert_called_with(TEST_ALLOC, tagName, facMock)

    def testDeleteAlloc(self, getStubMock, findAllocMock):
        args = self.parser.parse_args(
            ['-delete-alloc', '%s.%s' % (TEST_FACILITY, TEST_ALLOC), '-force'])
        allocMock = mock.Mock()
        findAllocMock.return_value = allocMock

        cueadmin.common.handleArgs(args)

        allocMock.delete.assert_called_with()

    def testRenameAlloc(self, getStubMock, findAllocMock):
        oldFullName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        newName = 'some_new_alloc_name'
        newFullName = '%s.%s' % (TEST_FACILITY, newName)
        args = self.parser.parse_args(['-rename-alloc', oldFullName, newFullName, '-force'])
        allocMock = mock.Mock()
        findAllocMock.return_value = allocMock

        cueadmin.common.handleArgs(args)

        findAllocMock.assert_called_with(oldFullName)
        allocMock.setName.assert_called_with(newName)

    def testTagAlloc(self, getStubMock, findAllocMock):
        allocName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        tagName = 'new_tag'
        args = self.parser.parse_args(['-tag-alloc', allocName, tagName, '-force'])
        allocMock = mock.Mock()
        findAllocMock.return_value = allocMock

        cueadmin.common.handleArgs(args)

        findAllocMock.assert_called_with(allocName)
        allocMock.setTag.assert_called_with(tagName)

    def testReparentHosts(self, getStubMock, findAllocMock):
        srcAllocName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        dstAllocName = '%s.some_other_alloc' % TEST_FACILITY
        args = self.parser.parse_args(['-transfer', srcAllocName, dstAllocName, '-force'])
        srcAllocMock = mock.Mock()
        dstAllocMock = mock.Mock()
        findAllocMock.side_effect = [srcAllocMock, dstAllocMock]
        hostList = ['some', 'arbitrary', 'list', 'of', 'hosts']
        srcAllocMock.getHosts.return_value = hostList

        cueadmin.common.handleArgs(args)

        findAllocMock.assert_has_calls([mock.call(srcAllocName), mock.call(dstAllocName)])
        dstAllocMock.reparentHosts.assert_called_with(hostList)

@mock.patch('opencue.search.HostSearch')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class HostTests(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    def testSetRepairState(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-repair', '-host', TEST_HOST, '-force'])
        hostMock = mock.Mock()
        hostSearchMock.byName.return_value = [hostMock]

        cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST])
        hostMock.setHardwareState.assert_called_with(opencue.api.host_pb2.REPAIR)

    def testLockHost(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-lock', '-host', TEST_HOST, '-force'])
        hostMock = mock.Mock()
        hostSearchMock.byName.return_value = [hostMock]

        cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST])
        hostMock.lock.assert_called_with()

    def testUnlockHost(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-unlock', '-host', TEST_HOST, '-force'])
        hostMock = mock.Mock()
        hostSearchMock.byName.return_value = [hostMock]

        cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST])
        hostMock.unlock.assert_called_with()

    @mock.patch('opencue.api.findAllocation')
    def testMoveHost(self, findAllocMock, getStubMock, hostSearchMock):
        allocName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        args = self.parser.parse_args(['-move', allocName, '-host', TEST_HOST, '-force'])
        hostMock = mock.Mock()
        hostSearchMock.byName.return_value = [hostMock]
        allocMock = mock.Mock()
        findAllocMock.return_value = allocMock

        cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST])
        findAllocMock.assert_called_with(allocName)
        hostMock.setAllocation.assert_called_with(allocMock.data)

    @mock.patch('opencue.api.getHosts')
    def testListHosts(self, getHostsMock, getStubMock, hostSearchMock):
        arbitraryMatchString = 'arbitraryMatchString'
        args = self.parser.parse_args(
            ['-lh', arbitraryMatchString, '-state', 'up', 'repair', '-alloc', TEST_ALLOC])

        cueadmin.common.handleArgs(args)

        getHostsMock.assert_called_with(
            alloc=[TEST_ALLOC], match=[arbitraryMatchString],
            state=[opencue.api.host_pb2.UP, opencue.api.host_pb2.REPAIR])


@mock.patch('opencue.api.findSubscription')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class SubscriptionTests(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    @mock.patch('opencue.api.findAllocation')
    @mock.patch('opencue.api.findShow')
    def testCreateSub(self, findShowMock, findAllocMock, getStubMock, findSubMock):
        allocName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        numCores = 125
        burstCores = 236
        args = self.parser.parse_args(
            ['-create-sub', TEST_SHOW, allocName, str(numCores), str(burstCores), '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock
        allocMock = mock.Mock()
        findAllocMock.return_value = allocMock

        cueadmin.common.handleArgs(args)

        findShowMock.assert_called_with(TEST_SHOW)
        findAllocMock.assert_called_with(allocName)
        showMock.createSubscription.assert_called_with(allocMock.data, numCores, burstCores)

    def testDeleteSub(self, getStubMock, findSubMock):
        allocName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        args = self.parser.parse_args(['-delete-sub', TEST_SHOW, allocName, '-force'])
        subName = '%s.%s' % (allocName, TEST_SHOW)
        subMock = mock.Mock()
        findSubMock.return_value = subMock

        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_with(subName)
        subMock.delete.assert_called_with()

    def testSetSize(self, getStubMock, findSubMock):
        allocName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        newSize = 200
        args = self.parser.parse_args(['-size', TEST_SHOW, allocName, str(newSize), '-force'])
        subName = '%s.%s' % (allocName, TEST_SHOW)
        subMock = mock.Mock()
        findSubMock.return_value = subMock

        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_with(subName)
        subMock.setSize.assert_called_with(newSize)

    def testSetBurst(self, getStubMock, findSubMock):
        allocName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        newBurstSize = 847
        args = self.parser.parse_args(['-burst', TEST_SHOW, allocName, str(newBurstSize), '-force'])
        subName = '%s.%s' % (allocName, TEST_SHOW)
        subMock = mock.Mock()
        findSubMock.return_value = subMock

        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_with(subName)
        subMock.setBurst.assert_called_with(newBurstSize)

    def testSetBurstPercentage(self, getStubMock, findSubMock):
        allocName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        originalSize = 120
        newBurstPerc = '20%'
        args = self.parser.parse_args(['-burst', TEST_SHOW, allocName, newBurstPerc, '-force'])
        subName = '%s.%s' % (allocName, TEST_SHOW)
        subMock = mock.Mock()
        subMock.data.size = originalSize
        findSubMock.return_value = subMock

        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_with(subName)
        subMock.setBurst.assert_called_with(originalSize * (1 + float(newBurstPerc[:-1]) / 100))


@mock.patch('opencue.search.JobSearch')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class JobTests(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    def testListJobs(self, getStubMock, jobSearchMock):
        args = self.parser.parse_args(['-lj', TEST_JOB])

        cueadmin.common.handleArgs(args)

        jobSearchMock.byMatch.assert_called_with([TEST_JOB])

    def testListJobInfo(self, getStubMock, jobSearchMock):
        args = self.parser.parse_args(['-lji', TEST_JOB])

        cueadmin.common.handleArgs(args)

        jobSearchMock.byMatch.assert_called_with([TEST_JOB])


@mock.patch('opencue.search.ProcSearch')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class ProcTests(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    def testListProcs(self, getStubMock, procSearchMock):
        resultsLimit = '54'
        args = self.parser.parse_args(
            ['-lp', TEST_SHOW, '-alloc', TEST_ALLOC, '-duration', '1.5', '-host', TEST_HOST,
             '-job', TEST_JOB, '-limit', resultsLimit, '-memory', '128'])

        cueadmin.common.handleArgs(args)

        procSearchMock.byOptions.assert_called_with(
            alloc=[TEST_ALLOC],
            duration=[opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(value=5400)],
            host=[TEST_HOST], job=[TEST_JOB], limit=resultsLimit,
            memory=[opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(value=134217728)],
            show=[TEST_SHOW])


if __name__ == '__main__':
    unittest.main()
