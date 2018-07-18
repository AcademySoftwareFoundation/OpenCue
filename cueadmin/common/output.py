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
    format = "%-10s %-7s %-24s %-30s / %-30s %-12s %-12s "
    print format % ("Host","Cores", "Memory", "Job","Frame","Start","Runtime")
    for proc in procs:
        print format % (proc.data.name.split("/")[0],
                        "%0.2f" % proc.data.reservedCores,
                         "%s of %s (%0.2f%%)" % (common.formatMem(proc.data.usedMemory),
                                                common.formatMem(proc.data.reservedMemory),
                                                (proc.data.usedMemory / float(proc.data.reservedMemory) * 100)),
                        common.cutoff(proc.data.jobName,30),
                        common.cutoff(proc.data.frameName,30),
                        common.formatTime(proc.data.dispatchTime),
                        common.formatDuration(time.time() - proc.data.dispatchTime))


def displayHosts(hosts):
    """Displays the host information on one line each.
    @type  hosts: list<Host>
    @param hosts: Hosts to display information about"""
    now = int(time.time())
    format = "%-15s %-4s %-5s %-8s %-8s %-9s %-5s %-5s %-16s %-8s %-8s %-6s %-9s %-10s %-7s"
    print format % ("Host", "Load","NIMBY",
                    "freeMem", "freeSwap", "freeMcp",
                    "Cores", "Mem", "Idle", "Os", "Uptime", "State", "Locked", "Alloc","Thread")
    for host in sorted(hosts, key=lambda v:v.data.name):
        print format % (host.data.name, host.data.load,
                        host.data.nimbyEnabled,
                        common.formatMem(host.data.freeMemory),
                        common.formatMem(host.data.freeSwap),
                        common.formatMem(host.data.freeMcp),
                        host.data.cores,
                        common.formatMem(host.data.memory),
                        "[ %0.2f / %s ]" % (host.data.idleCores,
                                   common.formatMem(host.data.idleMemory)),
                        host.data.os,
                        common.formatLongDuration(int(time.time()) - host.data.bootTime),
                        host.data.state,
                        host.data.lockState,
                        host.data.allocName,
                        host.data.threadMode)

def displayShows(shows):
    """Displays information about a list of shows
    @type  objs: list<Show>
    @param objs: A list of show objects"""
    format = "%-8s %-6s %15s %15s %15s %15s"
    print format % ("Show", "Active", "ReservedCores", "RunningFrames", "PendingFrames", "PendingJobs")
    for show in shows:
        print format % (show.data.name,
                        show.data.active,
                        "%0.2f" % (show.stats.reservedCores),
                        show.stats.runningFrames,
                        show.stats.pendingFrames,
                        show.stats.pendingJobs)

def displayServices(services):
    """Displays an array of services.
    @type  objs: list<Service>
    @param objs: A list of Server objects"""
    format = "%-20s %-12s %-20s %-15s %-36s"
    print format % ("Name", "Can Thread", "Min Cores Units", "Min Memory", "Tags")
    for srv in services:
        print format % (srv.data.name,
                        srv.data.threadable,
                        srv.data.minCores,
                        "%s MB" % srv.data.minMemory,
                        " | ".join(srv.data.tags))

def displayAllocations(allocations):
    """Displays information about a list of allocations
    @type  objs: list<Allocation>
    @param objs: A list of allocation objects"""
    format = "%-25s %15s %8s  %8s  %8s %8s %8s %8s %-8s"
    print format % ("Name", "Tag", "Running", "Avail", "Cores",  "Hosts", "Locked", "Down", "Billable")
    for alloc in sorted(allocations, key=lambda v:v.data.facility):
        print format % (alloc.data.name,
                        alloc.data.tag,
                        "%0.2f" % alloc.stats.runningCores,
                        "%0.2f" % alloc.stats.availableCores,
                        alloc.stats.cores,
                        alloc.stats.hosts,
                        alloc.stats.lockedHosts,
                        alloc.stats.downHosts,
                        alloc.data.billable)

def displaySubscriptions(subscriptions, show):
    """Displays information about a list of subscriptions
    @type  objs: list<Subscription>
    @param objs: A list of subscription objects"""
    print "Subscriptions for %s" % show
    format = "%-30s %-12s %6s %8s %8s %8s"
    print format % ("Allocation", "Show", "Size", "Burst", "Run", "Used")
    for s in subscriptions:
        if s.data.size:
            perc = (s.data.reservedCores / s.data.size) * 100.0
        else:
            perc = (s.data.reservedCores * 100.0)

        print format % (s.data.allocationName,
                        s.data.showName,
                        s.data.size,
                        s.data.burst,
                        "%0.2f" % s.data.reservedCores,
                        "%0.2f%%" % perc)

    print

def displayDepend(depend):
        print "-"
        print "Unique ID: %s" % Cue3.id(depend)
        print "Type: %s" % depend.data.type
        print "Internal: %s" % depend.data.target
        print "Active: %s" % depend.data.active
        print "AnyFrame: %s" % depend.data.anyFrame

        print "Depending Job: %s" % depend.data.dependErJob
        if depend.data.dependErLayer:
           print "Depending Layer: %s" % depend.data.dependErLayer
        if depend.data.dependErFrame:
           print "Depending Frame: %s" % depend.data.dependErFrame
        if depend.data.dependOnJob != depend.data.dependErJob:
            print "Depend On Job: %s" % depend.data.dependOnJob
        if depend.data.dependOnLayer:
            print "Depend On Layer: %s" % depend.data.dependOnLayer
        if depend.data.dependOnFrame:
           print "Depending Frame: %s" % depend.data.dependOnFrame

def displayDepends(depends, active_only=False):
    for depend in depends:
        if (depend.data.active and active_only) or not active_only:
            displayDepend(depend)

def displayGroups(show):
    print "Groups for %s" % Cue3.rep(show)
    format = "%-32s %-12s %8s %8s %8s %8s %8s %8s %8s %6s"
    print format % ("Name","Dept","DefPri","DefMin","DefMax","MaxC","MinC","Booked","Cores","Jobs")

    def enabled(v):
        if v < 0:
            return "off"
        return v

    def printGroup(group):
        name = "|%s+%-20s" % ("".join(["  " for i in range(0,int(group.data.level))]),group.data.name)
        print format % (name,
                        group.data.department,
                        enabled(group.data.defaultJobPriority),
                        enabled(group.data.defaultJobMinCores),
                        enabled(group.data.defaultJobMaxCores),
                        enabled(group.data.maxCores),
                        group.data.minCores,
                        group.stats.runningFrames,
                        "%0.2f" % group.stats.reservedCores,
                        group.stats.pendingJobs)
    def printGroups(item):
        printGroup(item)
        for group in item.proxy.getGroups():
            printGroups(group)
    printGroups(show.proxy.getRootGroup())

def displayFilters(show, filters):
    print "Filters for %s" % show
    print "%-32s %-10s %-5s" % ("Name","Type","Enabled")
    for filter in filters:
        print  "%-32s %-10s %-5s" % (filter.data.name, filter.data.type, filter.data.enabled)

def displayMatchers(matchers):
    print "%-6s %-16s %-16s %-32s" % ("Order","Subject","Type","Query")
    print "-------------------------------------------------------"
    order = 0
    for matcher in matchers:
        order = order + 1
        print "%06d %-16s %-16s %-32s" % (order,matcher.data.subject, matcher.data.type, matcher.data.input)
    print "------------------------------------------------------"

def displayActions(actions):
    print "%-6s %-24s %-16s" % ("Order","Type","Value")
    num = 0
    for action in actions:
        num+=1
        print "%06d %-24s %-16s" % (num, action.data.type, common.actionUtil.getValue(action))

def displayFilter(filter):
    print "Filter: "
    print "Name: %s " % filter.data.name
    print "Type: %s " % filter.data.type
    print "Enabled: %s " % filter.data.enabled
    print "Order: %d " % filter.data.order
    print
    displayMatchers(filter.proxy.getMatchers())
    print
    print "Actions: "
    print "-------------------------------------------------------"
    displayActions(filter.proxy.getActions())

def displayStrings(strings):
    """Print all of the strings in a list.
    @type  objs: list<String>
    @param objs: A list of strings"""
    for string in strings:
        print string

def displayNames(items):
    """Displays the .name of every object in the list.
    @type  objs: list<>
    @param objs: All objects must have a .name parameter"""
    for item in items:
        print Cue3.rep(item)

def displayLayers(job, layers):
    """Displays information about the layers in the list.
    @type  objs: list<Layer>
    @param objs: List of layers"""
    print
    print "Job: %s " % (job.data.name)
    print "--"
    for layer in layers:

        print "Layer - %s (type: %s) - Tagged: %s - Threadable: %s" % (layer.data.name,
                                                                       layer.data.type,
                                                                       layer.data.tags,
                                                                       layer.data.isThreadable)
        print "Minimum Resources - Cores: %0.2f  Memory: %s" % (layer.data.minCores,
                                                                common.formatMem(layer.data.minMemory))
        print "Frames - Total: %3d  Running: %3d  Pending: %3d " % (layer.stats.totalFrames,
                                                                    layer.stats.runningFrames,
                                                                    layer.stats.pendingFrames)
        print "--"



def displayJobs(jobs):
    """Displays job priority information.
    @type  objs: list<>
    @param objs: All objects must have a .name parameter"""
    format = "%-56s %-15s %5s %7s %8s %5s %8s %8s"
    print format % ("Job","Group","Booked","Cores","Wait","Pri","MinCores","MaxCores")
    for job in jobs:
        p = ""
        if job.data.isPaused:
            p=" [paused]"
        name = job.data.name + p
        print format % (common.cutoff(name,52),
                        common.cutoff(job.data.group,15),
                        job.stats.runningFrames,
                        "%0.2f" % (job.stats.reservedCores),
                        job.stats.waitingFrames,
                        job.data.priority,
                        "%0.2f" % (job.data.minCores),
                        "%0.2f" % (job.data.maxCores))

def displayJobInfo(job):
    """Displays the job's information in cueman format.
    @type  jobObj: Job
    @param jobObj: Job to display"""
    print "-"*60
    print "job: %s\n" % job.data.name
    print "%13s: %s" % ("start time", common.formatTime(job.data.startTime))
    if job.data.isPaused:
        print "%13s: %s" % ("state", "PAUSED")
    else:
        print "%13s: %s" % ("state", job.data.state)
    print "%13s: %s" % ("type", "N/A")
    print "%13s: %s" % ("architecture", "N/A")
    print "%13s: %s" % ("services", "N/A")
    print "%13s: %0.2f / %0.2f" % ("Min/Max cores", job.data.minCores, job.data.maxCores)
    print ""
    print "%22s: %s" % ("total number of frames", job.stats.totalFrames)
    print "%22s: %s" % ("done", job.stats.succeededFrames)
    print "%22s: %s" % ("running", job.stats.runningFrames)
    print "%22s: %s" % ("waiting (ready)", job.stats.waitingFrames)
    print "%22s: %s" % ("waiting (depend)", job.stats.dependFrames)
    print "%22s: %s" % ("failed", job.stats.deadFrames)

    print "%22s: %s\n" % ("total frame retries", "N/A")
    layers = job.proxy.getLayers()
    print "this is a cuerun3 job with %d layers\n" % len(layers)
    for layer in layers:
        print "%s  (%d frames, %d done)" % (layer.data.name, layer.stats.totalFrames, layer.stats.succeededFrames)
        print "   average frame time: %s" % "N/A"
        print "   average ram usage: %s" % "N/A"
        print "   tags: %s\n" % layer.data.tags

def displayFrames(frames):
    """Displays the supplied list of frames
    @type  frames: list<Frame>
    @param frames: List of frames to display"""
    header = "%-35s %-10s %-15s %-13s %-12s %-9s %5s %2s %2s" % \
             ("Frame","Staus","Host","Start","End","Runtime","Mem ","R"," Exit")
    print header, "\n", "-" * len(header)

    for frame in frames:
        dependencies = ""

        startTime = common.formatTime(frame.data.startTime)
        stopTime = common.formatTime(frame.data.stopTime)

        if frame.data.startTime:
            duration = common.formatDuration(common.findDuration(frame.data.startTime,
                                                             frame.data.stopTime))
        else:
            duration = ""

        memory = common.formatMem(frame.data.maxRss)
        exit = frame.data.exitStatus

        print "%-35s %-10s %-15s %-13s %-12s %-9s %4s %2s  %-4s %s" % \
               (common.cutoff(frame.data.name,35), frame.data.state, frame.data.lastResource,
                startTime,
                stopTime,
                duration,
                memory, frame.data.retryCount, exit, dependencies)

    if len(frames) == 1000:
        print "Warning: Only showing first 1000 matches. See frame query options to \
        limit your results."
