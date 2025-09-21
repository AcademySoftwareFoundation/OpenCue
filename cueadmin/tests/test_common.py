#!/usr/bin/env python

#  Copyright Contributors to the OpenCue Project
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


"""Tests for cueadmin.common."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
import unittest

import mock

import opencue_proto.facility_pb2
import opencue_proto.host_pb2
import opencue_proto.job_pb2
import opencue_proto.service_pb2
import opencue_proto.show_pb2
import opencue_proto.subscription_pb2
import opencue.wrappers.allocation
import opencue.wrappers.host
import opencue.wrappers.proc
import opencue.wrappers.service
import opencue.wrappers.show
import opencue.wrappers.subscription

import cueadmin.common


TEST_SHOW = 'test_show'
TEST_FACILITY = 'some-non-default-facility'
TEST_ALLOC = 'test_alloc'
TEST_HOST = 'some_host'
TEST_JOB = 'my_random_job_name'


class CommonArgTests(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    @mock.patch('cueadmin.util.enableDebugLogging')
    def testVerboseLogging(self, enableDebugLoggingMock):
        args = self.parser.parse_args(['-verbose'])

        cueadmin.common.handleArgs(args)

        enableDebugLoggingMock.assert_called_with()

    @mock.patch('opencue.Cuebot.setHosts')
    def testSetServer(self, setHostsMock):
        serverName = 'someRandomServer01'
        args = self.parser.parse_args(['-server', serverName])

        cueadmin.common.handleArgs(args)

        setHostsMock.assert_called_with([serverName])

    @mock.patch('opencue.Cuebot.setHostWithFacility')
    def testSetFacility(self, setFacilityMock):
        args = self.parser.parse_args(['-facility', TEST_FACILITY])

        cueadmin.common.handleArgs(args)

        setFacilityMock.assert_called_with(TEST_FACILITY)


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

    def testDisableShow(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-disable-show', TEST_SHOW, '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.setActive.assert_called_with(False)

    def testEnableShow(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-enable-show', TEST_SHOW, '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.setActive.assert_called_with(True)

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

    @mock.patch('opencue.api.getShows')
    def testListShows(self, getShowsMock, getStubMock, findShowMock):
        args = self.parser.parse_args(['-ls'])
        getShowsMock.return_value = [
            opencue.wrappers.show.Show(
                opencue_proto.show_pb2.Show(
                    name='testing',
                    active=True,
                    show_stats=opencue_proto.show_pb2.ShowStats(
                        reserved_cores=265,
                        running_frames=100,
                        pending_frames=248,
                        pending_jobs=29
                    )
                ))
        ]

        cueadmin.common.handleArgs(args)

        getShowsMock.assert_called_with()


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

    def testInvalidRenameAlloc(self, getStubMock, findAllocMock):
        oldFullName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        invalidNewName = 'invalid_alloc_name'
        args = self.parser.parse_args(['-rename-alloc', oldFullName, invalidNewName, '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

        findAllocMock.assert_not_called()

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

    @mock.patch('opencue.api.getAllocations')
    def testListAllocs(self, getAllocsMock, getStubMock, findAllocMock):
        args = self.parser.parse_args(['-la'])
        getAllocsMock.return_value = [
            opencue.wrappers.allocation.Allocation(
                opencue_proto.facility_pb2.Allocation(
                    name='local.desktop',
                    tag='desktop',
                    billable=False,
                    stats=opencue_proto.facility_pb2.AllocationStats(
                        running_cores=100,
                        available_cores=125,
                        cores=600,
                        locked_hosts=25,
                        down_hosts=3
                    )
                )
            )
        ]

        cueadmin.common.handleArgs(args)

        getAllocsMock.assert_called_with()

    def testListSubscriptionsForAlloc(self, getStubMock, findAllocMock):
        args = self.parser.parse_args(['-lba', TEST_ALLOC])
        allocMock = mock.Mock()
        allocMock.getSubscriptions.return_value = [
            opencue.wrappers.subscription.Subscription(
                opencue_proto.subscription_pb2.Subscription(
                    allocation_name='local.general',
                    show_name='showName',
                    size=1000,
                    burst=1500,
                    reserved_cores=500
                )
            )
        ]
        findAllocMock.return_value = allocMock

        cueadmin.common.handleArgs(args)

        findAllocMock.assert_called_with(TEST_ALLOC)
        allocMock.getSubscriptions.assert_called_with()


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

    def testInvalidSetRepairState(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-repair', '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_not_called()

    def testLockHost(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-lock', '-host', TEST_HOST, '-force'])
        hostMock = mock.Mock()
        hostSearchMock.byName.return_value = [hostMock]

        cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST])
        hostMock.lock.assert_called_with()

    def testInvalidLockHost(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-lock', '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_not_called()

    def testUnlockHost(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-unlock', '-host', TEST_HOST, '-force'])
        hostMock = mock.Mock()
        hostSearchMock.byName.return_value = [hostMock]

        cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST])
        hostMock.unlock.assert_called_with()

    def testInvalidUnlockHost(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-unlock', '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_not_called()

    @mock.patch('opencue.api.findAllocation')
    def testMoveHost(self, findAllocMock, getStubMock, hostSearchMock):
        allocName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        args = self.parser.parse_args(['-move', allocName, '-host', TEST_HOST, '-force'])
        host = opencue.wrappers.host.Host(opencue_proto.host_pb2.Host())
        host.setAllocation = mock.Mock()
        hostSearchMock.byName.return_value = [host]
        alloc = opencue.wrappers.allocation.Allocation()
        findAllocMock.return_value = alloc

        cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST])
        findAllocMock.assert_called_with(allocName)
        host.setAllocation.assert_called_with(alloc)

    def testInvalidMoveHost(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-move', TEST_ALLOC, '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_not_called()

    @mock.patch('opencue.api.getHosts')
    def testListHosts(self, getHostsMock, getStubMock, hostSearchMock):
        arbitraryMatchString = 'arbitraryMatchString'
        args = self.parser.parse_args(
            ['-lh', arbitraryMatchString, '-state', 'up', 'repair', '-alloc', TEST_ALLOC])
        getHostsMock.return_value = [
            opencue.wrappers.host.Host(
                opencue_proto.host_pb2.Host(
                    name='host1',
                    load=25,
                    nimby_enabled=False,
                    free_memory=3500000,
                    free_swap=1040000,
                    free_mcp=84782900,
                    cores=6,
                    memory=4500000,
                    idle_cores=5,
                    idle_memory=3000000,
                    os='Linux',
                    boot_time=1556836762,
                    state=1,
                    lock_state=1,
                    alloc_name='alloc01',
                    thread_mode=1
                )
            )
        ]

        cueadmin.common.handleArgs(args)

        getHostsMock.assert_called_with(
            alloc=[TEST_ALLOC], match=[arbitraryMatchString],
            state=[opencue.api.host_pb2.UP, opencue.api.host_pb2.REPAIR])

    def testDeleteHost(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-delete-host', '-host', TEST_HOST, '-force'])
        hostMock1 = mock.Mock()
        hostMock2 = mock.Mock()
        hostSearchMock.byName.return_value = [hostMock1, hostMock2]

        cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST])
        hostMock1.delete.assert_called_with()
        hostMock2.delete.assert_called_with()

    def testInvalidDeleteHost(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-delete-host', '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_not_called()

    def testSafeReboot(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-safe-reboot', '-host', TEST_HOST, '-force'])
        hostMock1 = mock.Mock()
        hostMock2 = mock.Mock()
        hostSearchMock.byName.return_value = [hostMock1, hostMock2]

        cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST])
        hostMock1.rebootWhenIdle.assert_called_with()
        hostMock2.rebootWhenIdle.assert_called_with()

    def testInvalidSafeReboot(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-safe-reboot', '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_not_called()

    def testSetThreadMode(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-thread', 'all', '-host', TEST_HOST, '-force'])
        hostMock1 = mock.Mock()
        hostMock2 = mock.Mock()
        hostSearchMock.byName.return_value = [hostMock1, hostMock2]

        cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST])
        hostMock1.setThreadMode.assert_called_with(opencue.api.host_pb2.ALL)
        hostMock2.setThreadMode.assert_called_with(opencue.api.host_pb2.ALL)

    def testInvalidSetThreadMode(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-thread', 'all', '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_not_called()

    def testSetFixed(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-fixed', '-host', TEST_HOST, '-force'])
        hostMock = mock.Mock()
        hostSearchMock.byName.return_value = [hostMock]

        cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST])
        hostMock.setHardwareState.assert_called_with(opencue.api.host_pb2.UP)

    def testInvalidSetFixed(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(['-fixed', '-force'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_not_called()


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

    @mock.patch('opencue.api.findShow')
    def testListSubs(self, findShowMock, getStubMock, findSubMock):
        args = self.parser.parse_args(['-lb', TEST_SHOW])
        showMock = mock.Mock()
        showMock.getSubscriptions.return_value = [
            opencue.wrappers.subscription.Subscription(
                opencue_proto.subscription_pb2.Subscription(
                    allocation_name='cloud.desktop',
                    show_name='showName',
                    size=0,
                    burst=1500,
                    reserved_cores=50
                )
            ),
        ]
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        findShowMock.assert_called_with(TEST_SHOW)
        showMock.getSubscriptions.assert_called_with()

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
        jobSearchMock.byMatch.return_value = opencue_proto.job_pb2.JobGetJobsResponse(
            jobs=opencue_proto.job_pb2.JobSeq(
                jobs=[
                    opencue_proto.job_pb2.Job(
                        name='d7HXvMXDNMKyfzLumwsY-P3CNG1w4pa452dGcqOyf_qVK5PbHmCZafkv4rEF8d',
                        is_paused=False,
                        group='u0uMmB1O0z3ZkvreFYzP',
                        job_stats=opencue_proto.job_pb2.JobStats(
                            running_frames=5,
                            reserved_cores=5,
                            waiting_frames=182,
                        ),
                        priority=89,
                        min_cores=1,
                        max_cores=1
                    )
                ]
            )
        )

        cueadmin.common.handleArgs(args)

        jobSearchMock.byMatch.assert_called_with([TEST_JOB])

    def testListJobInfo(self, getStubMock, jobSearchMock):
        args = self.parser.parse_args(['-lji', TEST_JOB])
        jobSearchMock.byMatch.return_value = opencue_proto.job_pb2.JobGetJobsResponse(
            jobs=opencue_proto.job_pb2.JobSeq(
                jobs=[
                    opencue_proto.job_pb2.Job(
                        name='d7HXvMXDNMKyfzLumwsY-P3CNG1w4pa452dGcqOyf_qVK5PbHmCZafkv4rEF8d',
                        is_paused=False,
                        group='u0uMmB1O0z3ZkvreFYzP',
                        job_stats=opencue_proto.job_pb2.JobStats(
                            running_frames=5,
                            reserved_cores=5,
                            waiting_frames=182,
                        ),
                        priority=89,
                        min_cores=1,
                        max_cores=1
                    )
                ]
            )
        )

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
        procSearchMock.byOptions.return_value = \
            opencue_proto.host_pb2.ProcGetProcsResponse(
                procs=opencue_proto.host_pb2.ProcSeq(
                    procs=[
                        opencue_proto.host_pb2.Proc(
                            name='proc1',
                            reserved_cores=28,
                            used_memory=44,
                            reserved_memory=120,
                            job_name='mms2oazed2bbcjk60gho_w11licymr63s66bw1b3s',
                            frame_name='y0ihh3fxrstz6ub7ut2k',
                            dispatch_time=1556845762
                        )
                    ]
                )
            )

        cueadmin.common.handleArgs(args)

        procSearchMock.byOptions.assert_called_with(
            alloc=[TEST_ALLOC],
            duration=[opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(value=5400)],
            host=[TEST_HOST], job=[TEST_JOB], limit=resultsLimit,
            memory=[opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(value=134217728)],
            show=[TEST_SHOW])

    def testListFrameLogPaths(self, getStubMock, procSearchMock):
        resultsLimit = '54'
        args = self.parser.parse_args(
            ['-ll', TEST_SHOW, '-alloc', TEST_ALLOC, '-duration', '1.5',
             '-job', TEST_JOB, '-limit', resultsLimit, '-memory', '128'])
        procSearchMock.byOptions.return_value = \
            opencue_proto.host_pb2.ProcGetProcsResponse(
                procs=opencue_proto.host_pb2.ProcSeq(
                    procs=[
                        opencue_proto.host_pb2.Proc(
                            name='proc1',
                            reserved_cores=28,
                            used_memory=44,
                            reserved_memory=120,
                            job_name='mms2oazed2bbcjk60gho_w11licymr63s66bw1b3s',
                            frame_name='y0ihh3fxrstz6ub7ut2k',
                            dispatch_time=1556845762
                        )
                    ]
                )
            )

        cueadmin.common.handleArgs(args)

        procSearchMock.byOptions.assert_called_with(
            alloc=[TEST_ALLOC],
            duration=[opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(value=5400)],
            host=[], job=[TEST_JOB], limit=resultsLimit,
            memory=[opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(value=134217728)],
            show=[TEST_SHOW])


@mock.patch('opencue.cuebot.Cuebot.getStub')
class ServiceTests(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    @mock.patch('opencue.api.getDefaultServices')
    def testListDefaultServices(self, getDefaultServicesMock, getStubMock):
        args = self.parser.parse_args(['-lv'])
        getDefaultServicesMock.return_value = [
            opencue.wrappers.service.Service(
                opencue_proto.service_pb2.Service(
                    name='maya',
                    threadable=False,
                    min_cores=100,
                    min_memory=2097152,
                    tags=['general', 'desktop']
                ))
        ]

        cueadmin.common.handleArgs(args)

        getDefaultServicesMock.assert_called_with()

    @mock.patch('opencue.api.findShow')
    def testListShowServices(self, findShowMock, getStubMock):
        args = self.parser.parse_args(['-lv', TEST_SHOW])
        showMock = mock.Mock()
        showMock.getServiceOverrides.return_value = [
            opencue.wrappers.service.Service(
                opencue_proto.service_pb2.Service(
                    name='maya',
                    threadable=False,
                    min_cores=100,
                    min_memory=2097152,
                    tags=['general', 'desktop']
                )
            )
        ]
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        findShowMock.assert_called_with(TEST_SHOW)
        showMock.getServiceOverrides.assert_called_with()


if __name__ == '__main__':
    unittest.main()
