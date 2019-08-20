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
Client side implementation of search criteria.
The basic premise here is we provide some easy factory
methods to do common things but expose
lower level rpc functionality for procedural searches.

Examples:

Simple example using high level API
jobs = getJobs(show=["pipe"])

Procedural examples using gRPC

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
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import object
import logging

import six

from opencue.compiled_proto import criterion_pb2
from opencue.compiled_proto import host_pb2
from opencue.compiled_proto import job_pb2
import opencue.wrappers.host
from .cuebot import Cuebot

logger = logging.getLogger("opencue")

__all__ = ["BaseSearch",
           "ProcSearch",
           "FrameSearch",
           "HostSearch",
           "JobSearch"]


class BaseSearch(object):
    def __init__(self, **options):
        self.options = options

    def search(self):
        return self.byOptions(**self.options)

    @classmethod
    def byOptions(cls, **options):
        raise NotImplementedError


class ProcSearch(BaseSearch):
    """See: help(opencue.getProcs)"""
    def __init__(self, **options):
        super(ProcSearch, self).__init__(**options)

    @staticmethod
    def criteriaFromOptions(**options):
        return _setOptions(host_pb2.ProcSearchCriteria(), options)

    @classmethod
    def byOptions(cls, **options):
        criteria = cls.criteriaFromOptions(**options)
        return Cuebot.getStub('proc').GetProcs(
            host_pb2.ProcGetProcsRequest(r=criteria), timeout=Cuebot.Timeout)


class FrameSearch(BaseSearch):

    page = 1
    limit = 1000
    change_date = 0

    def __init__(self, **options):
        super(FrameSearch, self).__init__(**options)

    @classmethod
    def criteriaFromOptions(cls, **options):
        criteria = _setOptions(job_pb2.FrameSearchCriteria(), options)
        criteria.page = options.get('page', cls.page)
        criteria.limit = options.get('limit', cls.limit)
        criteria.change_date = options.get('change_date', cls.change_date)
        return criteria

    @classmethod
    def byOptions(cls, job, **options):
        criteria = cls.criteriaFromOptions(**options)
        return Cuebot.getStub('frame').GetFrames(job_pb2.FrameGetFramesRequest(job=job, r=criteria),
                                                 timeout=Cuebot.Timeout)

    @classmethod
    def byRange(cls, job, val):
        cls.byOptions(job, frame_range=val)


class HostSearch(BaseSearch):
    def __init__(self, **options):
        super(HostSearch, self).__init__(**options)

    @staticmethod
    def criteriaFromOptions(**options):
        return _setOptions(host_pb2.HostSearchCriteria(), options)

    @classmethod
    def byOptions(cls, **options):
        criteria = cls.criteriaFromOptions(**options)
        return [
            opencue.wrappers.host.Host(host) for host in Cuebot.getStub('host').GetHosts(
                host_pb2.HostGetHostsRequest(r=criteria), timeout=Cuebot.Timeout).hosts.hosts]

    @classmethod
    def byName(cls, val):
        return cls.byOptions(name=val)

    @classmethod
    def byRegex(cls, val):
        return cls.byOptions(regex=val)

    @classmethod
    def byId(cls, val):
        return cls.byOptions(id=val)

    @classmethod
    def byMatch(cls, val):
        return cls.byOptions(substr=val)

    @classmethod
    def byAllocation(cls, val):
        return cls.byOptions(alloc=val)


class JobSearch(BaseSearch):
    def __init__(self, **options):
        super(JobSearch, self).__init__(**options)

    @staticmethod
    def criteriaFromOptions(**options):
        return _setOptions(job_pb2.JobSearchCriteria(), options)

    @classmethod
    def byOptions(cls, **options):
        criteria = cls.criteriaFromOptions(**options)
        return Cuebot.getStub('job').GetJobs(
            job_pb2.JobGetJobsRequest(r=criteria), timeout=Cuebot.Timeout)

    @classmethod
    def byName(cls, val):
        return cls.byOptions(job=val)

    @classmethod
    def byId(cls, val):
        return cls.byOptions(id=val)

    @classmethod
    def byRegex(cls, val):
        return cls.byOptions(regex=val)

    @classmethod
    def byMatch(cls, val):
        return cls.byOptions(substr=val)

    @classmethod
    def byShow(cls, val):
        return cls.byOptions(show=val)

    @classmethod
    def byShot(cls, val):
        return cls.byOptions(shots=val)

    @classmethod
    def byUser(cls, val):
        return cls.byOptions(user=val)


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

    if isinstance(search, (int, float)) or \
            isinstance(search, str) and search.isdigit():
        search = "gt%s" % search

    if searchType == float:
        searchTypeStr = "Float"
    elif searchType == int:
        searchTypeStr = "Integer"
    else:
        raise ValueError("Unknown searchType, must be Int or Float")

    if search.startswith("gt"):
        criterion = getattr(criterion_pb2,
                            "GreaterThan%sSearchCriterion" % searchTypeStr)
        return criterion(_convert(search[2:]))
    elif search.startswith("lt"):
        criterion = getattr(criterion_pb2,
                            "LessThan%sSearchCriterion" % searchTypeStr)
        return criterion(_convert(search[2:]))
    elif search.find("-") > -1:
        criterion = getattr(criterion_pb2,
                            "InRange%sSearchCriterion" % searchTypeStr)
        min, max = search.split("-")
        return criterion(_convert(min), _convert(max))

    raise ValueError("Unable to parse this format: %s" % search)


def _setOptions(criteria, options):

    for k, v in options.items():
        if k == "job" or (k == "name" and isinstance(criteria, job_pb2.JobSearchCriteria)):
            criteria.jobs.extend(v)
        elif k == "host" or (k == "name" and isinstance(criteria, host_pb2.HostSearchCriteria)):
            criteria.hosts.extend(v)
        elif k == "frames" or (k == "name" and isinstance(criteria, job_pb2.FrameSearchCriteria)):
            criteria.frames.extend(v)
        elif k in("match", "substr"):
            criteria.substr.extend(v)
        elif k == "regex":
            criteria.regex.extend(v)
        elif k == "id":
            criteria.ids.extend(v)
        elif k == "show":
            criteria.shows.extend(v)
        elif k == "shot":
            criteria.shots.extend(v)
        elif k == "user":
            criteria.users.extend(v)
        elif k == "state" and isinstance(criteria, job_pb2.FrameSearchCriteria):
            criteria.states.frame_states.extend(v)
        elif k == "state" and isinstance(criteria, host_pb2.HostSearchCriteria):
            criteria.states.state.extend(v)
        elif k == "layer":
            criteria.layers.extend(v)
        elif k == "alloc":
            criteria.allocs.extend(v)
        elif k in ("range", "frames"):
            if not v:
                continue
            if isinstance(criteria.frame_range, six.string_types):
                # Once FrameSearch.frameRange is not a string
                # this can go away
                criteria.frame_range = v
            else:
                criteria.frame_range.append(_createCriterion(v, int))
        elif k == "memory":
            if not v:
                continue
            if isinstance(criteria.memory_range, six.string_types):
                # Once FrameSearch.memoryRange is not a string
                # this can go away
                criteria.memory_range = v
            else:
                criteria.memory_range.append(_createCriterion(v, int,
                                                      lambda mem: (1048576 * mem)))
        elif k == "duration":
            if not v:
                continue
            if isinstance(criteria.duration_range, six.string_types):
                # Once FrameSearch.durationRange is not a string
                # this can go away
                criteria.duration_range = v
            else:
                criteria.duration_range.append(_createCriterion(v, int,
                                                        lambda duration:(60 * 60 * duration)))
        elif k == "limit":
            criteria.max_results.extend([int(v)])
        elif k == "offset":
            criteria.first_result = int(v)
        elif k == "include_finished":
            criteria.include_finished = v
    return criteria
