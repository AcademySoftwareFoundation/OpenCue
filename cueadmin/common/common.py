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
import sys
import logging
import time
import traceback

import output
from util import *

from Manifest import Cue3

TEST_SERVERS = []

class __NullHandler(logging.Handler):
    def emit(self, record):
        pass
logger = logging.getLogger("cue3.tools")
logger.addHandler(__NullHandler())

__ALL__=["testServer",
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

epilog ='''

'''

def testServers():
    return TEST_SERVERS

def handleCommonArgs(args):
    logger.debug(args)
    if args.unit_test:
        enableDebugLogging()
        Cue3.Cuebot.setHosts(testServers())
        logger.info("running unit tests")
        logger.info("setting up test servers")
    if args.verbose:
        enableDebugLogging()
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
        print >>sys.stderr, "Error: %s." %ex

def getCommonParser(**options):
    parser = argparse.ArgumentParser(**options)

    if parser.epilog:
        parser.epilog += epilog
    else:
        parser.epilog = epilog

    general = parser.add_argument_group("General Options")
    general.add_argument("-server",action='store', nargs="+", metavar='HOSTNAME',
                         help='Specify cuebot addres(s).')
    general.add_argument("-facility",action='store', metavar='CODE',
                         help='Specify the facility code.')
    general.add_argument("-verbose","-v",action='store_true',
                         help='Turn on verbose logging.')
    general.add_argument("-force",action='store_true',
                         help='Force operations that usually require confirmation.')
    general.add_argument("-unit-test", action="store_true", help=argparse.SUPPRESS)
    return parser

class QueryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if option_string == '-lh':
            namespace.lh = True
            namespace.query = values
        elif option_string in ('-lj','-laj'):
            namespace.lj = True
            namespace.query = values
        elif option_string == '-lji':
            namespace.lji = True
            namespace.query = values

def setCommonQueryArgs(parser):
    query = parser.add_argument_group("Query Options")
    query.add_argument("-lj","-laj",action=QueryAction,nargs="*", metavar="SUBSTR",
                       help="List jobs with optional name substring match.")
    query.add_argument("-lji",action=QueryAction, nargs="*", metavar="SUBSTR",
                       help="List job info with optional name substring match.")
    query.add_argument("-lh",action=QueryAction,nargs="*",metavar="SUBSTR",
                       help="List hosts with optional name substring match.")
    query.add_argument("-ls",action="store_true", help="List shows.")
    query.add_argument("-la",action="store_true", help="List allocations.")
    query.add_argument("-lb",action="store", nargs="+", help="List subscriptions.", metavar="SHOW")
    query.add_argument("-query","-q",nargs="+",action="store",default=[], help=argparse.SUPPRESS)
    return query

def handleCommonQueryArgs(args):
    if args.lh:
        output.displayHosts(Cue3.HostSearch.byMatch(args.query))
        return True
    elif args.lj:
        for job in Cue3.JobSearch.byMatch(args.query):
            print job.data.name
        return True
    elif args.lji:
        output.displayJobs(Cue3.JobSearch.byMatch(args.query))
        return True
    elif args.la:
        output.displayAllocations(Cue3.getAllocations())
        return True
    elif args.lb:
        for show in resolveShowNames(args.lb):
            output.displaySubscriptions(show.proxy.getSubscriptions(),show.data.name)
        return True
    elif args.ls:
        output.displayShows(Cue3.getShows())
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

    if isinstance(mixed, (float, int)):
        result = Cue3.SpiIce.GreaterThanFloatSearchCriterion(_convert(mixed))
    elif isinstance(mixed,str):
        if mixed.startswith("gt"):
            result = Cue3.SpiIce.GreaterThanFloatSearchCriterion(_convert(mixed[2:]))
        elif mixed.startswith("lt"):
            result = Cue3.SpiIce.LessThanFloatSearchCriterion(_convert(mixed[2:]))
        elif mixed.find("-") > -1:
            min,max = mixed.split("-",1)
            result = Cue3.SpiIce.InRangeFloatSearchCriterion(_convert(min),_convert(max))
        else:
            try:
                result = Cue3.SpiIce.GreaterThanFloatSearchCriterion(_convert(mixed))
            except ValueError:
                raise Exception("invalid float search input value: " + str(mixed))
    elif issubclass(mixed.__class__,Cue3.SpiIce.FloatSearchCriterion):
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

    if isinstance(mixed, (float, int)):
        result = Cue3.SpiIce.GreaterThanIntegerSearchCriterion(_convert(mixed))
    elif isinstance(mixed,str):
        if mixed.startswith("gt"):
            result = Cue3.SpiIce.GreaterThanIntegerSearchCriterion(_convert(mixed[2:]))
        elif mixed.startswith("lt"):
            result = Cue3.SpiIce.LessThanIntegerSearchCriterion(_convert(mixed[2:]))
        elif mixed.find("-") > -1:
            min,max = mixed.split("-",1)
            result = Cue3.SpiIce.InRangeIntegerSearchCriterion(_convert(min),_convert(max))
        else:
            try:
                result = Cue3.SpiIce.GreaterThanIntegerSearchCriterion(_convert(mixed))
            except ValueError:
                raise Exception("invalid int search input value: " + str(mixed))
    elif issubclass(mixed.__class__,Cue3.SpiIce.IntegerSearchCriterion):
        result = mixed
    elif not mixed:
        return []
    else:
       raise Exception("invalid float search input value: " + str(mixed))

    return [result]

def resolveJobNames(names):
    items = Cue3.JobSearch.byName(names);
    logger.debug("found %d of %d supplied jobs" % (len(items), len(names)))
    if len(names) != len(items) and len(items):
        logger.warn("Unable to match all job names with running jobs on the cue.");
        logger.warn("Operations executed for %s" % set(names).intersection([i.data.name for i in items]))
        logger.warn("Operations NOT executed for %s" % set(names).difference([i.data.name for i in items]))
    if not items:
        raise ValueError("no valid jobs")
    return items

def resolveHostNames(names=None, substr=None):
    if names:
        items = Cue3.HostSearch.byName(names);
        logger.debug("found %d of %d supplied hosts" % (len(items), len(names)))
        if len(names) != len(items) and len(items):
            logger.warn("Unable to match all host names with valid hosts on the cue.");
            logger.warn("Operations executed for %s" % set(names).intersection([i.data.name for i in items]))
            logger.warn("Operations NOT executed for %s" % set(names).difference([i.data.name for i in items]))
    elif substr:
        items = Cue3.HostSearch.byMatch(substr)
        logger.debug("matched %d hosts using patterns %s" % (len(items), substr))
    if not items:
        raise ValueError("no valid hosts")
    return items

def resolveShowNames(names):
    items = []
    try:
        for name in names:
            items.append(Cue3.findShow(name))
    except:
        pass
    logger.debug("found %d of %d supplied shows" % (len(items), len(names)))
    if len(names) != len(items) and len(items):
        logger.warn("Unable to match all show names with active shows.");
        logger.warn("Operations executed for %s" % set(names).intersection([i.data.name for i in items]))
        logger.warn("Operations NOT executed for %s" % set(names).difference([i.data.name for i in items]))
    if not items:
        raise ValueError("no valid shows")
    return items

def confirm(msg, force, func, *args, **kwargs):
    if promptYesNo("Please confirm. %s?" % msg, force):
        logger.debug("%s [forced %s]" % (msg,force))
        return func(*args, **kwargs)

def formatTime(epoch, format="%m/%d %H:%M", default="--/-- --:--"):
    """Formats time using time formatting standards
    see: http://docs.python.org/library/time.html"""
    if not epoch:
        return default
    return time.strftime(format,time.localtime(epoch))

def findDuration(start, stop):
    if stop < 1:
        stop = int(time.time())
    return stop - start

def formatDuration(sec):
    def splitTime(sec):
        min, sec = divmod(sec, 60)
        hour, min = divmod(min, 60)
        return (hour, min, sec)
    return "%02d:%02d:%02d" % splitTime(sec)

def formatLongDuration(sec):
    def splitTime(sec):
         min, sec = divmod(sec, 60)
         hour, min = divmod(min, 60)
         days, hour = divmod(hour, 24)
         return (days, hour)
    return "%02d:%02d" % splitTime(sec)

def formatMem(kmem, unit = None):
    k = 1024
    if unit == "K" or not unit and kmem < k:
        return "%dK" % kmem
    if unit == "M" or not unit and kmem < pow(k,2):
        return "%dM" % (kmem / k)
    if unit == "G" or not unit and kmem < pow(k,3):
        return "%.01fG" % (float(kmem) / pow(k,2))

def cutoff(s, length):
    if len(s) < length-2:
        return s
    else:
        return "%s.." % s[0:length-2]

# These static utility methods are implementations that may or may not
# need to be moved to the server, but should be someplace common
#
class AllocUtil:
    @staticmethod
    def transferHosts(src, dst):
        hosts = [host.proxy for host in Cue3.proxy(src).getHosts()]
        logger.debug("transfering %d hosts from %s to %s" %
                     (len(hosts), Cue3.rep(src), Cue3.rep(dst)))
        dst.proxy.reparentHosts(hosts)

class DependUtil:
    @staticmethod
    def dropAllDepends(job, layer=None, frame=None):
        if frame:
            logger.debug("dropping all depends on: %s/%04d-%s" % (job, layer, frame))
            depend_er_frame = Cue3.findFrame(job, layer, frame)
            for depend in depend_er_frame.proxy.getWhatThisDependsOn():
                depend.proxy.satisfy()
        elif layer:
            logger.debug("dropping all depends on: %s/%s" % (job, layer))
            depend_er_layer = Cue3.findLayer(job, layer)
            for depend in depend_er_layer.proxy.getWhatThisDependsOn():
                depend.proxy.satisfy()
        else:
            logger.debug("dropping all depends on: %s" % job)
            depend_er_job = Cue3.findJob(job)
            for depend in depend_er_job.proxy.getWhatThisDependsOn():
                logger.debug("dropping depend %s %s" % (depend.data.type, Cue3.id(depend)))
                depend.proxy.satisfy()

class Convert:

    @staticmethod
    def gigsToKB(val):
        return int(1048576 * val)

    @staticmethod
    def hoursToSeconds(val):
        return int(3600 * val)

    @staticmethod
    def stringToBoolean(val):
        if val.lower() in ("yes","on","enabled","true"):
            return True
        return False

    @staticmethod
    def strToMatchSubject(val):
        try:
            return Cue3.MatchSubject.__getattribute__(Cue3.MatchSubject, str(val))
        except:
            raise ValueError("invalid match subject: %s" % val)

    @staticmethod
    def strToMatchType(val):
        try:
            return Cue3.MatchType.__getattribute__(Cue3.MatchType, str(val))
        except:
            raise ValueError("invalid match type: %s" % val)

    @staticmethod
    def strToActionType(val):
        try:
            return Cue3.ActionType.__getattribute__(Cue3.ActionType, str(val))
        except:
            raise ValueError("invalid action type: %s" % value)

    @staticmethod
    def strToFrameState(val):
        try:
            return Cue3.FrameState.__getattribute__(Cue3.FrameState, str(val))
        except:
            raise ValueError("invalid frame state: %s" % val)

    @staticmethod
    def strToHardwareState(val):
        try:
            return Cue3.HardwareState.__getattribute__(Cue3.HardwareState, str(val.capitalize()))
        except:
            raise ValueError("invalid hardware state: %s" % val.capitalize())

    @staticmethod
    def strToThreadMode(val):
        """Converts the given value to Cue3.Threadmode enumerated value."""
        try:
            return Cue3.ThreadMode.__getattribute__(Cue3.ThreadMode, str(val.capitalize()))
        except:
            raise ValueError("invalid thread mode: %s" % val.capitalize())

class ActionUtil:

    @staticmethod
    def factory(actionType, value):
        a = Cue3.Entity.ActionData()
        a.type = convert.strToActionType(actionType)
        action.setValue(a, value)
        return a

    @staticmethod
    def getValue(a):
        valueType = str(a.data.valueType)
        if valueType == "GroupType":
            return a.data.groupValue
        elif valueType == "StringType":
            return a.data.stringValue
        elif valueType == "IntegerType":
            return a.data.integerValue
        elif valueType == "FloatType":
            return a.data.floatValue
        elif valueType == "BooleanType":
            return a.data.booleanValue
        else:
            return None

    @staticmethod
    def setValue(act, value):
        if act.type in (Cue3.ActionType.MoveJobToGroup,):
            act.groupValue = Cue3.proxy(value)
            act.valueType =  Cue3.ActionValueType.GroupType

        elif act.type in (Cue3.ActionType.PauseJob,):
            act.booleanValue = value
            act.valueType =  Cue3.ActionValueType.BooleanType

        elif act.type in (Cue3.ActionType.SetJobPriority,
                            Cue3.ActionType.SetAllRenderLayerMemory):
            act.integerValue = int(value)
            act.valueType =  Cue3.ActionValueType.IntegerType

        elif act.type in (Cue3.ActionType.SetJobMinCores,
                             Cue3.ActionType.SetJobMaxCores,
                             Cue3.ActionType.SetAllRenderLayerCores):
            act.floatValue = float(value)
            act.valueType =  Cue3.ActionValueType.FloatType
        elif act.type in (Cue3.ActionType.SetAllRenderLayerTags,):
            act.stringValue = value
            act.valueType =  Cue3.ActionValueType.StringType

        elif act.type in (ActionType.StopProcessing,):
            act.valueType =  Cue3.ActionValueType.NoneType
        else:
           raise TypeError("invalid action type: %s" % actionType)



