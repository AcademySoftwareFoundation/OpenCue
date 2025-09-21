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

"""Client side implementation of search criteria.

This module provides some easy factory methods to do common search operations. It also exposes
lower level RPC functionality for procedural searches.

==============
Usage examples
==============

The following example illustrates searching using the high level API::

    jobs = getJobs(show=["pipe"])

An example of a procedural search::

    s = JobSearch()
    s.shows.append("pipe")
    s.users.append("chambers")
    jobs = s.find()

A procedural example searching by regular expression::

    s = JobSearch()
    s.includeFinished = True
    s.regex.append("blah")
    for job in s.find():
        print job

Another procedural example::

    for job in JobSearch.byUser(["chambers","jwelborn"]):
        job.proxy.kill()

"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from builtins import object
import logging

# pylint: disable=cyclic-import
from opencue_proto import criterion_pb2
from opencue_proto import host_pb2
from opencue_proto import job_pb2
import opencue.wrappers.host
from .cuebot import Cuebot

logger = logging.getLogger("opencue")

__all__ = ["BaseSearch",
           "ProcSearch",
           "FrameSearch",
           "HostSearch",
           "JobSearch"]


class BaseSearch(object):
    """Base class for searching."""

    def __init__(self, **options):
        self.options = options

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.options == other.options

    def search(self):
        """Executes the search using the options provided at initiation."""
        return self.byOptions(**self.options)

    @classmethod
    def byOptions(cls, **options):
        """Executes the search using the provided options."""
        raise NotImplementedError


class ProcSearch(BaseSearch):
    """Class for searching for procs.

    See: help(opencue.getProcs)"""

    @staticmethod
    def criteriaFromOptions(**options):
        """Constructs a search criteria object for the given options."""
        return _setOptions(host_pb2.ProcSearchCriteria(), options)

    @classmethod
    def byOptions(cls, **options):
        """Executes the search using the given options."""
        criteria = cls.criteriaFromOptions(**options)
        return Cuebot.getStub('proc').GetProcs(
            host_pb2.ProcGetProcsRequest(r=criteria), timeout=Cuebot.Timeout)


class FrameSearch(BaseSearch):
    """Class for searching for frames."""

    page = 1
    limit = 500
    change_date = 0

    @classmethod
    def criteriaFromOptions(cls, **options):
        """Constructs a search criteria object for the given options."""
        criteria = _setOptions(job_pb2.FrameSearchCriteria(), options)
        criteria.page = options.get('page', cls.page)
        criteria.limit = options.get('limit', cls.limit)
        criteria.change_date = options.get('change_date', cls.change_date)
        return criteria

    # pylint: disable=arguments-differ
    @classmethod
    def byOptions(cls, job, **options):
        criteria = cls.criteriaFromOptions(**options)
        return Cuebot.getStub('frame').GetFrames(job_pb2.FrameGetFramesRequest(job=job, r=criteria),
                                                 timeout=Cuebot.Timeout)

    @classmethod
    def byRange(cls, job, val):
        """Executes a search by frame range."""
        cls.byOptions(job, frame_range=val)


class HostSearch(BaseSearch):
    """Class for searching for hosts."""

    @staticmethod
    def criteriaFromOptions(**options):
        """Constructs a search criteria object for the given options."""
        return _setOptions(host_pb2.HostSearchCriteria(), options)

    @classmethod
    def byOptions(cls, **options):
        criteria = cls.criteriaFromOptions(**options)
        return [
            opencue.wrappers.host.Host(host) for host in Cuebot.getStub('host').GetHosts(
                host_pb2.HostGetHostsRequest(r=criteria), timeout=Cuebot.Timeout).hosts.hosts]

    @classmethod
    def byName(cls, val):
        """Searches for a host by name."""
        return cls.byOptions(name=val)

    @classmethod
    def byRegex(cls, val):
        """Searches for a host by regular expression."""
        return cls.byOptions(regex=val)

    @classmethod
    def byId(cls, val):
        """Searches for a host by id."""
        return cls.byOptions(id=val)

    @classmethod
    def byMatch(cls, val):
        """Searches for a host by substring match."""
        return cls.byOptions(substr=val)

    @classmethod
    def byAllocation(cls, val):
        """Searches for a host by allocation."""
        return cls.byOptions(alloc=val)


class JobSearch(BaseSearch):
    """Class for searching for jobs."""

    @staticmethod
    def criteriaFromOptions(**options):
        """Constructs a search criteria object for the given options."""
        return _setOptions(job_pb2.JobSearchCriteria(), options)

    @classmethod
    def byOptions(cls, **options):
        criteria = cls.criteriaFromOptions(**options)
        return Cuebot.getStub('job').GetJobs(
            job_pb2.JobGetJobsRequest(r=criteria), timeout=Cuebot.Timeout)

    @classmethod
    def byName(cls, val):
        """Searches for a job by name."""
        return cls.byOptions(job=val)

    @classmethod
    def byId(cls, val):
        """Searches for a job by id."""
        return cls.byOptions(id=val)

    @classmethod
    def byRegex(cls, val):
        """Searches for a job by regex."""
        return cls.byOptions(regex=val)

    @classmethod
    def byMatch(cls, val):
        """Searches for a job by substring match."""
        return cls.byOptions(substr=val)

    @classmethod
    def byShow(cls, val):
        """Searches for a job by show."""
        return cls.byOptions(show=val)

    @classmethod
    def byShot(cls, val):
        """Searches for a job by shot."""
        return cls.byOptions(shots=val)

    @classmethod
    def byUser(cls, val):
        """Searches for a job by user."""
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

    :type  search: String or Int or Float
    :param search: The search desired: 'gt#', 'lt#', '#-#'.
                   '#' or # is assumed greater than.
    :type  searchType: Int or Float
    :param searchType: The type of search criterion required
    :type  convert: callable
    :param convert: Optional callable to convert the input to the units the
                    cuebot uses. ie: hours to seconds.
    :rtype:  SearchCriterion
    :return: A SearchCriterion object"""
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
        return criterion(value=_convert(search[2:]))

    if search.startswith("lt"):
        criterion = getattr(criterion_pb2,
                            "LessThan%sSearchCriterion" % searchTypeStr)
        return criterion(value=_convert(int(search[2:])))

    if search.find("-") > -1:
        criterion = getattr(criterion_pb2,
                            "InRange%sSearchCriterion" % searchTypeStr)
        min_range, max_range = search.split("-")
        return criterion(min=_convert(min_range), max=_convert(max_range))

    raise ValueError("Unable to parse this format: %s" % search)


def _raiseIfNotType(searchOption, value, expectedType):
    if not isinstance(value, list):
        raise TypeError("Failed to set search option: '{}'. Expects type '{}', but got {}.".format(
            searchOption, expectedType, type(value)))


def raiseIfNotList(searchOption, value):
    """Raises an exception if the provided value is not a list."""
    _raiseIfNotType(searchOption, value, list)


def _setOptions(criteria, options):

    for k, v in options.items():
        if k == "job" or (k == "name" and isinstance(criteria, job_pb2.JobSearchCriteria)):
            raiseIfNotList(k, v)
            criteria.jobs.extend(v)
        elif k == "host" or (k == "name" and isinstance(criteria, host_pb2.HostSearchCriteria)):
            raiseIfNotList(k, v)
            criteria.hosts.extend(v)
        elif k == "frames" or (k == "name" and isinstance(criteria, job_pb2.FrameSearchCriteria)):
            raiseIfNotList(k, v)
            criteria.frames.extend(v)
        elif k in("match", "substr"):
            raiseIfNotList(k, v)
            criteria.substr.extend(v)
        elif k == "regex":
            raiseIfNotList(k, v)
            criteria.regex.extend(v)
        elif k == "id":
            raiseIfNotList(k, v)
            criteria.ids.extend(v)
        elif k == "show":
            raiseIfNotList(k, v)
            criteria.shows.extend(v)
        elif k == "shot":
            raiseIfNotList(k, v)
            criteria.shots.extend(v)
        elif k == "user":
            raiseIfNotList(k, v)
            criteria.users.extend(v)
        elif k == "state" and isinstance(criteria, job_pb2.FrameSearchCriteria):
            raiseIfNotList(k, v)
            criteria.states.frame_states.extend(v)
        elif k == "state" and isinstance(criteria, host_pb2.HostSearchCriteria):
            raiseIfNotList(k, v)
            criteria.states.state.extend(v)
        elif k == "lock_state" and isinstance(criteria, host_pb2.HostSearchCriteria):
            raiseIfNotList(k, v)
            criteria.lock_states.state.extend(v)
        elif k == "layer":
            raiseIfNotList(k, v)
            criteria.layers.extend(v)
        elif k == "alloc":
            raiseIfNotList(k, v)
            criteria.allocs.extend(v)
        elif k in ("range", "frames"):
            if not v:
                continue
            if isinstance(criteria.frame_range, str):
                # Once FrameSearch.frameRange is not a string
                # this can go away
                criteria.frame_range = v
            else:
                criteria.frame_range.append(_createCriterion(v, int))
        elif k == "memory":
            if not v:
                continue
            if isinstance(criteria.memory_range, str):
                # Once FrameSearch.memoryRange is not a string
                # this can go away
                criteria.memory_range = v
            else:
                criteria.memory_range.append(
                    _createCriterion(v, int, lambda mem: (mem)))
        elif k == "memory_greater_than":
            if not v:
                continue
            criteria.memory_greater_than.append(
                    _createCriterion(v, int, lambda mem: (mem)))
        elif k == "memory_less_than":
            if not v:
                continue
            criteria.memory_greater_than.append(
                _createCriterion(v, int, lambda mem: (mem)))
        elif k == "duration":
            if not v:
                continue
            if isinstance(criteria.duration_range, str):
                # Once FrameSearch.durationRange is not a string
                # this can go away
                criteria.duration_range = v
            else:
                criteria.duration_range.append(
                    _createCriterion(v, int, lambda duration: (60 * 60 * duration)))
        elif k == "limit":
            criteria.max_results = int(v)
        elif k == "page" and isinstance(criteria, job_pb2.FrameSearchCriteria):
            criteria.page = int(v)
        elif k == "offset":
            criteria.first_result = int(v)
        elif k == "include_finished":
            criteria.include_finished = v
        elif k in ("os_filter",):
            # Client-side only options - these don't get sent to the server
            pass
        elif len(k) == 0:
            return criteria
        else:
            raise Exception("Criteria for search does not exist")
    return criteria
