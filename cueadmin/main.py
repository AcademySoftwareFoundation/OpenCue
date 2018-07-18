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


import logging
import common

Cue3 = common.Cue3

logger = logging.getLogger("cue3.tools.cueadmin")

OS_LIST = []

def main(argv):

    parser = common.getCommonParser(description="Cueadmin Cue3 Administrator Tool",
                                    formatter_class=common.argparse.RawDescriptionHelpFormatter,
                                    conflict_handler='resolve')
    query = common.setCommonQueryArgs(parser)

    query.add_argument("-lp","-lap",action="store", nargs="*",
                       metavar="[SHOW ...] [-host HOST ...] [-alloc ...] [-job JOB ...] [-memory ...] [-limit ...]",
                       help="List running procs.  Optionally filter by show, show, memory, alloc. Use \
                       -limit to limit the results to N procs.")

    query.add_argument("-ll","-lal",action="store", nargs="*",
                       metavar="[SHOW ...] [-host HOST ...] [-alloc ...] [-job JOB ...] [-memory ...] [-limit ...]",
                       help="List running frame log paths.  Optionally filter by show, show, memory, alloc. Use \
                       -limit to limit the results to N logs.")

    query.add_argument("-lh",action=common.QueryAction,nargs="*",metavar="[SUBSTR ...] [-state STATE] [-alloc ALLOC]",
                       help="List hosts with optional name substring match.")

    query.add_argument("-lv", action="store", nargs="*", metavar="[SHOW]",
                       help="List default services.")

    query.add_argument("-lba",action="store", metavar="ALLOC",
                       help="List all subscriptions to a specified allocation.")

    query.add_argument("-state", nargs="+",metavar="STATE", action="store",default=[],
                       choices=["up","down","repair","Up","Down","Repair"],
                       help="Filter host search by hardware state, up or down.")


    filter = parser.add_argument_group("Filter Options")

    filter.add_argument("-job", nargs="+",metavar="JOB", action="store",default=[],
                       help="Filter proc or log search by job")

    filter.add_argument("-alloc", nargs="+",metavar="ALLOC", action="store",default=[],
                       help="Filter host or proc search by allocation")

    filter.add_argument("-memory", action="store",
                        help="Filters a list of procs by the amount of reserved memory. \
                        Memory can be specified in one of 3 ways. As a range, <min>-<max>.  Less than, \
                        lt<value>.  Greater than, gt<value>. Values should be specified in GB.")

    filter.add_argument("-duration", action="store",
                        help="Show procs that have been running longer than the specified \
                        number of hours or within a specific time frame.  Ex. -time 1.2 or \
                        -time 3.5-4.5.  Waiting frames are automatically filtered out.")

    filter.add_argument("-limit", action="store", default=0,
                        help="Limit the result of a proc search to N rows")
    #
    # Show
    #
    show = parser.add_argument_group("Show Options")
    show.add_argument("-create-show",action="store", metavar="SHOW",
                      help="create a new show")

    show.add_argument("-delete-show",action="store", metavar="SHOW",
                      help="delete specified show")

    show.add_argument("-disable-show",action="store", metavar="SHOW",
                      help="Disable the specified show")

    show.add_argument("-enable-show",action="store", metavar="SHOW",
                      help="Enable the specified show")

    show.add_argument("-dispatching",action="store", nargs=2, metavar="SHOW ON|OFF",
                      help="Enables frame dispatching on the specified show.")

    show.add_argument("-booking",action="store", nargs=2, metavar="SHOW ON|OFF",
                      help="Booking is new proc assignment.  If booking is disabled \
                      procs will continue to run on new jobs but no new jobs will \
                      be booked.")

    show.add_argument("-default-min-cores",action="store", nargs=2, metavar="SHOW CORES",
                      help="The default min core value for all jobs before \
                      any min core filers are applied.")

    show.add_argument("-default-max-cores",action="store", nargs=2, metavar="SHOW CORES",
                      help="The default min core value for all jobs before \
                      any max core filters are applied.")
    #
    # Allocation
    #
    alloc = parser.add_argument_group("Allocation Options")
    alloc.add_argument("-create-alloc",action="store", nargs=3, metavar="FACILITY ALLOC TAG",
                       help="Create a new allocation.")
    alloc.add_argument("-delete-alloc",action="store", metavar="NAME",
                       help="Delete an allocation.  It must be empty.")
    alloc.add_argument("-rename-alloc",action="store",nargs=2, metavar="OLD NEW",
                       help="Rename allocation. New name must not contain facility prefix.")
    alloc.add_argument("-transfer",action="store",nargs=2, metavar="OLD NEW",
                       help="Move all hosts from src alloc to dest alloc")
    alloc.add_argument("-tag-alloc",action="store", nargs=2, metavar="ALLOC TAG",
                       help="Tag allocation.")
    #
    # Subscription
    #
    sub = parser.add_argument_group("Subscription Options")

    sub.add_argument("-create-sub",action="store", nargs=4,
                     help="Create new subcription.",metavar="SHOW ALLOC SIZE BURST")
    sub.add_argument("-delete-sub", action="store", nargs=2, metavar="SHOW ALLOC",
                     help="Delete subscription")
    sub.add_argument("-size", action="store", nargs=3, metavar="SHOW ALLOC SIZE",
                     help="Set the gauranteed number of cores.")
    sub.add_argument("-burst", action="store", nargs=3, metavar="SHOW ALLOC BURST",
                     help="Set the number of burst cores.  Use the percent sign to indicate a \
                     percentage of the subscription size instead of a hard size.")
    #
    # Host
    #
    host = parser.add_argument_group("Host Options")
    host.add_argument("-host",action="store", nargs="+",metavar="HOSTNAME",
                     help="Specify the host names to operate on")
    host.add_argument("-hostmatch","-hm",action="store", nargs="+", metavar="SUBSTR",
                     help="Specify a list of substring matches to match groups of hosts.")
    host.add_argument("-lock", action="store_true", help="lock hosts")
    host.add_argument("-unlock", action="store_true", help="unlock hosts")
    host.add_argument("-move", action="store", metavar="ALLOC",
                      help="move hosts into a new allocation")
    host.add_argument("-delete-host",action="store_true", help="delete hosts")
    host.add_argument("-safe-reboot",action="store_true", help="lock and reboot hosts when idle")
    host.add_argument("-repair", action="store_true", help="Sets hosts into the repair state.");
    host.add_argument("-fixed", action="store_true", help="Sets hosts into Up state.");
    host.add_argument("-thread", action="store", help="Set the host's thread mode.",
                      choices=[mode.lower() for mode in dir(Cue3.ThreadMode) if not mode.startswith('__')])
    host.add_argument("-os", action="store", help="Set the host's operating system.",
                      choices=OS_LIST)

    try:
        args = parser.parse_args()
        common.handleCommonArgs(args)
        if args.unit_test:
            runTests(parser)
        else:
            handleArgs(args)
    except Exception,e:
        common.handleParserException(args, e)

def runTests(parser):
    import tests
    tests.run(parser)

def handleArgs(args):

    #
    # Query
    #
    if isinstance(args.lp,list) or isinstance(args.ll,list):
        if isinstance(args.ll,list):
            args.lp = args.ll
        if not args.host:
            args.host = []

        procs = Cue3.ProcSearch().byOptions(show=args.lp,
                                            host=args.host,
                                            limit=args.limit,
                                            alloc=args.alloc,
                                            job=args.job,
                                            memory=common.handleIntCriterion(args.memory,
                                                                             common.Convert.gigsToKB),
                                            duration=common.handleIntCriterion(args.duration,
                                                                               common.Convert.hoursToSeconds))
        if isinstance(args.ll,list):
            print "\n".join([l.data.logPath for l in procs])
        else:
            common.output.displayProcs(procs)
        return

    elif args.lh:
        states = [common.Convert.strToHardwareState(s) for s in args.state]
        common.output.displayHosts(Cue3.getHosts(match=args.query,
                                                 state=states,alloc=args.alloc))
        return


    elif args.lba:
        common.output.displaySubscriptions( \
            Cue3.findAllocation(args.lba).proxy.getSubscriptions(),"All Shows")
        return

    elif isinstance(args.lv, (list,)):
        if args.lv:
            common.output.displayServices(Cue3.findShow(args.lv[0]).proxy.getServiceOverrides())
        else:
            common.output.displayServices(Cue3.getDefaultServices())
        return
    #
    # Gather hosts if -host - hostmatch was specified
    #
    host_error_msg = "No valid hosts selected, see the -host/-hostmatch options"
    hosts = None
    if args.host or args.hostmatch:
        hosts = common.resolveHostNames(args.host,args.hostmatch)

    #
    # Allocations
    #
    if args.create_alloc:
        fac, name, tag = args.create_alloc
        common.confirm("Create new allocation %s.%s, with tag %s" % (fac, name, tag),
                args.force, createAllocation, fac, name, tag)

    elif args.delete_alloc:
        common.confirm("Delete allocation %s" % args.delete_alloc,
                args.force, Cue3.findAllocation(args.delete_alloc).proxy.delete)

    elif args.rename_alloc:
        old, new = args.rename_alloc
        try:
            new = new.split(".", 2)[1]
        except:
            msg = "Allocation names must be in the form 'facility.name'"
            raise Exception(msg)

        common.confirm("Rename allocation from %s to %s" % (old,new),
                args.force, Cue3.findAllocation(old).proxy.setName, new)

    elif args.transfer:
        src = Cue3.findAllocation(args.transfer[0])
        dst = Cue3.findAllocation(args.transfer[1])
        common.confirm("Transfer hosts from from %s to %s" % (src.data.name, dst.data.name),
                args.force, common.AllocUtil.transferHosts, src, dst)

    elif args.tag_alloc:
        alloc, tag = args.tag_alloc
        common.confirm("Re-tag allocation %s with %s" % (alloc, tag),
                args.force, Cue3.findAllocation(alloc).proxy.setTag,tag)
    #
    # Shows
    #
    elif args.create_show:
        common.confirm("Create new show %s" % args.create_show,
                       args.force, Cue3.createShow, args.create_show)
    elif args.delete_show:
        common.confirm("Delete show %s" % args.delete_show,
                       args.force, Cue3.findShow(args.delete_show).proxy.delete)

    elif args.disable_show:
        common.confirm("Disable show %s" % args.disable_show,
                       args.force, Cue3.findShow(args.disable_show).proxy.setActive, False);

    elif args.enable_show:
        common.confirm("Enable show %s" % args.enable_show,
                       args.force, Cue3.findShow(args.enable_show).proxy.setActive, True);

    elif args.dispatching:
        show = Cue3.findShow(args.dispatching[0])
        enabled = common.Convert.stringToBoolean(args.dispatching[1])
        if not enabled:
            common.confirm("Disable dispatching on %s" % Cue3.rep(show),
                           args.force, show.proxy.enableDispatching, enabled)
        else:
             show.proxy.enableDispatching(True)

    elif args.booking:
        show = Cue3.findShow(args.booking[0])
        enabled = common.Convert.stringToBoolean(args.booking[1])
        if not enabled:
            common.confirm("Disable booking on %s" % Cue3.rep(show),
                           args.force, show.proxy.enableBooking, False)
        else:
             show.proxy.enableBooking(True)

    elif args.default_min_cores:
        common.confirm("Set the default min cores to: %s"  %
                       args.default_min_cores[1], args.force,
                       Cue3.findShow(args.default_min_cores[0]).proxy.setDefaultMinCores,
                       float(int(args.default_min_cores[1])))

    elif args.default_max_cores:
        common.confirm("Set the default max cores to: %s" %
                       args.default_max_cores[1], args.force,
                       Cue3.findShow(args.default_max_cores[0]).proxy.setDefaultMaxCores,
                       float(int(args.default_max_cores[1])))
    #
    # Hosts are handled a bit differently than the rest
    # of the entities. To specify a host or hosts the user
    # must use the -host or -hostmatch flags.  This is so you can
    # specify more than one host in an operation. For example,
    # -hostmatch vrack -lock would locl all vrack hosts.
    #
    elif args.lock:
        if not hosts:
            raise ValueError(host_error_msg)
        for host in hosts:
            logger.debug("locking host: %s" % Cue3.rep(host))
            host.proxy.lock()

    elif args.unlock:
        if not hosts:
            raise ValueError(host_error_msg)
        for host in hosts:
            logger.debug("unlocking host: %s" % Cue3.rep(host))
            host.proxy.unlock()

    elif args.move:
        if not hosts:
            raise ValueError(host_error_msg)
        def moveHosts(hosts, dst):
            for host in hosts:
                logger.debug("moving %s to %s" % (Cue3.rep(host), Cue3.rep(dst)))
                host.proxy.setAllocation(dst.proxy)
        common.confirm("Move %d hosts to %s" % (len(hosts), args.move),
                       args.force, moveHosts, hosts, Cue3.findAllocation(args.move))

    # No Test coverage, takes up to a minute for
    # a host to report back in.
    elif args.delete_host:
        if not hosts:
            raise ValueError(host_error_msg)
        def deleteHosts(hosts):
            for host in hosts:
                logger.debug("deleting host: %s" % host)
                try:
                    host.proxy.delete()
                except Exception, e:
                    print "Failed to delete %s due to %s" % (host, e)
        common.confirm("Delete %s hosts" % len(hosts),
                       args.force, deleteHosts, hosts)

    # No Test coverage, sometimes the machines don't come
    # back up.
    elif args.safe_reboot:
        if not hosts:
            raise ValueError(host_error_msg)
        def safeReboot(hosts):
            for host in hosts:
                logger.debug("locking host and rebooting when idle %s" % Cue3.rep(host))
                host.proxy.rebootWhenIdle()
        common.confirm("Lock and reboot %d hosts when idle" % len(hosts),
                       args.force, safeReboot, hosts)

    elif args.thread:
        if not hosts:
            raise ValueError(host_error_msg)
        def setThreadMode(hosts, mode):
            for host in hosts:
                logger.debug("setting host %s to thread mode %s" % (host.data.name, mode))
                host.proxy.setThreadMode(common.Convert.strToThreadMode(mode))
        common.confirm("Set %d hosts to thread mode %s" % (len(hosts),args.thread), args.force,
                       setThreadMode, hosts, args.thread)

    elif args.os:
        if not hosts:
            raise ValueError(host_error_msg)
        def setHostOs(hosts, os):
            for host in hosts:
                logger.debug("setting host %s to OS %s" % (host.data.name, os))
                host.proxy.setOs(os)
        common.confirm("Set %d hosts to OS %s" % (len(hosts), args.os), args.force,
                       setHostOs, hosts, args.os)
    elif args.repair:
        if not hosts:
            raise ValueError(host_error_msg)
        def setRepairState(hosts):
            for host in hosts:
                logger.debug("setting host into the repair state %s" % host.data.name)
                host.proxy.setHardwareState(Cue3.HardwareState.Repair)
        common.confirm("Set %d hosts into the Repair state?" % len(hosts),
                       args.force, setRepairState, hosts)

    elif args.fixed:
        if not hosts:
            raise ValueError(host_error_msg)
        def setUpState(hosts):
            for host in hosts:
                logger.debug("setting host into the repair state %s" % host.data.name)
                host.proxy.setHardwareState(Cue3.HardwareState.Up)
        common.confirm("Set %d hosts into the Up state?" % len(hosts),
                       args.force, setUpState, hosts)

    elif args.create_sub:
        show = Cue3.findShow(args.create_sub[0]);
        alloc = Cue3.findAllocation(args.create_sub[1]);
        common.confirm("Create subscripton for %s on %s" % (Cue3.rep(show), Cue3.rep(alloc)),
                       args.force, show.proxy.createSubscription,
                       alloc.proxy, float(args.create_sub[2]), float(args.create_sub[3]))
    elif args.delete_sub:
        sub_name = "%s.%s" % (args.delete_sub[1], args.delete_sub[0])
        common.confirm("Delete %s's subscription to %s" %
                       (args.delete_sub[0], args.delete_sub[1]),
                       args.force, Cue3.findSubscription(sub_name).proxy.delete)
    elif args.size:
        sub_name = "%s.%s" % (args.size[1], args.size[0])
        Cue3.findSubscription(sub_name).proxy.setSize(float(args.size[2]))
    elif args.burst:
        sub_name = "%s.%s" % (args.burst[1], args.burst[0])
        sub = Cue3.findSubscription(sub_name)
        burst = args.burst[2]
        if burst.find("%") !=-1:
            burst = int(sub.data.size + (sub.data.size * (int(burst[0:-1]) / 100.0)))
        sub.proxy.setBurst(float(burst))
    else:
        common.handleCommonQueryArgs(args)

def createAllocation(fac, name, tag):
    """Create a new allocation with the given name and tag."""
    facprx = Cue3.getFacility(fac).proxy
    alloc = facprx.createAllocation(name, tag);
    print "Created allocation: %s" % alloc.data.name

def displayJobs(jobs):
    """Displays job priority information.
    @type  objs: list<>
    @param objs: All objects must have a .name parameter"""
    format = "%-48s %-15s %5s %7s %8s %5s %8s %8s"
    print format % ("Job","Group","Run","Cores","Wait","Pri","MinCores","MaxCores")
    for job in jobs:
        print format % (job.data.name,
                        job.data.group,
                        job.stats.runningFrames,
                        job.stats.reservedCores,
                        job.stats.waitingFrames,
                        job.data.priority,
                        job.data.minCores,
                        job.data.maxCores)
