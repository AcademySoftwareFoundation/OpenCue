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
import sys

import opencue

import common


logger = logging.getLogger("opencue.tools.cueadmin")

OS_LIST = []


def main():

    parser = common.getCommonParser(description="CueAdmin OpenCue Administrator Tool",
                                    formatter_class=common.argparse.RawDescriptionHelpFormatter,
                                    conflict_handler='resolve')
    query = common.setCommonQueryArgs(parser)

    query.add_argument("-lp", "-lap", action="store", nargs="*",
                       metavar="[SHOW ...] [-host HOST ...] [-alloc ...] [-job JOB ...] "
                               "[-memory ...] [-limit ...]",
                       help="List running procs.  Optionally filter by show, show, memory, alloc. "
                            "Use -limit to limit the results to N procs.")

    query.add_argument("-ll", "-lal", action="store", nargs="*",
                       metavar="[SHOW ...] [-host HOST ...] [-alloc ...] [-job JOB ...] "
                               "[-memory ...] [-limit ...]",
                       help="List running frame log paths.  Optionally filter by show, show, memory"
                            ", alloc. Use -limit to limit the results to N logs.")

    query.add_argument("-lh", action=common.QueryAction, nargs="*",
                       metavar="[SUBSTR ...] [-state STATE] [-alloc ALLOC]",
                       help="List hosts with optional name substring match.")

    query.add_argument("-lv", action="store", nargs="*", metavar="[SHOW]",
                       help="List default services.")

    query.add_argument("-lba", action="store", metavar="ALLOC",
                       help="List all subscriptions to a specified allocation.")

    query.add_argument("-state", nargs="+", metavar="STATE", action="store", default=[],
                       choices=["up", "down", "repair", "Up", "Down", "Repair"],
                       help="Filter host search by hardware state, up or down.")
    #
    # Filter
    #
    filter_grp = parser.add_argument_group("Filter Options")
    filter_grp.add_argument("-job", nargs="+", metavar="JOB", action="store", default=[],
                            help="Filter proc or log search by job")

    filter_grp.add_argument("-alloc", nargs="+", metavar="ALLOC", action="store", default=[],
                            help="Filter host or proc search by allocation")

    filter_grp.add_argument("-memory", action="store",
                            help="Filters a list of procs by the amount of reserved memory. "
                                 "Memory can be specified in one of 3 ways. As a range, "
                                 "<min>-<max>.  Less than, lt<value>.  Greater than, gt<value>. "
                                 "Values should be specified in GB.")

    filter_grp.add_argument("-duration", action="store",
                            help="Show procs that have been running longer than the specified "
                                 "number of hours or within a specific time frame.  Ex. -time 1.2 "
                                 "or  -time 3.5-4.5.  Waiting frames are automatically filtered "
                                 "out.")

    filter_grp.add_argument("-limit", action="store", default=0,
                            help="Limit the result of a proc search to N rows")
    #
    # Show
    #
    show = parser.add_argument_group("Show Options")
    show.add_argument("-create-show", action="store", metavar="SHOW",
                      help="create a new show")

    show.add_argument("-delete-show", action="store", metavar="SHOW",
                      help="delete specified show")

    show.add_argument("-disable-show", action="store", metavar="SHOW",
                      help="Disable the specified show")

    show.add_argument("-enable-show", action="store", metavar="SHOW",
                      help="Enable the specified show")

    show.add_argument("-dispatching", action="store", nargs=2, metavar="SHOW ON|OFF",
                      help="Enables frame dispatching on the specified show.")

    show.add_argument("-booking", action="store", nargs=2, metavar="SHOW ON|OFF",
                      help="Booking is new proc assignment.  If booking is disabled "
                           "procs will continue to run on new jobs but no new jobs will "
                           "be booked.")

    show.add_argument("-default-min-cores", action="store", nargs=2, metavar="SHOW CORES",
                      help="The default min core value for all jobs before "
                           "any min core filers are applied.")

    show.add_argument("-default-max-cores", action="store", nargs=2, metavar="SHOW CORES",
                      help="The default min core value for all jobs before "
                           "any max core filters are applied.")
    #
    # Allocation
    #
    alloc = parser.add_argument_group("Allocation Options")
    alloc.add_argument("-create-alloc", action="store", nargs=3, metavar="FACILITY ALLOC TAG",
                       help="Create a new allocation.")
    alloc.add_argument("-delete-alloc", action="store", metavar="NAME",
                       help="Delete an allocation.  It must be empty.")
    alloc.add_argument("-rename-alloc", action="store", nargs=2, metavar="OLD NEW",
                       help="Rename allocation. New name must not contain facility prefix.")
    alloc.add_argument("-transfer", action="store", nargs=2, metavar="OLD NEW",
                       help="Move all hosts from src alloc to dest alloc")
    alloc.add_argument("-tag-alloc", action="store", nargs=2, metavar="ALLOC TAG",
                       help="Tag allocation.")
    #
    # Subscription
    #
    sub = parser.add_argument_group("Subscription Options")

    sub.add_argument("-create-sub", action="store", nargs=4,
                     help="Create new subcription.", metavar="SHOW ALLOC SIZE BURST")
    sub.add_argument("-delete-sub", action="store", nargs=2, metavar="SHOW ALLOC",
                     help="Delete subscription")
    sub.add_argument("-size", action="store", nargs=3, metavar="SHOW ALLOC SIZE",
                     help="Set the guaranteed number of cores.")
    sub.add_argument("-burst", action="store", nargs=3, metavar="SHOW ALLOC BURST",
                     help="Set the number of burst cores.  Use the percent sign to indicate a "
                          "percentage of the subscription size instead of a hard size.")
    #
    # Host
    #
    host = parser.add_argument_group("Host Options")
    host.add_argument("-host", action="store", nargs="+", metavar="HOSTNAME",
                      help="Specify the host names to operate on")
    host.add_argument("-hostmatch", "-hm", action="store", nargs="+", metavar="SUBSTR",
                      help="Specify a list of substring matches to match groups of hosts.")
    host.add_argument("-lock", action="store_true", help="lock hosts")
    host.add_argument("-unlock", action="store_true", help="unlock hosts")
    host.add_argument("-move", action="store", metavar="ALLOC",
                      help="move hosts into a new allocation")
    host.add_argument("-delete-host", action="store_true", help="delete hosts")
    host.add_argument("-safe-reboot", action="store_true", help="lock and reboot hosts when idle")
    host.add_argument("-repair", action="store_true", help="Sets hosts into the repair state.")
    host.add_argument("-fixed", action="store_true", help="Sets hosts into Up state.")
    host.add_argument("-thread", action="store", help="Set the host's thread mode.",
                      choices=[mode.lower() for mode in opencue.api.host_pb2.ThreadMode.keys()])
    host.add_argument("-os", action="store", help="Set the host's operating system.",
                      choices=OS_LIST)

    try:
        args = parser.parse_args()
    except common.argparse.ArgumentError, exc:
        print >>sys.stderr, "Could not parse arguments, check command line flags."
        raise exc

    try:
        common.handleCommonArgs(args)
        if args.unit_test:
            runTests(parser)
        else:
            common.handleArgs(args)
    except Exception, e:
        common.handleParserException(args, e)


def runTests(parser):
    import tests
    tests.run(parser)


if __name__ == '__main__':
    main()