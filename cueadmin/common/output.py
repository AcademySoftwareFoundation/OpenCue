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


import time

import common
from Manifest import Cue3


def displayProcs(procs):
    """Displays the proc information on one line each.
    @type procs: list<Proc>
    @param procs: Procs to display information about
    """
    proc_format = "%-10s %-7s %-24s %-30s / %-30s %-12s %-12s "
    print proc_format % ("Host", "Cores", "Memory", "Job", "Frame", "Start", "Runtime")
    for proc in procs:
        print proc_format % (proc.data.name.split("/")[0],
                             "%0.2f" % proc.data.reserved_cores,
                             "%s of %s (%0.2f%%)" % (
                                 common.formatMem(proc.data.used_memory),
                                 common.formatMem(proc.data.reserved_memory),
                                 (proc.data.used_memory / float(proc.data.reserved_memory) * 100)),
                             common.cutoff(proc.data.job_name, 30),
                             common.cutoff(proc.data.frame_name, 30),
                             common.formatTime(proc.data.dispatch_time),
                             common.formatDuration(time.time() - proc.data.dispatch_time))


def displayHosts(hosts):
    """Displays the host information on one line each.
    @type hosts: list<Host>
    @param hosts: Hosts to display information about
    """
    host_format = "%-15s %-4s %-5s %-8s %-8s %-9s %-5s %-5s %-16s %-8s %-8s %-6s %-9s %-10s %-7s"
    print host_format % ("Host", "Load", "NIMBY", "freeMem", "freeSwap", "freeMcp", "Cores", "Mem",
                         "Idle", "Os", "Uptime", "State", "Locked", "Alloc", "Thread")
    for host in sorted(hosts, key=lambda v: v.data.name):
        print host_format % (host.data.name, host.data.load,
                             host.data.nimby_enabled,
                             common.formatMem(host.data.free_memory),
                             common.formatMem(host.data.free_swap),
                             common.formatMem(host.data.free_mcp),
                             host.data.cores,
                             common.formatMem(host.data.memory),
                             "[ %0.2f / %s ]" % (host.data.idle_cores,
                                                 common.formatMem(host.data.idle_memory)),
                             host.data.os,
                             common.formatLongDuration(int(time.time()) - host.data.boot_time),
                             host.data.state,
                             host.data.lock_state,
                             host.data.alloc_name,
                             host.data.thread_mode)


def displayShows(shows):
    """Displays information about a list of shows
    @type shows: list<Show>
    @param shows: A list of show objects
    """
    show_format = "%-8s %-6s %15s %15s %15s %15s"
    print show_format % ("Show", "Active", "ReservedCores", "RunningFrames", "PendingFrames",
                         "PendingJobs")
    for show in shows:
        print show_format % (show.data.name,
                             show.data.active,
                             "%0.2f" % show.data.show_stats.reserved_cores,
                             show.data.show_stats.running_frames,
                             show.data.show_stats.pending_frames,
                             show.data.show_stats.pending_jobs)


def displayServices(services):
    """Displays an array of services.
    @type services: list<Service>
    @param services: A list of Server objects
    """
    service_format = "%-20s %-12s %-20s %-15s %-36s"
    print service_format % ("Name", "Can Thread", "Min Cores Units", "Min Memory", "Tags")
    for srv in services:
        print service_format % (srv.data.name,
                                srv.data.threadable,
                                srv.data.min_cores,
                                "%s MB" % srv.data.min_memory,
                                " | ".join(srv.data.tags))


def displayAllocations(allocations):
    """Displays information about a list of allocations
    @type allocations: list<Allocation>
    @param allocations: A list of allocation objects
    """
    alloc_format = "%-25s %15s %8s  %8s  %8s %8s %8s %8s %-8s"
    print alloc_format % ("Name", "Tag", "Running", "Avail", "Cores",  "Hosts", "Locked", "Down",
                          "Billable")
    for alloc in sorted(allocations, key=lambda v: v.data.facility):
        print alloc_format % (alloc.data.name,
                              alloc.data.tag,
                              "%0.2f" % alloc.data.stats.running_cores,
                              "%0.2f" % alloc.data.stats.available_cores,
                              alloc.data.stats.cores,
                              alloc.data.stats.hosts,
                              alloc.data.stats.locked_hosts,
                              alloc.data.stats.down_hosts,
                              alloc.data.billable)


def displaySubscriptions(subscriptions, show):
    """Displays information about a list of subscriptions
    @type subscriptions: list<Subscription>
    @param subscriptions: A list of subscription objects
    @type show: str
    @param show: show name
    """
    print "Subscriptions for %s" % show
    sub_format = "%-30s %-12s %6s %8s %8s %8s"
    print sub_format % ("Allocation", "Show", "Size", "Burst", "Run", "Used")
    for s in subscriptions:
        if s.data.size:
            perc = (s.data.reserved_cores / s.data.size) * 100.0
        else:
            perc = (s.data.reserved_cores * 100.0)

        print sub_format % (s.data.allocation_name,
                            s.data.show_name,
                            s.data.size,
                            s.data.burst,
                            "%0.2f" % s.data.reserved_cores,
                            "%0.2f%%" % perc)


def displayDepend(depend):
        print "-"
        print "Unique ID: %s" % Cue3.id(depend)
        print "Type: %s" % depend.data.type
        print "Internal: %s" % depend.data.target
        print "Active: %s" % depend.data.active
        print "AnyFrame: %s" % depend.data.any_frame

        print "Depending Job: %s" % depend.data.depend_er_job
        if depend.data.depend_er_layer:
            print "Depending Layer: %s" % depend.data.depend_er_layer
        if depend.data.depend_er_frame:
            print "Depending Frame: %s" % depend.data.depend_er_frame
        if depend.data.depend_on_job != depend.data.depend_er_job:
            print "Depend On Job: %s" % depend.data.depend_on_job
        if depend.data.depend_on_layer:
            print "Depend On Layer: %s" % depend.data.depend_on_layer
        if depend.data.depend_on_frame:
            print "Depending Frame: %s" % depend.data.depend_on_frame


def displayDepends(depends, active_only=False):
    for depend in depends:
        if (depend.data.active and active_only) or not active_only:
            displayDepend(depend)


def displayGroups(show):
    print "Groups for %s" % Cue3.rep(show)
    grp_format = "%-32s %-12s %8s %8s %8s %8s %8s %8s %8s %6s"
    print grp_format % ("Name", "Dept", "DefPri", "DefMin", "DefMax", "MaxC", "MinC", "Booked",
                        "Cores", "Jobs")

    def enabled(v):
        if v < 0:
            return "off"
        return v

    def printGroup(group):
        name = "|%s+%-20s" % (
            "".join(["  " for i in range(0, int(group.data.level))]), group.data.name)
        print grp_format % (name,
                            group.data.department,
                            enabled(group.data.default_job_priority),
                            enabled(group.data.default_job_min_cores),
                            enabled(group.data.default_job_max_cores),
                            enabled(group.data.max_cores),
                            group.data.min_cores,
                            group.data.group_stats.running_frames,
                            "%0.2f" % group.data.group_stats.reserved_cores,
                            group.data.group_stats.pending_jobs)

    def printGroups(item):
        printGroup(item)
        for group in item.getGroups():
            printGroups(group)

    printGroups(show.getRootGroup())


def displayFilters(show, filters):
    print "Filters for %s" % show
    print "%-32s %-10s %-5s" % ("Name", "Type", "Enabled")
    for filter_ in filters:
        print "%-32s %-10s %-5s" % (filter_.data.name, filter_.data.type, filter_.data.enabled)


def displayMatchers(matchers):
    print "%-6s %-16s %-16s %-32s" % ("Order", "Subject", "Type", "Query")
    print "-------------------------------------------------------"
    order = 0
    for matcher in matchers:
        order = order + 1
        print "%06d %-16s %-16s %-32s" % (order, matcher.data.subject, matcher.data.type,
                                          matcher.data.input)
    print "------------------------------------------------------"


def displayActions(actions):
    print "%-6s %-24s %-16s" % ("Order", "Type", "Value")
    num = 0
    for action in actions:
        num += 1
        print "%06d %-24s %-16s" % (num, action.data.type, common.ActionUtil.getValue(action))


def displayFilter(filter_):
    print "Filter: "
    print "Name: %s " % filter_.data.name
    print "Type: %s " % filter_.data.type
    print "Enabled: %s " % filter_.data.enabled
    print "Order: %d " % filter_.data.order
    displayMatchers(filter_.getMatchers())
    print "Actions: "
    print "-------------------------------------------------------"
    displayActions(filter_.getActions())


def displayStrings(strings):
    """Print all of the strings in a list.
    @type  strings: list<String>
    @param strings: A list of strings"""
    for string in strings:
        print string


def displayNames(items):
    """Displays the .name of every object in the list.
    @type  items: list<>
    @param items: All objects must have a .name parameter"""
    for item in items:
        print Cue3.rep(item)


def displayLayers(job, layers):
    """Displays information about the layers in the list.
    @type  job: Job
    @param job: Job object
    @type  layers: list<Layer>
    @param layers: List of layers"""
    print "Job: %s " % job.data.name
    print "--"
    for layer in layers:

        print "Layer - %s (type: %s) - Tagged: %s - Threadable: %s" % (
            layer.data.name,
            layer.data.type,
            layer.data.tags,
            layer.data.is_threadable)
        print "Minimum Resources - Cores: %0.2f  Memory: %s" % (
            layer.data.min_cores,
            common.formatMem(layer.data.min_memory))
        print "Frames - Total: %3d  Running: %3d  Pending: %3d " % (
            layer.data.layer_stats.total_frames,
            layer.data.layer_stats.running_frames,
            layer.data.layer_stats.pending_frames)
        print "--"


def displayJobs(jobs):
    """Displays job priority information.
    @type  jobs: list<Job>
    @param jobs: All objects must have a .name parameter"""
    job_format = "%-56s %-15s %5s %7s %8s %5s %8s %8s"
    print job_format % ("Job", "Group", "Booked", "Cores", "Wait", "Pri", "MinCores", "MaxCores")
    for job in jobs:
        p = ""
        if job.data.is_paused:
            p = " [paused]"
        name = job.data.name + p
        print job_format % (common.cutoff(name, 52),
                            common.cutoff(job.data.group, 15),
                            job.stats.running_frames,
                            "%0.2f" % job.stats.reserved_cores,
                            job.stats.waiting_frames,
                            job.data.priority,
                            "%0.2f" % job.data.min_cores,
                            "%0.2f" % job.data.max_cores)


def displayJobInfo(job):
    """Displays the job's information in cueman format.
    @type  job: Job
    @param job: Job to display"""
    print "-"*60
    print "job: %s\n" % job.data.name
    print "%13s: %s" % ("start time", common.formatTime(job.data.start_time))
    if job.data.is_paused:
        print "%13s: %s" % ("state", "PAUSED")
    else:
        print "%13s: %s" % ("state", job.data.state)
    print "%13s: %s" % ("type", "N/A")
    print "%13s: %s" % ("architecture", "N/A")
    print "%13s: %s" % ("services", "N/A")
    print "%13s: %0.2f / %0.2f" % ("Min/Max cores", job.data.min_cores, job.data.max_cores)
    print ""
    print "%22s: %s" % ("total number of frames", job.data.job_stats.total_frames)
    print "%22s: %s" % ("done", job.data.job_stats.succeeded_frames)
    print "%22s: %s" % ("running", job.data.job_stats.running_frames)
    print "%22s: %s" % ("waiting (ready)", job.data.job_stats.waiting_frames)
    print "%22s: %s" % ("waiting (depend)", job.data.job_stats.depend_frames)
    print "%22s: %s" % ("failed", job.data.job_stats.deadFrames)

    print "%22s: %s\n" % ("total frame retries", "N/A")
    layers = job.getLayers()
    print "this is a cuerun3 job with %d layers\n" % len(layers)
    for layer in layers:
        print "%s  (%d frames, %d done)" % (layer.data.name, layer.data.job_stats.total_frames,
                                            layer.data.job_stats.succeeded_frames)
        print "   average frame time: %s" % "N/A"
        print "   average ram usage: %s" % "N/A"
        print "   tags: %s\n" % layer.data.tags


def displayFrames(frames):
    """Displays the supplied list of frames
    @type  frames: list<Frame>
    @param frames: List of frames to display"""
    header = "%-35s %-10s %-15s %-13s %-12s %-9s %5s %2s %2s" % \
             ("Frame", "Staus", "Host", "Start", "End", "Runtime", "Mem ", "R", " Exit")
    print header, "\n", "-" * len(header)

    for frame in frames:
        dependencies = ""

        startTime = common.formatTime(frame.data.start_time)
        stopTime = common.formatTime(frame.data.stop_time)

        if frame.data.start_time:
            duration = common.formatDuration(common.findDuration(frame.data.start_time,
                                                                 frame.data.stop_time))
        else:
            duration = ""

        memory = common.formatMem(frame.data.max_rss)
        exitStatus = frame.data.exit_status

        print "%-35s %-10s %-15s %-13s %-12s %-9s %4s %2s  %-4s %s" % (
            common.cutoff(frame.data.name, 35),
            frame.data.state,
            frame.data.last_resource,
            startTime,
            stopTime,
            duration,
            memory,
            frame.data.retry_count,
            exitStatus,
            dependencies)

    if len(frames) == 1000:
        print "Warning: Only showing first 1000 matches. See frame query options to " \
              "limit your results."
