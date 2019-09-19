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
Project: opencue Library

Module: filter.py - opencue Library implementation of spank filter

"""


import enum

from opencue import Cuebot
from opencue.compiled_proto import filter_pb2
from opencue.compiled_proto import job_pb2
from opencue.compiled_proto.filter_pb2 import Action as ActionData
from opencue.compiled_proto.filter_pb2 import ActionType
from opencue.compiled_proto.filter_pb2 import ActionValueType
from opencue.compiled_proto.filter_pb2 import Filter as FilterData
from opencue.compiled_proto.filter_pb2 import FilterType
from opencue.compiled_proto.filter_pb2 import MatchSubject
from opencue.compiled_proto.filter_pb2 import MatchType
from opencue.compiled_proto.filter_pb2 import Matcher as MatcherData

__all__ = ["Filter", "Action", "Matcher",
           "FilterData", "ActionData", "MatcherData",
           "FilterType", "ActionType", "MatchType",
           "ActionValueType", "MatchSubject"]


class Filter(object):
    """This class contains the grpc implementation related to a Filter."""

    class FilterType(enum.IntEnum):
        MATCH_ANY = filter_pb2.MATCH_ANY
        MATCH_ALL = filter_pb2.MATCH_ALL

    def __init__(self, filter=None):
        """_Filter class initialization"""
        self.data = filter
        self.stub = Cuebot.getStub('filter')

    def delete(self):
        """Deletes the filter"""
        self.stub.Delete(filter_pb2.FilterDeleteRequest(filter=self.data), timeout=Cuebot.Timeout)

    def createMatcher(self, subject, matchType, query):
        """Creates a matcher for this filter
        @type  subject: filter_pb2.MatchSubject.*
        @param subject: The job attribute to match
        @type  matchType: filter_pb2.MatchType.*
        @param matchType: The type of match to perform
        @type  query: string
        @param query: The value to match
        @rtype:  Matcher
        @return: The new matcher object"""
        matcher = MatcherData(
            subject=subject,
            type=matchType,
            input=query.replace(' ', '')
        )
        return Matcher(self.stub.CreateMatcher(
            filter_pb2.FilterCreateMatcherRequest(filter=self.data, data=matcher),
            timeout=Cuebot.Timeout).matcher)

    def createAction(self, actionType, value):
        """Creates an action for this filter.
        @type  actionType: filter_pb2.ActionType.*
        @param actionType: The action to perform
        @type  value: Group or str, or int or bool
        @param value: Value relevant to the type selected
        @rtype:  Action
        @return: The new Action object"""
        action = ActionData(
            type=actionType,
            group_value=None,
            string_value=None,
            integer_value=0,
            float_value=0.0,
            boolean_value=False
        )

        if isinstance(value, job_pb2.Group):
            action.value_type = filter_pb2.GROUP_TYPE
            action.group_value = value.id
        elif isinstance(value, str):
            action.value_type = filter_pb2.STRING_TYPE
            action.string_value = value
        elif isinstance(value, bool):
            action.value_type = filter_pb2.BOOLEAN_TYPE
            action.boolean_value = value
        elif isinstance(value, int):
            action.value_type = filter_pb2.INTEGER_TYPE
            action.integer_value = value
        elif isinstance(value, float):
            action.value_type = filter_pb2.FLOAT_TYPE
            action.float_value = value
        else:
            action.value_type = filter_pb2.NONE_TYPE

        return Action(self.stub.CreateAction(
            filter_pb2.FilterCreateActionRequest(filter=self.data, data=action),
            timeout=Cuebot.Timeout).action)

    def getActions(self):
        """Returns the actions in this filter
        @rtype: list<Action>
        @return: A list of the actions in this filter"""
        response = self.stub.GetActions(filter_pb2.FilterGetActionsRequest(filter=self.data),
                                        timeout=Cuebot.Timeout)
        return [Action(action) for action in response.actions.actions]

    def getMatchers(self):
        """Returns the matchers in this filter
        @rtype:  list<Matcher>
        @return: A list of the matchers in this filter"""
        response = self.stub.GetMatchers(filter_pb2.FilterGetMatchersRequest(filter=self.data),
                                         timeout=Cuebot.Timeout)
        return [Matcher(matcher) for matcher in response.matchers.matchers]

    def lowerOrder(self):
        """Lowers the order of this filter relative to the other filters"""
        self.stub.LowerOrder(filter_pb2.FilterLowerOrderRequest(filter=self.data),
                             timeout=Cuebot.Timeout)

    def raiseOrder(self):
        """Raises the order of this filter relative to the other filters"""
        self.stub.RaiseOrder(filter_pb2.FilterRaiseOrderRequest(filter=self.data),
                             timeout=Cuebot.Timeout)

    def orderFirst(self):
        """Orders this filter above all the other filters"""
        self.stub.OrderFirst(filter_pb2.FilterOrderFirstRequest(filter=self.data),
                             timeout=Cuebot.Timeout)

    def orderLast(self):
        """Orders this filter below all the other filters"""
        self.stub.OrderLast(filter_pb2.FilterOrderLastRequest(filter=self.data),
                            timeout=Cuebot.Timeout)

    def runFilterOnGroup(self, group):
        """Runs the filter on the group provided
        @type  group: list<opencue.wrapper.group.Group>
        @param group: The group to run the filter on"""
        self.stub.RunFilterOnGroup(
            filter_pb2.FilterRunFilterOnGroupRequest(filter=self.data, group=group.data),
            timeout=Cuebot.Timeout)

    def runFilterOnJobs(self, jobs):
        """Runs the filter on the list of jobs provided
        @type  jobs: list<opencue.wrapper.job.Job>
        @param jobs: The jobs to run the filter on"""
        jobSeq = job_pb2.JobSeq(jobs=[job.data for job in jobs])
        self.stub.RunFilterOnJobs(
            filter_pb2.FilterRunFilterOnJobsRequest(filter=self.data, jobs=jobSeq),
            timeout=Cuebot.Timeout)

    def setEnabled(self, value):
        """Enables or disables the filter
        @type  value: bool
        @param value: True to enable the filter and false to disable it"""
        self.stub.SetEnabled(filter_pb2.FilterSetEnabledRequest(filter=self.data, enabled=value),
                             timeout=Cuebot.Timeout)

    def setName(self, name):
        """Sets the name of this filter
        @type  name: str
        @param name: The new name for this filter"""
        self.stub.SetName(filter_pb2.FilterSetNameRequest(filter=self.data, name=name),
                          timeout=Cuebot.Timeout)

    def setType(self, filterType):
        """Changes the filter type
        @type  filterType: filter_pb2.FilterType
        @param filterType: The new filter type"""
        self.stub.SetType(filter_pb2.FilterSetTypeRequest(filter=self.data, type=filterType),
                          timeout=Cuebot.Timeout)

    def setOrder(self, order):
        self.stub.SetOrder(filter_pb2.FilterSetOrderRequest(filter=self.data, order=order),
                           timeout=Cuebot.Timeout)

    def name(self):
        return self.data.name

    def type(self):
        return self.data.type

    def order(self):
        return self.data.order

    def isEnabled(self):
        return self.data.enabled

    def id(self):
        """Returns the id of the filter
        @rtype:  str
        @return: Filter uuid"""
        return self.data.id


class Action(object):

    class ActionType(enum.IntEnum):
        MOVE_JOB_TO_GROUP = filter_pb2.MOVE_JOB_TO_GROUP
        PAUSE_JOB = filter_pb2.PAUSE_JOB
        SET_JOB_MIN_CORES = filter_pb2.SET_JOB_MIN_CORES
        SET_JOB_MAX_CORES = filter_pb2.SET_JOB_MAX_CORES
        STOP_PROCESSING = filter_pb2.STOP_PROCESSING
        SET_JOB_PRIORITY = filter_pb2.SET_JOB_PRIORITY
        SET_ALL_RENDER_LAYER_TAGS = filter_pb2.SET_ALL_RENDER_LAYER_TAGS
        SET_ALL_RENDER_LAYER_MEMORY = filter_pb2.SET_ALL_RENDER_LAYER_MEMORY
        SET_ALL_RENDER_LAYER_CORES = filter_pb2.SET_ALL_RENDER_LAYER_CORES
        SET_MEMORY_OPTIMIZER = filter_pb2.SET_MEMORY_OPTIMIZER

    class ActionValueType(enum.IntEnum):
        GROUP_TYPE = filter_pb2.GROUP_TYPE
        STRING_TYPE = filter_pb2.STRING_TYPE
        INTEGER_TYPE = filter_pb2.INTEGER_TYPE
        FLOAT_TYPE = filter_pb2.FLOAT_TYPE
        BOOLEAN_TYPE = filter_pb2.BOOLEAN_TYPE
        NONE_TYPE = filter_pb2.NONE_TYPE

    def __init__(self, action=None):
        self.data = action
        self.stub = Cuebot.getStub('action')

    def getParentFilter(self):
        response = self.stub.GetParentFilter(
            filter_pb2.ActionGetParentFilterRequest(action=self.data),
            timeout=Cuebot.Timeout
        )
        return Filter(response.filter)

    def delete(self):
        self.stub.Delete(filter_pb2.ActionDeleteRequest(action=self.data), timeout=Cuebot.Timeout)

    def commit(self):
        if self.isNew():
            raise Exception(
                "unable to commit action that has not been created, proxy does not exist")
        self.stub.Commit(filter_pb2.ActionCommitRequest(action=self.data), timeout=Cuebot.Timeout)

    def isNew(self):
        return self.data is None

    def name(self):
        if self.value() is None:
            return "%s" % self.type()
        else:
            return "%s %s" % (self.type(), self.value())

    def value(self):
        valueType = self.data.value_type
        if valueType == filter_pb2.GROUP_TYPE:
            return self.data.group_value
        elif valueType == filter_pb2.STRING_TYPE:
            return self.data.string_value
        elif valueType == filter_pb2.INTEGER_TYPE:
            return self.data.integer_value
        elif valueType == filter_pb2.FLOAT_TYPE:
            return self.data.float_value
        elif valueType == filter_pb2.BOOLEAN_TYPE:
            return self.data.boolean_value
        else:
            return None

    def type(self):
        return self.data.type

    def setTypeAndValue(self, actionType, value):
        self.data.type = actionType
        if actionType == filter_pb2.MOVE_JOB_TO_GROUP:
            if not isinstance(value, job_pb2.Group):
                raise TypeError("invalid group argument, not a group")
            if not value.id:
                raise ValueError("group is not a valid rpc object")
            self.data.group_value = value.id
            self.data.value_type = filter_pb2.GROUP_TYPE

        elif actionType in (filter_pb2.PAUSE_JOB, filter_pb2.SET_MEMORY_OPTIMIZER):
            self.data.boolean_value = value
            self.data.value_type = filter_pb2.BOOLEAN_TYPE

        elif actionType in (filter_pb2.SET_JOB_PRIORITY,
                            filter_pb2.SET_ALL_RENDER_LAYER_MEMORY):
            self.data.integer_value = int(value)
            self.data.value_type = filter_pb2.INTEGER_TYPE

        elif actionType in (filter_pb2.SET_JOB_MIN_CORES,
                            filter_pb2.SET_JOB_MAX_CORES,
                            filter_pb2.SET_ALL_RENDER_LAYER_CORES):
            self.data.float_value = float(value)
            self.data.value_type = filter_pb2.FLOAT_TYPE

        elif actionType == filter_pb2.SET_ALL_RENDER_LAYER_TAGS:
            self.data.string_value = value
            self.data.value_type = filter_pb2.STRING_TYPE

        elif actionType == filter_pb2.STOP_PROCESSING:
            self.data.value_type = filter_pb2.NONE_TYPE

        else:
           raise Exception("invalid action type: %s" % actionType)

        self.commit()

    def id(self):
        """Returns the id of the action
        @rtype:  str
        @return: Action uuid"""
        return self.data.id


class Matcher(object):

    class MatchSubject(enum.IntEnum):
        JOB_NAME = filter_pb2.JOB_NAME
        SHOW = filter_pb2.SHOW
        SHOT = filter_pb2.SHOT
        USER = filter_pb2.USER
        SERVICE_NAME = filter_pb2.SERVICE_NAME
        PRIORITY = filter_pb2.PRIORITY
        FACILITY = filter_pb2.FACILITY
        LAYER_NAME = filter_pb2.LAYER_NAME

    class MatchType(enum.IntEnum):
        CONTAINS = filter_pb2.CONTAINS
        DOES_NOT_CONTAIN = filter_pb2.DOES_NOT_CONTAIN
        IS = filter_pb2.IS
        IS_NOT = filter_pb2.IS_NOT
        REGEX = filter_pb2.REGEX
        BEGINS_WITH = filter_pb2.BEGINS_WITH
        ENDS_WITH = filter_pb2.ENDS_WITH

    def __init__(self, matcher=None):
        self.data = matcher
        self.stub = Cuebot.getStub('matcher')

    def getParentFilter(self):
        response = self.stub.GetParentFilter(
            filter_pb2.MatcherGetParentFilterRequest(matcher=self.data),
            timeout=Cuebot.Timeout
        )
        return Filter(response.filter)

    def delete(self):
        self.stub.Delete(filter_pb2.MatcherDeleteRequest(matcher=self.data), timeout=Cuebot.Timeout)

    def commit(self):
        if self.isNew():
            raise Exception(
                "unable to commit matcher that has not been created, proxy does not exist")
        self.data.input = self.data.input.replace(" ", "")
        self.stub.Commit(filter_pb2.MatcherCommitRequest(matcher=self.data), timeout=Cuebot.Timeout)

    def isNew(self):
        return self.data is None

    def name(self):
        return "%s %s %s" % (self.data.subject, self.data.type, self.data.input)

    def subject(self):
        return self.data.subject

    def type(self):
        return self.data.type

    def input(self):
        return self.data.input

    def id(self):
        """Returns the id of the matcher
        @rtype:  str
        @return: Matcher uuid"""
        return self.data.id

    def setSubject(self, value):
        self.data.subject = value
        self.commit()

    def setType(self, value):
        self.data.type = value
        self.commit()

    def setInput(self, value):
        value = value.replace(" ", "")
        self.data.input = str(value)
        self.commit()
