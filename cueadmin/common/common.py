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

import output
import util
from Manifest import Cue3

TEST_SERVERS = []


class __NullHandler(logging.Handler):
    def emit(self, record):
        pass


logger = logging.getLogger("cue3.tools")
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

epilog = '\n\n'


def testServers():
    return TEST_SERVERS


def handleCommonArgs(args):
    logger.debug(args)
    if args.unit_test:
        util.enableDebugLogging()
        Cue3.Cuebot.setHosts(testServers())
        logger.info("running unit tests")
        logger.info("setting up test servers")
    if args.verbose:
        util.enableDebugLogging()
    if args.server:
        logger.debug("setting cue3 host servers to %s" % args.server)
        Cue3.Cuebot.setHosts(args.server)
    if args.facility:
        logger.debug("setting facility to %s" % args.facility)
        Cue3.Cuebot.setFacility(args.facility)
    if args.force:
        pass


def handleParserException(args, e):
    try:
        if args.verbose:
            traceback.print_exc(file=sys.stderr)
        print epilog
        raise e
    except ValueError, ex:
            print >>sys.stderr, "Error: %s. Try the -verbose or -h flags for more info." % ex
    except Exception, ex:
        print >> sys.stderr, "Error: %s." % ex


def getCommonParser(**options):
    parser = argparse.ArgumentParser(**options)

    if parser.epilog:
        parser.epilog += epilog
    else:
        parser.epilog = epilog

    general = parser.add_argument_group("General Options")
    general.add_argument("-server", action='store', nargs="+", metavar='HOSTNAME',
                         help='Specify cuebot addres(s).')
    general.add_argument("-facility", action='store', metavar='CODE',
                         help='Specify the facility code.')
    general.add_argument("-verbose", "-v", action='store_true',
                         help='Turn on verbose logging.')
    general.add_argument("-force", action='store_true',
                         help='Force operations that usually require confirmation.')
    general.add_argument("-unit-test", action="store_true", help=argparse.SUPPRESS)
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
        output.displayHosts(Cue3.search.HostSearch.byMatch(args.query))
        return True
    elif args.lj:
        for job in Cue3.search.JobSearch.byMatch(args.query):
            print job.data.name
        return True
    elif args.lji:
        output.displayJobs(Cue3.search.JobSearch.byMatch(args.query))
        return True
    elif args.la:
        output.displayAllocations(Cue3.api.getAllocations())
        return True
    elif args.lb:
        for show in resolveShowNames(args.lb):
            output.displaySubscriptions(show.getSubscriptions(), show.data.name)
        return True
    elif args.ls:
        output.displayShows(Cue3.api.getShows())
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
        Cue3.api.criterion_pb2.GreaterThanFloatSearchCriterion,
        Cue3.api.criterion_pb2.LessThanFloatSearchCriterion,
        Cue3.api.criterion_pb2.InRangeFloatSearchCriterion]

    if isinstance(mixed, (float, int)):
        result = Cue3.api.criterion_pb2.GreaterThanFloatSearchCriterion(value=_convert(mixed))
    elif isinstance(mixed, str):
        if mixed.startswith("gt"):
            result = Cue3.api.criterion_pb2.GreaterThanFloatSearchCriterion(
                value=_convert(mixed[2:]))
        elif mixed.startswith("lt"):
            result = Cue3.api.criterion_pb2.LessThanFloatSearchCriterion(value=_convert(mixed[2:]))
        elif mixed.find("-") > -1:
            min_value, max_value = mixed.split("-", 1)
            result = Cue3.api.criterion_pb2.InRangeFloatSearchCriterion(min=_convert(min_value),
                                                                        max=_convert(max_value))
        else:
            try:
                result = Cue3.api.criterion_pb2.GreaterThanFloatSearchCriterion(
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
        Cue3.api.criterion_pb2.GreaterThanIntegerSearchCriterion,
        Cue3.api.criterion_pb2.LessThanIntegerSearchCriterion,
        Cue3.api.criterion_pb2.InRangeIntegerSearchCriterion]

    if isinstance(mixed, (float, int)):
        result = Cue3.api.criterion_pb2.GreaterThanIntegerSearchCriterion(value=_convert(mixed))
    elif isinstance(mixed, str):
        if mixed.startswith("gt"):
            result = Cue3.api.criterion_pb2.GreaterThanIntegerSearchCriterion(
                value=_convert(mixed[2:]))
        elif mixed.startswith("lt"):
            result = Cue3.api.criterion_pb2.LessThanIntegerSearchCriterion(
                value=_convert(mixed[2:]))
        elif mixed.find("-") > -1:
            min_value, max_value = mixed.split("-", 1)
            result = Cue3.api.criterion_pb2.InRangeIntegerSearchCriterion(
                min=_convert(min_value), max=_convert(max_value))
        else:
            try:
                result = Cue3.api.criterion_pb2.GreaterThanIntegerSearchCriterion(
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
    items = Cue3.search.JobSearch.byName(names)
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
        items = Cue3.search.HostSearch.byName(names)
        logger.debug("found %d of %d supplied hosts" % (len(items), len(names)))
        if len(names) != len(items) and len(items):
            logger.warn("Unable to match all host names with valid hosts on the cue.")
            logger.warn("Operations executed for %s" % set(names).intersection(
                [i.data.name for i in items]))
            logger.warn("Operations NOT executed for %s" % set(names).difference([
                i.data.name for i in items]))
    elif substr:
        items = Cue3.search.HostSearch.byMatch(substr)
        logger.debug("matched %d hosts using patterns %s" % (len(items), substr))
    if not items:
        raise ValueError("no valid hosts")
    return items


def resolveShowNames(names):
    items = []
    try:
        for name in names:
            items.append(Cue3.api.findShow(name))
    except Cue3.CueException:
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
class AllocUtil(object):
    def __init__(self):
        pass

    @staticmethod
    def transferHosts(src, dst):
        hosts = Cue3.proxy(src).getHosts()
        logger.debug("transferring %d hosts from %s to %s" %
                     (len(hosts), Cue3.rep(src), Cue3.rep(dst)))
        dst.proxy.reparentHosts(hosts)


class DependUtil(object):

    def __init__(self):
        pass

    @staticmethod
    def dropAllDepends(job, layer=None, frame=None):
        if frame:
            logger.debug("dropping all depends on: %s/%04d-%s" % (job, layer, frame))
            depend_er_frame = Cue3.api.findFrame(job, layer, frame)
            for depend in depend_er_frame.getWhatThisDependsOn():
                depend.proxy.satisfy()
        elif layer:
            logger.debug("dropping all depends on: %s/%s" % (job, layer))
            depend_er_layer = Cue3.api.findLayer(job, layer)
            for depend in depend_er_layer.getWhatThisDependsOn():
                depend.proxy.satisfy()
        else:
            logger.debug("dropping all depends on: %s" % job)
            depend_er_job = Cue3.api.findJob(job)
            for depend in depend_er_job.getWhatThisDependsOn():
                logger.debug("dropping depend %s %s" % (depend.data.type, Cue3.id(depend)))
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
            return getattr(Cue3.api.filter_pb2, str(val).upper())
        except Exception:
            raise ValueError("invalid match subject: %s" % val.upper())

    @staticmethod
    def strToMatchType(val):
        try:
            return getattr(Cue3.api.filter_pb2, str(val).upper())
        except Exception:
            raise ValueError("invalid match type: %s" % val.upper())

    @staticmethod
    def strToActionType(val):
        try:
            return getattr(Cue3.api.filter_pb2, str(val).upper())
        except Exception:
            raise ValueError("invalid action type: %s" % val.upper())

    @staticmethod
    def strToFrameState(val):
        try:
            return getattr(Cue3.api.job_pb2, str(val).upper())
        except Exception:
            raise ValueError("invalid frame state: %s" % val.upper())

    @staticmethod
    def strToHardwareState(val):
        try:
            return getattr(Cue3.api.host_pb2, str(val.upper()))
        except Exception:
            raise ValueError("invalid hardware state: %s" % val.upper())

    @staticmethod
    def strToThreadMode(val):
        """Converts the given value to Cue3.api.host_pb2.ThreadMode enumerated value."""
        try:
            return getattr(Cue3.api.host_pb2, str(val.upper()))
        except Exception:
            raise ValueError("invalid thread mode: %s" % val.upper())


class ActionUtil(object):

    def __init__(self):
        pass

    @staticmethod
    def factory(actionType, value):
        a = Cue3.api.filter_pb2.Action()
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
        if act.type == Cue3.api.filter_pb2.MOVE_JOB_TO_GROUP:
            act.groupValue = Cue3.proxy(value)
            act.valueType = Cue3.api.filter_pb2.GROUP_TYPE

        elif act.type == Cue3.api.filter_pb2.PAUSE_JOB:
            act.booleanValue = value
            act.valueType = Cue3.api.filter_pb2.BOOLEAN_TYPE

        elif act.type in (Cue3.api.filter_pb2.SET_JOB_PRIORITY,
                          Cue3.api.filter_pb2.SET_ALL_RENDER_LAYER_MEMORY):
            act.integerValue = int(value)
            act.valueType = Cue3.api.filter_pb2.INTEGER_TYPE

        elif act.type in (Cue3.api.filter_pb2.SET_JOB_MIN_CORES,
                          Cue3.api.filter_pb2.SET_JOB_MAX_CORES,
                          Cue3.api.filter_pb2.SET_ALL_RENDER_LAYER_CORES):
            act.floatValue = float(value)
            act.valueType = Cue3.api.filter_pb2.FLOAT_TYPE

        elif act.type == Cue3.api.filter_pb2.SET_ALL_RENDER_LAYER_TAGS:
            act.stringValue = value
            act.valueType = Cue3.api.filter_pb2.STRING_TYPE

        elif act.type in (Cue3.api.filter_pb2.STOP_PROCESSING,):
            act.valueType = Cue3.api.filter_pb2.NONE_TYPE
        else:
            raise TypeError("invalid action type: %s" % act.type)
