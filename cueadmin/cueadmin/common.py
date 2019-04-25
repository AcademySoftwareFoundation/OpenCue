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


import argparse
import logging
import sys
import time
import traceback

import opencue

import output
import util


class __NullHandler(logging.Handler):
    def emit(self, record):
        pass


logger = logging.getLogger("opencue.tools.cueadmin")
logger.addHandler(__NullHandler())

__ALL__ = ["testServer",
           "handleCommonArgs",
           "handleParserException",
           "handFloatCriterion",
           "getCommonParser",
           "setCommonQueryArgs",
           "handleCommonQueryArgs",
           "resolveJobNames",
           "resolveHostNames",
           "resolveShowNames",
           "confirm",
           "formatTime",
           "formatDuration",
           "formatLongDuration",
           "formatMem",
           "cutoff",
           "ActionUtil",
           "DependUtil",
           "Convert",
           "AllocUtil"]

EPILOG = '\n\n'


def handleCommonArgs(args):
    logger.debug(args)
    if args.verbose:
        util.enableDebugLogging()
    if args.server:
        logger.debug("setting opencue host servers to %s" % args.server)
        opencue.Cuebot.setHosts(args.server)
    if args.facility:
        logger.debug("setting facility to %s" % args.facility)
        opencue.Cuebot.setFacility(args.facility)
    if args.force:
        pass


def handleParserException(args, e):
    try:
        if args.verbose:
            traceback.print_exc(file=sys.stderr)
        print EPILOG
        raise e
    except ValueError, ex:
            print >>sys.stderr, "Error: %s. Try the -verbose or -h flags for more info." % ex
    except Exception, ex:
        print >> sys.stderr, "Error: %s." % ex


def getParser():

    parser = getCommonParser(description="CueAdmin OpenCue Administrator Tool",
                                    formatter_class=argparse.RawDescriptionHelpFormatter,
                                    conflict_handler='resolve')
    query = setCommonQueryArgs(parser)

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

    query.add_argument("-lh", action=QueryAction, nargs="*",
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
                      help="The default max core value for all jobs before "
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

    return parser


def getCommonParser(**options):
    parser = argparse.ArgumentParser(**options)

    if parser.epilog:
        parser.epilog += EPILOG
    else:
        parser.epilog = EPILOG

    general = parser.add_argument_group("General Options")
    general.add_argument("-server", action='store', nargs="+", metavar='HOSTNAME',
                         help='Specify cuebot addres(s).')
    general.add_argument("-facility", action='store', metavar='CODE',
                         help='Specify the facility code.')
    general.add_argument("-verbose", "-v", action='store_true',
                         help='Turn on verbose logging.')
    general.add_argument("-force", action='store_true',
                         help='Force operations that usually require confirmation.')
    return parser


class QueryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if option_string == '-lh':
            namespace.lh = True
            namespace.query = values
        elif option_string in ('-lj', '-laj'):
            namespace.lj = True
            namespace.query = values
        elif option_string == '-lji':
            namespace.lji = True
            namespace.query = values


def setCommonQueryArgs(parser):
    query = parser.add_argument_group("Query Options")
    query.add_argument("-lj", "-laj", action=QueryAction, nargs="*", metavar="SUBSTR",
                       help="List jobs with optional name substring match.")
    query.add_argument("-lji", action=QueryAction, nargs="*", metavar="SUBSTR",
                       help="List job info with optional name substring match.")
    query.add_argument("-lh", action=QueryAction, nargs="*", metavar="SUBSTR",
                       help="List hosts with optional name substring match.")
    query.add_argument("-ls", action="store_true", help="List shows.")
    query.add_argument("-la", action="store_true", help="List allocations.")
    query.add_argument("-lb", action="store", nargs="+", help="List subscriptions.", metavar="SHOW")
    query.add_argument("-query", "-q", nargs="+", action="store", default=[],
                       help=argparse.SUPPRESS)
    return query


def handleCommonQueryArgs(args):
    if args.lh:
        output.displayHosts(opencue.search.HostSearch.byMatch(args.query))
        return True
    elif args.lj:
        for job in opencue.search.JobSearch.byMatch(args.query):
            print job.data.name
        return True
    elif args.lji:
        output.displayJobs(opencue.search.JobSearch.byMatch(args.query))
        return True
    elif args.la:
        output.displayAllocations(opencue.api.getAllocations())
        return True
    elif args.lb:
        for show in resolveShowNames(args.lb):
            output.displaySubscriptions(show.getSubscriptions(), show.data.name)
        return True
    elif args.ls:
        output.displayShows(opencue.api.getShows())
        return True
    return False


def handleFloatCriterion(mixed, convert=None):
    """handleFloatCriterion
        returns the proper subclass of FloatSearchCriterion based on
        input from the user. There are a few formats which are accepted.

        float/int - GreaterThanFloatSearchCriterion
        string -
            gt<value> - GreaterThanFloatSearchCriterion
            lt<value> - LessThanFloatSearchCriterion
            min-max  - InRangeFloatSearchCriterion
    """
    def _convert(val):
        if not convert:
            return float(val)
        return float(convert(float(val)))

    criterions = [
        opencue.api.criterion_pb2.GreaterThanFloatSearchCriterion,
        opencue.api.criterion_pb2.LessThanFloatSearchCriterion,
        opencue.api.criterion_pb2.InRangeFloatSearchCriterion]

    if isinstance(mixed, (float, int)):
        result = opencue.api.criterion_pb2.GreaterThanFloatSearchCriterion(value=_convert(mixed))
    elif isinstance(mixed, str):
        if mixed.startswith("gt"):
            result = opencue.api.criterion_pb2.GreaterThanFloatSearchCriterion(
                value=_convert(mixed[2:]))
        elif mixed.startswith("lt"):
            result = opencue.api.criterion_pb2.LessThanFloatSearchCriterion(
                value=_convert(mixed[2:]))
        elif mixed.find("-") > -1:
            min_value, max_value = mixed.split("-", 1)
            result = opencue.api.criterion_pb2.InRangeFloatSearchCriterion(min=_convert(min_value),
                                                                           max=_convert(max_value))
        else:
            try:
                result = opencue.api.criterion_pb2.GreaterThanFloatSearchCriterion(
                    value=_convert(mixed))
            except ValueError:
                raise Exception("invalid float search input value: " + str(mixed))
    elif any([isinstance(mixed.__class__, crit_cls) for crit_cls in criterions]):
        result = mixed
    elif not mixed:
        return []
    else:
        raise Exception("invalid float search input value: " + str(mixed))

    return [result]


def handleIntCriterion(mixed, convert=None):
    """handleIntCriterion
        returns the proper subclass of IntSearchCriterion based on
        input from the user. There are a few formats which are accepted.

        float/int - GreaterThanFloatSearchCriterion
        string -
            gt<value> - GreaterThanFloatSearchCriterion
            lt<value> - LessThanFloatSearchCriterion
            min-max  - InRangeFloatSearchCriterion
    """
    def _convert(val):
        if not convert:
            return int(val)
        return int(convert(float(val)))

    criterions = [
        opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion,
        opencue.api.criterion_pb2.LessThanIntegerSearchCriterion,
        opencue.api.criterion_pb2.InRangeIntegerSearchCriterion]

    if isinstance(mixed, (float, int)):
        result = opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(value=_convert(mixed))
    elif isinstance(mixed, str):
        if mixed.startswith("gt"):
            result = opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(
                value=_convert(mixed[2:]))
        elif mixed.startswith("lt"):
            result = opencue.api.criterion_pb2.LessThanIntegerSearchCriterion(
                value=_convert(mixed[2:]))
        elif mixed.find("-") > -1:
            min_value, max_value = mixed.split("-", 1)
            result = opencue.api.criterion_pb2.InRangeIntegerSearchCriterion(
                min=_convert(min_value), max=_convert(max_value))
        else:
            try:
                result = opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(
                    value=_convert(mixed))
            except ValueError:
                raise Exception("invalid int search input value: " + str(mixed))
    elif any([isinstance(mixed.__class__, crit_cls) for crit_cls in criterions]):
        result = mixed
    elif not mixed:
        return []
    else:
        raise Exception("invalid float search input value: " + str(mixed))

    return [result]


def resolveJobNames(names):
    items = opencue.search.JobSearch.byName(names)
    logger.debug("found %d of %d supplied jobs" % (len(items), len(names)))
    if len(names) != len(items) and len(items):
        logger.warn("Unable to match all job names with running jobs on the cue.")
        logger.warn("Operations executed for %s" % set(names).intersection(
            [i.data.name for i in items]))
        logger.warn("Operations NOT executed for %s" % set(names).difference(
            [i.data.name for i in items]))
    if not items:
        raise ValueError("no valid jobs")
    return items


def resolveHostNames(names=None, substr=None):
    items = []
    if names:
        items = opencue.search.HostSearch.byName(names)
        logger.debug("found %d of %d supplied hosts" % (len(items), len(names)))
        if len(names) != len(items) and len(items):
            logger.warn("Unable to match all host names with valid hosts on the cue.")
            logger.warn("Operations executed for %s" % set(names).intersection(
                [i.data.name for i in items]))
            logger.warn("Operations NOT executed for %s" % set(names).difference([
                i.data.name for i in items]))
    elif substr:
        items = opencue.search.HostSearch.byMatch(substr)
        logger.debug("matched %d hosts using patterns %s" % (len(items), substr))
    if not items:
        raise ValueError("no valid hosts")
    return items


def resolveShowNames(names):
    items = []
    try:
        for name in names:
            items.append(opencue.api.findShow(name))
    except opencue.CueException:
        pass
    logger.debug("found %d of %d supplied shows" % (len(items), len(names)))
    if len(names) != len(items) and len(items):
        logger.warn("Unable to match all show names with active shows.")
        logger.warn("Operations executed for %s" % set(names).intersection(
            [i.data.name for i in items]))
        logger.warn("Operations NOT executed for %s" % set(names).difference(
            [i.data.name for i in items]))
    if not items:
        raise ValueError("no valid shows")
    return items


def confirm(msg, force, func, *args, **kwargs):
    if util.promptYesNo("Please confirm. %s?" % msg, force):
        logger.debug("%s [forced %s]" % (msg, force))
        return func(*args, **kwargs)


def formatTime(epoch, time_format="%m/%d %H:%M", default="--/-- --:--"):
    """Formats time using time formatting standards
    see: http://docs.python.org/library/time.html"""
    if not epoch:
        return default
    return time.strftime(time_format, time.localtime(epoch))


def findDuration(start, stop):
    if stop < 1:
        stop = int(time.time())
    return stop - start


def formatDuration(sec):
    def splitTime(seconds):
        minutes, seconds = divmod(seconds, 60)
        hour, minutes = divmod(minutes, 60)
        return hour, minutes, seconds
    return "%02d:%02d:%02d" % splitTime(sec)


def formatLongDuration(sec):
    def splitTime(seconds):
        minutes, seconds = divmod(seconds, 60)
        hour, minutes = divmod(minutes, 60)
        days, hour = divmod(hour, 24)
        return days, hour
    return "%02d:%02d" % splitTime(sec)


def formatMem(kmem, unit=None):
    k = 1024
    if unit == "K" or not unit and kmem < k:
        return "%dK" % kmem
    if unit == "M" or not unit and kmem < pow(k, 2):
        return "%dM" % (kmem / k)
    if unit == "G" or not unit and kmem < pow(k, 3):
        return "%.01fG" % (float(kmem) / pow(k, 2))


def cutoff(s, length):
    if len(s) < length-2:
        return s
    else:
        return "%s.." % s[0:length-2]


# These static utility methods are implementations that may or may not
# need to be moved to the server, but should be someplace common
#
class DependUtil(object):

    def __init__(self):
        pass

    @staticmethod
    def dropAllDepends(job, layer=None, frame=None):
        if frame:
            logger.debug("dropping all depends on: %s/%04d-%s" % (job, layer, frame))
            depend_er_frame = opencue.api.findFrame(job, layer, frame)
            for depend in depend_er_frame.getWhatThisDependsOn():
                depend.proxy.satisfy()
        elif layer:
            logger.debug("dropping all depends on: %s/%s" % (job, layer))
            depend_er_layer = opencue.api.findLayer(job, layer)
            for depend in depend_er_layer.getWhatThisDependsOn():
                depend.proxy.satisfy()
        else:
            logger.debug("dropping all depends on: %s" % job)
            depend_er_job = opencue.api.findJob(job)
            for depend in depend_er_job.getWhatThisDependsOn():
                logger.debug("dropping depend %s %s" % (depend.data.type, opencue.id(depend)))
                depend.proxy.satisfy()


class Convert(object):

    def __init__(self):
        pass

    @staticmethod
    def gigsToKB(val):
        return int(1048576 * val)

    @staticmethod
    def hoursToSeconds(val):
        return int(3600 * val)

    @staticmethod
    def stringToBoolean(val):
        if val.lower() in ("yes", "on", "enabled", "true"):
            return True
        return False

    @staticmethod
    def strToMatchSubject(val):
        try:
            return getattr(opencue.api.filter_pb2, str(val).upper())
        except Exception:
            raise ValueError("invalid match subject: %s" % val.upper())

    @staticmethod
    def strToMatchType(val):
        try:
            return getattr(opencue.api.filter_pb2, str(val).upper())
        except Exception:
            raise ValueError("invalid match type: %s" % val.upper())

    @staticmethod
    def strToActionType(val):
        try:
            return getattr(opencue.api.filter_pb2, str(val).upper())
        except Exception:
            raise ValueError("invalid action type: %s" % val.upper())

    @staticmethod
    def strToFrameState(val):
        try:
            return getattr(opencue.api.job_pb2, str(val).upper())
        except Exception:
            raise ValueError("invalid frame state: %s" % val.upper())

    @staticmethod
    def strToHardwareState(val):
        try:
            return getattr(opencue.api.host_pb2, str(val.upper()))
        except Exception:
            raise ValueError("invalid hardware state: %s" % val.upper())

    @staticmethod
    def strToThreadMode(val):
        """Converts the given value to opencue.api.host_pb2.ThreadMode enumerated value."""
        try:
            return getattr(opencue.api.host_pb2, str(val.upper()))
        except Exception:
            raise ValueError("invalid thread mode: %s" % val.upper())


class ActionUtil(object):

    def __init__(self):
        pass

    @staticmethod
    def factory(actionType, value):
        a = opencue.api.filter_pb2.Action()
        a.type = Convert.strToActionType(actionType)
        ActionUtil.setValue(a, value)
        return a

    @staticmethod
    def getValue(a):
        valueType = str(a.data.value_type)
        if valueType == "GroupType":
            return a.data.group_value
        elif valueType == "StringType":
            return a.data.string_value
        elif valueType == "IntegerType":
            return a.data.integer_value
        elif valueType == "FloatType":
            return a.data.float_value
        elif valueType == "BooleanType":
            return a.data.boolean_value
        else:
            return None

    @staticmethod
    def setValue(act, value):
        if act.type == opencue.api.filter_pb2.MOVE_JOB_TO_GROUP:
            act.groupValue = opencue.proxy(value)
            act.valueType = opencue.api.filter_pb2.GROUP_TYPE

        elif act.type == opencue.api.filter_pb2.PAUSE_JOB:
            act.booleanValue = value
            act.valueType = opencue.api.filter_pb2.BOOLEAN_TYPE

        elif act.type in (opencue.api.filter_pb2.SET_JOB_PRIORITY,
                          opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MEMORY):
            act.integerValue = int(value)
            act.valueType = opencue.api.filter_pb2.INTEGER_TYPE

        elif act.type in (opencue.api.filter_pb2.SET_JOB_MIN_CORES,
                          opencue.api.filter_pb2.SET_JOB_MAX_CORES,
                          opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_CORES):
            act.floatValue = float(value)
            act.valueType = opencue.api.filter_pb2.FLOAT_TYPE

        elif act.type == opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_TAGS:
            act.stringValue = value
            act.valueType = opencue.api.filter_pb2.STRING_TYPE

        elif act.type == opencue.api.filter_pb2.STOP_PROCESSING:
            act.valueType = opencue.api.filter_pb2.NONE_TYPE
        else:
            raise TypeError("invalid action type: %s" % act.type)


def handleArgs(args):

    #
    # Query
    #
    if isinstance(args.lp, list) or isinstance(args.ll, list):
        if isinstance(args.ll, list):
            args.lp = args.ll
        if not args.host:
            args.host = []

        procs = opencue.search.ProcSearch().byOptions(
            show=args.lp,
            host=args.host,
            limit=args.limit,
            alloc=args.alloc,
            job=args.job,
            memory=handleIntCriterion(args.memory, Convert.gigsToKB),
            duration=handleIntCriterion(args.duration, Convert.hoursToSeconds))
        if isinstance(args.ll, list):
            print "\n".join([l.data.logPath for l in procs])
        else:
            output.displayProcs(procs)
        return

    elif args.lh:
        states = [Convert.strToHardwareState(s) for s in args.state]
        output.displayHosts(opencue.api.getHosts(match=args.query, state=states, alloc=args.alloc))
        return

    elif args.lba:
        allocation = opencue.api.findAllocation(args.lba)
        output.displaySubscriptions(allocation.getSubscriptions(), "All Shows")
        return

    elif isinstance(args.lv, (list,)):
        if args.lv:
            show = opencue.api.findShow(args.lv[0])
            output.displayServices(show.getServiceOverrides())
        else:
            output.displayServices(opencue.api.getDefaultServices())
        return
    #
    # Gather hosts if -host - hostmatch was specified
    #
    host_error_msg = "No valid hosts selected, see the -host/-hostmatch options"
    hosts = None
    if args.host or args.hostmatch:
        hosts = resolveHostNames(args.host, args.hostmatch)

    #
    # Allocations
    #
    if args.create_alloc:
        fac, name, tag = args.create_alloc
        confirm(
            "Create new allocation %s.%s, with tag %s" % (fac, name, tag),
            args.force, createAllocation, fac, name, tag)

    elif args.delete_alloc:
        allocation = opencue.api.findAllocation(args.delete_alloc)
        confirm("Delete allocation %s" % args.delete_alloc, args.force, allocation.delete)

    elif args.rename_alloc:
        old, new = args.rename_alloc
        try:
            new = new.split(".", 2)[1]
        except Exception:
            msg = "Allocation names must be in the form 'facility.name'"
            raise Exception(msg)

        confirm(
            "Rename allocation from %s to %s" % (old, new),
            args.force, opencue.api.findAllocation(old).setName, new)

    elif args.transfer:
        src = opencue.api.findAllocation(args.transfer[0])
        dst = opencue.api.findAllocation(args.transfer[1])
        confirm(
            "Transfer hosts from from %s to %s" % (src.data.name, dst.data.name),
            args.force, dst.reparentHosts, src.getHosts())

    elif args.tag_alloc:
        alloc, tag = args.tag_alloc
        confirm("Re-tag allocation %s with %s" % (alloc, tag),
                args.force, opencue.api.findAllocation(alloc).setTag, tag)
    #
    # Shows
    #
    elif args.create_show:
        confirm("Create new show %s" % args.create_show,
                args.force, opencue.api.createShow, args.create_show)
    elif args.delete_show:
        confirm("Delete show %s" % args.delete_show,
                args.force, opencue.api.findShow(args.delete_show).delete)

    elif args.disable_show:
        confirm("Disable show %s" % args.disable_show,
                args.force, opencue.api.findShow(args.disable_show).setActive, False)

    elif args.enable_show:
        confirm("Enable show %s" % args.enable_show,
                args.force, opencue.api.findShow(args.enable_show).setActive, True)

    elif args.dispatching:
        show = opencue.api.findShow(args.dispatching[0])
        enabled = Convert.stringToBoolean(args.dispatching[1])
        if not enabled:
            confirm("Disable dispatching on %s" % opencue.rep(show),
                    args.force, show.enableDispatching, enabled)
        else:
            show.enableDispatching(True)

    elif args.booking:
        show = opencue.api.findShow(args.booking[0])
        enabled = Convert.stringToBoolean(args.booking[1])
        if not enabled:
            confirm("Disable booking on %s" % opencue.rep(show),
                    args.force, show.enableBooking, False)
        else:
            show.enableBooking(True)

    elif args.default_min_cores:
        confirm("Set the default min cores to: %s" %
                args.default_min_cores[1], args.force,
                opencue.api.findShow(args.default_min_cores[0]).setDefaultMinCores,
                float(int(args.default_min_cores[1])))

    elif args.default_max_cores:
        confirm("Set the default max cores to: %s" %
                args.default_max_cores[1], args.force,
                opencue.api.findShow(args.default_max_cores[0]).setDefaultMaxCores,
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
            logger.debug("locking host: %s" % opencue.rep(host))
            host.lock()

    elif args.unlock:
        if not hosts:
            raise ValueError(host_error_msg)
        for host in hosts:
            logger.debug("unlocking host: %s" % opencue.rep(host))
            host.unlock()

    elif args.move:
        if not hosts:
            raise ValueError(host_error_msg)

        def moveHosts(hosts_, dst_):
            for host_ in hosts_:
                logger.debug("moving %s to %s" % (opencue.rep(host_), opencue.rep(dst_)))
                host_.setAllocation(dst_.data)

        confirm("Move %d hosts to %s" % (len(hosts), args.move),
                args.force, moveHosts, hosts, opencue.api.findAllocation(args.move))

    # No Test coverage, takes up to a minute for
    # a host to report back in.
    elif args.delete_host:
        if not hosts:
            raise ValueError(host_error_msg)

        def deleteHosts(hosts_):
            for host_ in hosts_:
                logger.debug("deleting host: %s" % host_)
                try:
                    host_.delete()
                except Exception, e:
                    print "Failed to delete %s due to %s" % (host_, e)

        confirm("Delete %s hosts" % len(hosts), args.force, deleteHosts, hosts)

    # No Test coverage, sometimes the machines don't come
    # back up.
    elif args.safe_reboot:
        if not hosts:
            raise ValueError(host_error_msg)

        def safeReboot(hosts_):
            for host_ in hosts_:
                logger.debug("locking host and rebooting when idle %s" % opencue.rep(host_))
                host_.rebootWhenIdle()

        confirm("Lock and reboot %d hosts when idle" % len(hosts),
                args.force, safeReboot, hosts)

    elif args.thread:
        if not hosts:
            raise ValueError(host_error_msg)

        def setThreadMode(hosts_, mode):
            for host_ in hosts_:
                logger.debug("setting host %s to thread mode %s" % (host_.data.name, mode))
                host_.setThreadMode(Convert.strToThreadMode(mode))

        confirm("Set %d hosts to thread mode %s" % (len(hosts), args.thread), args.force,
                setThreadMode, hosts, args.thread)

    elif args.repair:
        if not hosts:
            raise ValueError(host_error_msg)

        def setRepairState(hosts_):
            for host_ in hosts_:
                logger.debug("setting host into the repair state %s" % host_.data.name)
                host_.setHardwareState(opencue.api.host_pb2.REPAIR)

        confirm("Set %d hosts into the Repair state?" % len(hosts),
                args.force, setRepairState, hosts)

    elif args.fixed:
        if not hosts:
            raise ValueError(host_error_msg)

        def setUpState(hosts_):
            for host_ in hosts_:
                logger.debug("setting host into the repair state %s" % host_.data.name)
                host_.setHardwareState(opencue.api.host_pb2.UP)

        confirm("Set %d hosts into the Up state?" % len(hosts),
                args.force, setUpState, hosts)

    elif args.create_sub:
        show = opencue.api.findShow(args.create_sub[0])
        alloc = opencue.api.findAllocation(args.create_sub[1])
        confirm("Create subscription for %s on %s" % (opencue.rep(show), opencue.rep(alloc)),
                args.force, show.createSubscription,
                alloc.data, float(args.create_sub[2]), float(args.create_sub[3]))

    elif args.delete_sub:
        sub_name = "%s.%s" % (args.delete_sub[1], args.delete_sub[0])
        confirm("Delete %s's subscription to %s" %
                (args.delete_sub[0], args.delete_sub[1]),
                args.force, opencue.api.findSubscription(sub_name).delete)

    elif args.size:
        sub_name = "%s.%s" % (args.size[1], args.size[0])
        opencue.api.findSubscription(sub_name).setSize(float(args.size[2]))

    elif args.burst:
        sub_name = "%s.%s" % (args.burst[1], args.burst[0])
        sub = opencue.api.findSubscription(sub_name)
        burst = args.burst[2]
        if burst.find("%") !=-1:
            burst = int(sub.data.size + (sub.data.size * (int(burst[0:-1]) / 100.0)))
        sub.setBurst(float(burst))

    else:
        handleCommonQueryArgs(args)


def createAllocation(fac, name, tag):
    """Create a new allocation with the given name and tag."""
    facility = opencue.api.getFacility(fac)
    alloc = opencue.api.createAllocation(name, tag, facility)
    print "Created allocation: %s" % alloc.data.name
