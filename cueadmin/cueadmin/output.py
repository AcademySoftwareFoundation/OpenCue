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


"""Functions for displaying output to the terminal."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import time

import opencue
import opencue_proto.job_pb2

# pylint: disable=cyclic-import
import cueadmin.common
import cueadmin.format


def displayProcs(procs):
    """Displays the proc information on one line each.
    @type procs: list<Proc>
    @param procs: Procs to display information about
    """
    proc_format = "%-10s %-7s %-24s %-30s / %-30s %-12s %-12s"
    print(proc_format % ("Host", "Cores", "Memory", "Job", "Frame", "Start", "Runtime"))
    for proc in procs:
        print(proc_format % (proc.data.name.split("/")[0],
                             "%0.2f" % proc.data.reserved_cores,
                             "%s of %s (%0.2f%%)" % (
                                 cueadmin.format.formatMem(proc.data.used_memory),
                                 cueadmin.format.formatMem(proc.data.reserved_memory),
                                 (proc.data.used_memory / float(proc.data.reserved_memory) * 100)),
                             cueadmin.format.cutoff(proc.data.job_name, 30),
                             cueadmin.format.cutoff(proc.data.frame_name, 30),
                             cueadmin.format.formatTime(proc.data.dispatch_time),
                             cueadmin.format.formatDuration(time.time() - proc.data.dispatch_time)))


def displayHosts(hosts):
    """Displays the host information on one line each.
    @type hosts: list<Host>
    @param hosts: Hosts to display information about
    """
    host_format = "%-15s %-4s %-5s %-8s %-8s %-9s %-5s %-5s %-16s %-8s %-8s %-6s %-9s %-10s %-7s"
    print(host_format % ("Host", "Load", "NIMBY", "freeMem", "freeSwap", "freeMcp", "Cores", "Mem",
                         "Idle", "Os", "Uptime", "State", "Locked", "Alloc", "Thread"))
    for host in sorted(hosts, key=lambda v: v.data.name):
        print(host_format % (host.data.name, host.data.load,
                             host.data.nimby_enabled,
                             cueadmin.format.formatMem(host.data.free_memory),
                             cueadmin.format.formatMem(host.data.free_swap),
                             cueadmin.format.formatMem(host.data.free_mcp),
                             host.data.cores,
                             cueadmin.format.formatMem(host.data.memory),
                             "[ %0.2f / %s ]" % (host.data.idle_cores,
                                                 cueadmin.format.formatMem(host.data.idle_memory)),
                             host.data.os,
                             cueadmin.format.formatLongDuration(
                                 int(time.time()) - host.data.boot_time),
                             opencue.api.host_pb2.HardwareState.Name(host.data.state),
                             opencue.api.host_pb2.LockState.Name(host.data.lock_state),
                             host.data.alloc_name,
                             opencue.api.host_pb2.ThreadMode.Name(host.data.thread_mode)))


def displayShows(shows):
    """Displays information about a list of shows
    @type shows: list<Show>
    @param shows: A list of show objects
    """
    show_format = "%-8s %-6s %15s %15s %15s %15s"
    print(show_format % ("Show", "Active", "ReservedCores", "RunningFrames", "PendingFrames",
                         "PendingJobs"))
    for show in shows:
        print(show_format % (show.data.name,
                             show.data.active,
                             "%0.2f" % show.data.show_stats.reserved_cores,
                             show.data.show_stats.running_frames,
                             show.data.show_stats.pending_frames,
                             show.data.show_stats.pending_jobs))


def displayServices(services):
    """Displays an array of services.
    @type services: list<Service>
    @param services: A list of Server objects
    """
    service_format = "%-20s %-12s %-20s %-15s %-36s"
    print(service_format % ("Name", "Can Thread", "Min Cores Units", "Min Memory", "Tags"))
    for srv in services:
        print(service_format % (srv.data.name,
                                srv.data.threadable,
                                srv.data.min_cores,
                                "%s MB" % srv.data.min_memory,
                                " | ".join(srv.data.tags)))


def displayAllocations(allocations):
    """Displays information about a list of allocations
    @type allocations: list<Allocation>
    @param allocations: A list of allocation objects
    """
    alloc_format = "%-25s %15s %8s  %8s  %8s %8s %8s %8s %-8s"
    print(alloc_format % ("Name", "Tag", "Running", "Avail", "Cores",  "Hosts", "Locked", "Down",
                          "Billable"))
    for alloc in sorted(allocations, key=lambda v: v.data.facility):
        print(alloc_format % (alloc.data.name,
                              alloc.data.tag,
                              "%0.2f" % alloc.data.stats.running_cores,
                              "%0.2f" % alloc.data.stats.available_cores,
                              alloc.data.stats.cores,
                              alloc.data.stats.hosts,
                              alloc.data.stats.locked_hosts,
                              alloc.data.stats.down_hosts,
                              alloc.data.billable))


def displaySubscriptions(subscriptions, show):
    """Displays information about a list of subscriptions
    @type subscriptions: list<Subscription>
    @param subscriptions: A list of subscription objects
    @type show: str
    @param show: show name
    """
    print("Subscriptions for %s" % show)
    sub_format = "%-30s %-12s %6s %8s %8s %8s"
    print(sub_format % ("Allocation", "Show", "Size", "Burst", "Run", "Used"))
    for s in subscriptions:
        size = s.data.size/100
        burst = s.data.burst/100
        run = s.data.reserved_cores/100
        if s.data.size:
            perc = float(s.data.reserved_cores) / s.data.size * 100.0
        else:
            perc = run

        print(sub_format % (s.data.allocation_name,
                            s.data.show_name,
                            size,
                            burst,
                            "%0.2f" % run,
                            "%0.2f%%" % perc))


def displayJobs(jobs):
    """Displays job priority information.
    @type  jobs: list<Job>
    @param jobs: All objects must have a .name parameter"""
    job_format = "%-56s %-15s %5s %7s %8s %5s %8s %8s"
    print(job_format % ("Job", "Group", "Booked", "Cores", "Wait", "Pri", "MinCores", "MaxCores"))
    for job in jobs:
        name = job.data.name + (' [paused]' if job.data.is_paused else '')
        print(job_format % (cueadmin.format.cutoff(name, 52),
                            cueadmin.format.cutoff(job.data.group, 15),
                            job.data.job_stats.running_frames,
                            "%0.2f" % job.data.job_stats.reserved_cores,
                            job.data.job_stats.waiting_frames,
                            job.data.priority,
                            "%0.2f" % job.data.min_cores,
                            "%0.2f" % job.data.max_cores))


def displayJobInfo(job):
    """Displays the job's information in cueman format.
    @type  job: Job
    @param job: Job to display"""
    print("-"*60)
    print("job: %s\n" % job.data.name)
    print("%13s: %s" % ("start time", cueadmin.format.formatTime(job.data.start_time)))
    print("%13s: %s" % ("state", "PAUSED" if job.data.is_paused else job.data.state))
    print("%13s: %s" % ("type", "N/A"))
    print("%13s: %s" % ("architecture", "N/A"))
    print("%13s: %s" % ("services", "N/A"))
    print("%13s: %0.2f / %0.2f" % ("Min/Max cores", job.data.min_cores, job.data.max_cores))
    print("")
    print("%22s: %s" % ("total number of frames", job.data.job_stats.total_frames))
    print("%22s: %s" % ("done", job.data.job_stats.succeeded_frames))
    print("%22s: %s" % ("running", job.data.job_stats.running_frames))
    print("%22s: %s" % ("waiting (ready)", job.data.job_stats.waiting_frames))
    print("%22s: %s" % ("waiting (depend)", job.data.job_stats.depend_frames))
    print("%22s: %s" % ("failed", job.data.job_stats.dead_frames))

    print("%22s: %s\n" % ("total frame retries", "N/A"))
    layers = job.getLayers()
    print("this is a cuerun3 job with %d layers\n" % len(layers))
    for layer in layers:
        print("%s  (%d frames, %d done)" % (layer.data.name, layer.data.layer_stats.total_frames,
                                            layer.data.layer_stats.succeeded_frames))
        print("   average frame time: %s" % "N/A")
        print("   average ram usage: %s" % "N/A")
        print("   tags: %s\n" % ' | '.join(layer.data.tags))


def displayFrames(frames):
    """Displays the supplied list of frames
    @type  frames: list<Frame>
    @param frames: List of frames to display"""
    framesFormat = "%-35s %-11s %-15s %-13s %-12s %-9s %5s %7s %5s"
    header = framesFormat % (
        "Frame", "Status", "Host", "Start", "End", "Runtime", "Mem", "Retry", "Exit")
    print(header + "\n" + "-" * len(header))

    for frame in frames:
        startTime = cueadmin.format.formatTime(frame.data.start_time)
        stopTime = cueadmin.format.formatTime(frame.data.stop_time)

        if frame.data.start_time:
            duration = cueadmin.format.formatDuration(
                cueadmin.format.findDuration(frame.data.start_time, frame.data.stop_time))
        else:
            duration = ""

        memory = cueadmin.format.formatMem(frame.data.max_rss)
        exitStatus = frame.data.exit_status

        print(framesFormat % (
            cueadmin.format.cutoff(frame.data.name, 35),
            opencue_proto.job_pb2.FrameState.Name(frame.data.state),
            frame.data.last_resource,
            startTime,
            stopTime,
            duration,
            memory,
            frame.data.retry_count,
            exitStatus))

    if len(frames) == 1000:
        print("Warning: Only showing first 1000 matches. See frame query options to "
              "limit your results.")
