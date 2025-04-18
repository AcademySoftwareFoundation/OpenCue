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


"""Tests for cueadmin.output."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

# pylint: disable=wrong-import-order,wrong-import-position
from future import standard_library
standard_library.install_aliases()

import contextlib
import mock
import io
import sys
import time
import unittest

import opencue_proto.facility_pb2
import opencue_proto.host_pb2
import opencue_proto.job_pb2
import opencue_proto.service_pb2
import opencue_proto.show_pb2
import opencue_proto.subscription_pb2
import opencue.wrappers.allocation
import opencue.wrappers.frame
import opencue.wrappers.host
import opencue.wrappers.job
import opencue.wrappers.layer
import opencue.wrappers.proc
import opencue.wrappers.service
import opencue.wrappers.show
import opencue.wrappers.subscription

import cueadmin.output


# pylint: disable=line-too-long


@contextlib.contextmanager
def captured_output():
    new_out, new_err = io.StringIO(), io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


@mock.patch('opencue.cuebot.Cuebot.getStub')
@mock.patch('time.time', mock.MagicMock(return_value=1556846762+time.altzone))
class OutputTests(unittest.TestCase):

    def testDisplayProcs(self, getStubMock):
        procs = [
            opencue.wrappers.proc.Proc(
                opencue_proto.host_pb2.Proc(
                    name='proc1',
                    reserved_cores=28,
                    used_memory=44,
                    reserved_memory=120,
                    job_name='mms2oazed2bbcjk60gho_w11licymr63s66bw1b3s',
                    frame_name='y0ihh3fxrstz6ub7ut2k',
                    dispatch_time=1556845762+time.altzone
                ))]

        with captured_output() as (out, err):
            cueadmin.output.displayProcs(procs)

        self.assertEqual(
            'Host       Cores   Memory                   Job                            / Frame                          Start        Runtime     \n'
            'proc1      28.00   44K of 120K (36.67%)     mms2oazed2bbcjk60gho_w11licy.. / y0ihh3fxrstz6ub7ut2k           05/03 01:09  00:16:40    \n',
            out.getvalue())

    def testDisplayHosts(self, getStubMock):
        hosts = [
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
                    boot_time=1556836762+time.altzone,
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
                opencue_proto.show_pb2.Show(
                    name='testing',
                    active=True,
                    show_stats=opencue_proto.show_pb2.ShowStats(
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
                opencue_proto.service_pb2.Service(
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
                opencue_proto.subscription_pb2.Subscription(
                    allocation_name='local.general',
                    show_name='showName',
                    size=1000,
                    burst=1500,
                    reserved_cores=500
                )),
            opencue.wrappers.subscription.Subscription(
                opencue_proto.subscription_pb2.Subscription(
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
            'local.general                  showName       10.0     15.0     5.00   50.00%\n'
            'cloud.desktop                  showName        0.0     15.0     0.50    0.50%\n',
            out.getvalue())

    def testDisplayJobs(self, getStubMock):
        jobs = [
            opencue.wrappers.job.Job(
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
                )),
            opencue.wrappers.job.Job(
                opencue_proto.job_pb2.Job(
                    name='mlSCNFWWwksH8i0rb8UE-v5u1bh5jfixzXG7',
                    is_paused=True,
                    group='u0uMmB1O0z3ZkvreFYzP',
                    job_stats=opencue_proto.job_pb2.JobStats(
                        running_frames=2300,
                        reserved_cores=1000,
                        waiting_frames=0,
                    ),
                    priority=95,
                    min_cores=6,
                    max_cores=None
                )),
        ]

        with captured_output() as (out, err):
            cueadmin.output.displayJobs(jobs)

        self.assertEqual(
            'Job                                                      Group           Booked   Cores     Wait   Pri MinCores MaxCores\n'
            'd7HXvMXDNMKyfzLumwsY-P3CNG1w4pa452dGcqOyf_qVK5PbHm..     u0uMmB1O0z3Zk..     5    5.00      182    89     1.00     1.00\n'
            'mlSCNFWWwksH8i0rb8UE-v5u1bh5jfixzXG7 [paused]            u0uMmB1O0z3Zk..  2300 1000.00        0    95     6.00     0.00\n',
            out.getvalue())

    @mock.patch('opencue.wrappers.job.Job.getLayers')
    def testDisplayJobInfo(self, getLayersMock, getStubMock):
        job = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(
                name='d7HXvMXDNMKyfzLumwsY-P3CNG1w4pa452dGcqOyf_qVK5PbHmCZafkv4rEF8d',
                start_time=1556836762+time.altzone,
                is_paused=True,
                min_cores=1,
                max_cores=6,
                job_stats=opencue_proto.job_pb2.JobStats(
                    total_frames=2600,
                    succeeded_frames=150,
                    running_frames=2300,
                    waiting_frames=100,
                    depend_frames=50,
                    dead_frames=0,
                ),
            )
        )

        getLayersMock.return_value = [
            opencue.wrappers.layer.Layer(
                opencue_proto.job_pb2.Layer(
                    name='preflight',
                    tags=['preflightTag', 'general'],
                    layer_stats=opencue_proto.job_pb2.LayerStats(
                        total_frames=2,
                        succeeded_frames=1
                    )
                )
            ),
            opencue.wrappers.layer.Layer(
                opencue_proto.job_pb2.Layer(
                    name='render',
                    tags=['renderPool'],
                    layer_stats=opencue_proto.job_pb2.LayerStats(
                        total_frames=2598,
                        succeeded_frames=149
                    )
                )
            )
        ]

        with captured_output() as (out, err):
            cueadmin.output.displayJobInfo(job)

        self.assertEqual(
            '------------------------------------------------------------\n'
            'job: d7HXvMXDNMKyfzLumwsY-P3CNG1w4pa452dGcqOyf_qVK5PbHmCZafkv4rEF8d\n'
            '\n'
            '   start time: 05/02 22:39\n'
            '        state: PAUSED\n'
            '         type: N/A\n'
            ' architecture: N/A\n'
            '     services: N/A\n'
            'Min/Max cores: 1.00 / 6.00\n'
            '\n'
            'total number of frames: 2600\n'
            '                  done: 150\n'
            '               running: 2300\n'
            '       waiting (ready): 100\n'
            '      waiting (depend): 50\n'
            '                failed: 0\n'
            '   total frame retries: N/A\n'
            '\n'
            'this is a cuerun3 job with 2 layers\n'
            '\n'
            'preflight  (2 frames, 1 done)\n'
            '   average frame time: N/A\n'
            '   average ram usage: N/A\n'
            '   tags: preflightTag | general\n'
            '\n'
            'render  (2598 frames, 149 done)\n'
            '   average frame time: N/A\n'
            '   average ram usage: N/A\n'
            '   tags: renderPool\n'
            '\n',
            out.getvalue())

    def testDisplayFrames(self, getStubMock):
        frames = [
            opencue.wrappers.frame.Frame(
                opencue_proto.job_pb2.Frame(
                    name='rFNQafSvWkCQA3O7SaJw-tWa1L92CjGM0syBsxMwp-8sk6X0thFbCFaL06wAPc',
                    state=opencue_proto.job_pb2.SUCCEEDED,
                    start_time=1556836762+time.altzone,
                    stop_time=1556846762+time.altzone,
                    max_rss=927392,
                    exit_status=0,
                    last_resource='render-host-01',
                    retry_count=1
                )
            ),
            opencue.wrappers.frame.Frame(
                opencue_proto.job_pb2.Frame(
                    name='XjWPTN6CsAujCmgKHfyA-u2wFSQg2MNu',
                    state=opencue_proto.job_pb2.WAITING,
                    start_time=None,
                    stop_time=None,
                    max_rss=None,
                    exit_status=None,
                    last_resource=None,
                    retry_count=0
                )
            ),
        ]

        with captured_output() as (out, err):
            cueadmin.output.displayFrames(frames)

        self.assertEqual(
            'Frame                               Status      Host            Start         End          Runtime     Mem   Retry  Exit\n'
            '------------------------------------------------------------------------------------------------------------------------\n'
            'rFNQafSvWkCQA3O7SaJw-tWa1L92CjGM0.. SUCCEEDED   render-host-01  05/02 22:39   05/03 01:26  02:46:40   905M       1     0\n'
            'XjWPTN6CsAujCmgKHfyA-u2wFSQg2MNu    WAITING                     --/-- --:--   --/-- --:--               0K       0     0\n',
            out.getvalue())


if __name__ == '__main__':
    unittest.main()
