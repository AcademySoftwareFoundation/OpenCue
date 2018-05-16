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



"""
Client side implemenation of search criteria.
The basic premise here is we provide some easy factory
methods to do common things but expose
lower level ICE functionality for procedural searches.

Examples:

Simple example using high level API
jobs = getJobs(show=["pipe"])

Procedural examples using ICE

Procedural Example 1:
s = JobSearch()
s.shows.append("pipe")
s.users.append("chambers")
jobs = s.find()

Procedural Example 2:
s = JobSearch()
s.includeFinished = True
s.regex.append("blah")
for job in s.find():
    print job

Procedural Example 3:
for job in JobSearch.byUser(["chambers","jwelborn"]):
    job.proxy.kill()

"""
from cuebot import Cuebot
import cue.CueClientIce as CueIce
import spi.SpiIce as SpiIce
from util import *
import logging

logger = logging.getLogger("cue3")

__all__ = ["ProcSearch",
         "FrameSearch",
         "HostSearch",
         "JobSearch"]

class ProcSearch(CueIce.ProcSearchCriteria):
    """See: help(Cue3.getProcs)"""
    def __init__(self, **options):
        """See: help(Cue3.getProcs)"""
        CueIce.ProcSearchCriteria.__init__(self, 1, [], [], [], [], [], [], [], [])
        if options:
            self.setOptions(**options)

    def setOptions(self, **options):
        """See: help(Cue3.getProcs)"""
        _setOptions(self, options)

    @staticmethod
    def byOptions(**options):
        """See: help(Cue3.getProcs)"""
        return Cuebot.Proxy.getProcs(ProcSearch(**options))

class FrameSearch(CueIce.FrameSearchCriteria):
    def __init__(self, **options):
        CueIce.FrameSearchCriteria.__init__(self, [], [], [], [], "","","", 1, 1000, 0)
        if options:
            self.setOptions(**options)

    def setOptions(self, **options):
        _setOptions(self, options)

    @staticmethod
    def byOptions(job, **options):
        return proxy(job).getFrames(FrameSearch(**options))

    @staticmethod
    def byRange(job, val):
        return proxy(job).getFrames(FrameSearch(range=val))

class HostSearch(CueIce.HostSearchCriteria):
    def __init__(self, **options):
        CueIce.HostSearchCriteria.__init__(self,[],[],[],[],[],[])
        self.setOptions(**options)

    def setOptions(self, **options):
        _setOptions(self, options)

    @staticmethod
    def byOptions(**options):
        return Cuebot.Proxy.getHosts(HostSearch(**options))

    @staticmethod
    def byName(val):
        return Cuebot.Proxy.getHosts(HostSearch(host=val))

    @staticmethod
    def byRegex(val):
        return Cuebot.Proxy.getHosts(HostSearch(regex=val))

    @staticmethod
    def byId(val):
        return Cuebot.Proxy.getHosts(HostSearch(id=val))

    @staticmethod
    def byMatch(val):
        return Cuebot.Proxy.getHosts(HostSearch(substr=val))

    @staticmethod
    def byAllocation(val):
        return Cuebot.Proxy.getHosts(HostSearch(alloc=val))

class JobSearch(CueIce.JobSearchCriteria):
    def __init__(self, **options):
        CueIce.JobSearchCriteria.__init__(self,[],[],[],[],[],[],[],False)
        self.setOptions(**options)
        self.includeFinished = options.get("all", False)

    def setOptions(self, **options):
        _setOptions(self, options)

    @staticmethod
    def byOptions(**options):
        return Cuebot.Proxy.getJobs(JobSearch(**options))

    @staticmethod
    def byName(val):
        return Cuebot.Proxy.getJobs(JobSearch(job=val))

    @staticmethod
    def byId(val):
        return Cuebot.Proxy.getJobs(JobSearch(id=val))

    @staticmethod
    def byRegex(val):
        return Cuebot.Proxy.getJobs(JobSearch(regex=val))

    @staticmethod
    def byMatch(val):
        return Cuebot.Proxy.getJobs(JobSearch(substr=val))

    @staticmethod
    def byShow(val):
        return Cuebot.Proxy.getJobs(JobSearch(show=val))

    @staticmethod
    def byShot(val):
        return Cuebot.Proxy.getJobs(JobSearch(shots=val))

    @staticmethod
    def byUser(name):
        return Cuebot.Proxy.getJobs(JobSearch(user=val))

def _append(stuff, item):
    if isinstance(item, (tuple, list, set)):
        stuff.extend(item)
    else:
        stuff.append(item)

def _createCriterion(search, searchType, convert=None):
    """handleCriterion
        returns the proper subclass of FloatSearchCriterion or IntSearchCriterion
        based on input from the user. There are a few formats which are accepted.

        float/int - GreaterThan[searchType]SearchCriterion
        string -
            gt<value> - GreaterThan[searchType]SearchCriterion
            lt<value> - LessThan[searchType]SearchCriterion
            min-max  - InRange[searchType]SearchCriterion
    @type  search: String or Int or Float
    @param search: The search desired: 'gt#', 'lt#', '#-#'.
                   '#' or # is assumed greater than.
    @type  searchType: Int or Float
    @param searchType: The type of search criterion required
    @type  convert: callable
    @param convert: Optional callable to convert the input to the units the
                    cuebot uses. ie: hours to seconds.
    @rtype:  SearchCriterion
    @return: A SearchCriterion object"""
    def _convert(val):
        if not convert:
            return searchType(val)
        return searchType(convert(searchType(val)))

    # A value by itself should be a greater than search
    if isinstance(search, (int, float)) or \
       isinstance(search, str) and search.isdigit():
        search = "gt%s" % search

    if searchType == float:
        searchTypeStr = "Float"
    elif searchType == int:
        searchTypeStr = "Integer"
    else:
        raise "Unknown searchType, must be Int or Float"

    if search.startswith("gt"):
        criterion = getattr(SpiIce,
                            "GreaterThan%sSearchCriterion" % searchTypeStr)
        return criterion(_convert(search[2:]))
    elif search.startswith("lt"):
        criterion = getattr(SpiIce,
                            "LessThan%sSearchCriterion" % searchTypeStr)
        return criterion(_convert(search[2:]))
    elif search.find("-") > -1:
        criterion = getattr(SpiIce,
                            "InRange%sSearchCriterion" % searchTypeStr)
        min, max = search.split("-")
        return criterion(_convert(min), _convert(max))

    raise "Unable to parse this format: %s" % search

def _setOptions(s, options):
    """_setOptions(criteria, dict)
        All the search options have relitively the same
        critiera.
    """
    for k, v in options.iteritems():
        if k == "job" or (k=="name" and isinstance(s, JobSearch)):
            _append(s.jobs,v)
        elif k == "host" or (k=="name" and isinstance(s, HostSearch)):
            _append(s.hosts,v)
        elif k == "frame" or (k=="name" and isinstance(s, FrameSearch)):
            _append(s.frames, v)
        elif k in("match","substr"):
            _append(s.substr,v)
        elif k == "regex":
            _append(s.regex,v)
        elif k == "id":
            _append(s.ids,id(v))
        elif k == "show":
            _append(s.shows,v)
        elif k == "shot":
            _append(s.shots,v)
        elif k == "user":
            _append(s.users,v)
        elif k == "state":
            _append(s.states, v)
        elif k == "layer":
            _append(s.layers, v)
        elif k == "alloc":
            _append(s.allocs, v)
        elif k in ("range", "frames"):
            if not v:
                continue
            if isinstance(s.frameRange, str):
                # Once FrameSearch.frameRange is not a string
                # this can go away
                s.frameRange = v
            else:
                s.frameRange.append(_createCriterion(v, int))
        elif k == "memory":
            if not v:
                continue
            if isinstance(s.memoryRange, str):
                # Once FrameSearch.memoryRange is not a string
                # this can go away
                s.memoryRange = v
            else:
                s.memoryRange.append(_createCriterion(v, int,
                                                      lambda mem:(1048576 * mem)))
        elif k == "duration":
            if not v:
                continue
            if isinstance(s.durationRange, str):
                # Once FrameSearch.durationRange is not a string
                # this can go away
                s.durationRange = v
            else:
                s.durationRange.append(_createCriterion(v, int,
                                                        lambda duration:(60 * 60 * duration)))
        elif k == "limit":
            s.maxResults = [int(v)]
        elif k == "offset":
            s.firstResult = int(v)

