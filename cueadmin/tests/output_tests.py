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


import contextlib
import mock
import StringIO
import sys
import unittest

import opencue.compiled_proto.facility_pb2
import opencue.compiled_proto.host_pb2
import opencue.compiled_proto.service_pb2
import opencue.compiled_proto.show_pb2
import opencue.compiled_proto.subscription_pb2
import opencue.wrappers.allocation
import opencue.wrappers.host
import opencue.wrappers.proc
import opencue.wrappers.service
import opencue.wrappers.show
import opencue.wrappers.subscription
import cueadmin.output


@contextlib.contextmanager
def captured_output():
    new_out, new_err = StringIO.StringIO(), StringIO.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


@mock.patch('opencue.cuebot.Cuebot.getStub')
@mock.patch('time.time', mock.MagicMock(return_value=1556846762))
class OutputTests(unittest.TestCase):

    def testDisplayProcs(self, getStubMock):
        procs = [
            opencue.wrappers.proc.Proc(
                opencue.compiled_proto.host_pb2.Proc(
                    name='proc1',
                    reserved_cores=28,
                    used_memory=44,
                    reserved_memory=120,
                    job_name='mms2oazed2bbcjk60gho_w11licymr63s66bw1b3s',
                    frame_name='y0ihh3fxrstz6ub7ut2k',
                    dispatch_time=1556845762
                ))]

        with captured_output() as (out, err):
            cueadmin.output.displayProcs(procs)

        self.assertEqual(
            'Host       Cores   Memory                   Job                            / Frame                          Start        Runtime      \n'
            'proc1      28.00   44K of 120K (36.67%)     mms2oazed2bbcjk60gho_w11licy.. / y0ihh3fxrstz6ub7ut2k           05/02 18:09  00:16:40     \n',
            out.getvalue())

    def testDisplayHosts(self, getStubMock):
        hosts = [
            opencue.wrappers.host.Host(
                opencue.compiled_proto.host_pb2.Host(
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
                ))]

        with captured_output() as (out, err):
            cueadmin.output.displayHosts(hosts)

        self.assertEqual(
            'Host            Load NIMBY freeMem  freeSwap freeMcp   Cores Mem   Idle             Os       Uptime   State  Locked    Alloc      Thread \n'
            'host1           25   False 3.3G     1015M    80.9G     6.0   4.3G  [ 5.00 / 2.9G ]  Linux    00:02    DOWN   LOCKED    alloc01    ALL    \n',
            out.getvalue())

    def testDisplayShows(self, getStubMock):
        shows = [
            opencue.wrappers.show.Show(
                opencue.compiled_proto.show_pb2.Show(
                    name='testing',
                    active=True,
                    show_stats=opencue.compiled_proto.show_pb2.ShowStats(
                        reserved_cores=265,
                        running_frames=100,
                        pending_frames=248,
                        pending_jobs=29
                    )
                ))]

        with captured_output() as (out, err):
            cueadmin.output.displayShows(shows)

        self.assertEqual(
            'Show     Active   ReservedCores   RunningFrames   PendingFrames     PendingJobs\n'
            'testing  True            265.00             100             248              29\n',
            out.getvalue())

    def testDisplayServices(self, getStubMock):
        services = [
            opencue.wrappers.service.Service(
                opencue.compiled_proto.service_pb2.Service(
                    name='maya',
                    threadable=False,
                    min_cores=100,
                    min_memory=2097152,
                    tags=['general', 'desktop']
                ))
        ]

        with captured_output() as (out, err):
            cueadmin.output.displayServices(services)

        self.assertEqual(
            'Name                 Can Thread   Min Cores Units      Min Memory      Tags                                \n'
            'maya                 False        100                  2097152 MB      general | desktop                   \n',
            out.getvalue())

    def testDisplayAllocations(self, getStubMock):
        allocs = [
            opencue.wrappers.allocation.Allocation(
                opencue.compiled_proto.facility_pb2.Allocation(
                    name='local.desktop',
                    tag='desktop',
                    billable=False,
                    stats=opencue.compiled_proto.facility_pb2.AllocationStats(
                        running_cores=100,
                        available_cores=125,
                        cores=600,
                        locked_hosts=25,
                        down_hosts=3
                    )
                ))]

        with captured_output() as (out, err):
            cueadmin.output.displayAllocations(allocs)

        self.assertEqual(
            'Name                                  Tag  Running     Avail     Cores    Hosts   Locked     Down Billable\n'
            'local.desktop                     desktop   100.00    125.00     600.0        0       25        3 False   \n',
            out.getvalue())

    def testDisplaySubscriptions(self, getStubMock):
        subs = [
            opencue.wrappers.subscription.Subscription(
                opencue.compiled_proto.subscription_pb2.Subscription(
                    allocation_name='local.general',
                    show_name='showName',
                    size=1000,
                    burst=1500,
                    reserved_cores=500
                )),
            opencue.wrappers.subscription.Subscription(
                opencue.compiled_proto.subscription_pb2.Subscription(
                    allocation_name='cloud.desktop',
                    show_name='showName',
                    size=0,
                    burst=1500,
                    reserved_cores=50
                )),
        ]

        with captured_output() as (out, err):
            cueadmin.output.displaySubscriptions(subs, 'showName')

        self.assertEqual(
            'Subscriptions for showName\n'
            'Allocation                     Show           Size    Burst      Run     Used\n'
            'local.general                  showName       1000     1500   500.00   50.00%\n'
            'cloud.desktop                  showName          0     1500    50.00 5000.00%\n',
            out.getvalue())

    def testDisplayJobs(self, getStubMock):
        with captured_output() as (out, err):
            cueadmin.output.displayJobs([])


        'Job                                                      Group           Booked   Cores     Wait   Pri MinCores MaxCores\n'




if __name__ == '__main__':
    unittest.main()
