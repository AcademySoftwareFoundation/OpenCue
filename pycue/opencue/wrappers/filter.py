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

"""Classes for working with filters."""

import enum

from opencue_proto import filter_pb2
from opencue_proto import job_pb2
from opencue_proto.filter_pb2 import Action as ActionData
from opencue_proto.filter_pb2 import ActionType
from opencue_proto.filter_pb2 import ActionValueType
from opencue_proto.filter_pb2 import Filter as FilterData
from opencue_proto.filter_pb2 import FilterType
from opencue_proto.filter_pb2 import MatchSubject
from opencue_proto.filter_pb2 import MatchType
from opencue_proto.filter_pb2 import Matcher as MatcherData
from opencue import Cuebot
import opencue.wrappers.group


__all__ = ["Filter", "Action", "Matcher",
           "FilterData", "ActionData", "MatcherData",
           "FilterType", "ActionType", "MatchType",
           "ActionValueType", "MatchSubject"]


class Filter(object):
    """This class contains the grpc implementation related to a Filter."""

    class FilterType(enum.IntEnum):
        """The type of match used to determine if objects pass the filter."""
        MATCH_ANY = filter_pb2.MATCH_ANY
        MATCH_ALL = filter_pb2.MATCH_ALL

    # pylint: disable=redefined-builtin
    def __init__(self, filter=None):
        self.data = filter
        self.stub = Cuebot.getStub('filter')

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.data == other.data

    def delete(self):
        """Deletes the filter."""
        self.stub.Delete(filter_pb2.FilterDeleteRequest(filter=self.data), timeout=Cuebot.Timeout)

    def createMatcher(self, subject, matchType, query):
        """Creates a matcher for the filter.

        :type  subject: filter_pb2.MatchSubject.*
        :param subject: the job attribute to match
        :type  matchType: filter_pb2.MatchType.*
        :param matchType: the type of match to perform
        :type  query: string
        :param query: the value to match
        :rtype:  Matcher
        :return: the new matcher object
        """
        matcher = MatcherData(
            subject=subject,
            type=matchType,
            input=query.replace(' ', '')
        )
        return Matcher(self.stub.CreateMatcher(
            filter_pb2.FilterCreateMatcherRequest(filter=self.data, data=matcher),
            timeout=Cuebot.Timeout).matcher)

    def createAction(self, actionType, value):
        """Creates an action for the filter.

        :type  actionType: filter_pb2.ActionType.*
        :param actionType: the action to perform
        :type  value: opencue.wrapper.group.Group / str / int / bool
        :param value: value relevant to the type selected
        :rtype:  opencue.wrappers.filter.Action
        :return: the new action
        """
        action = ActionData(
            type=actionType,
            group_value=None,
            string_value=None,
            integer_value=0,
            float_value=0.0,
            boolean_value=False
        )

        if isinstance(value, opencue.wrappers.group.Group):
            action.value_type = filter_pb2.GROUP_TYPE
            action.group_value = value.id()
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
        """Returns the filter actions.

        :rtype:  list<opencue.wrappers.filter.Action>
        :return: list of the filter actions
        """
        response = self.stub.GetActions(filter_pb2.FilterGetActionsRequest(filter=self.data),
                                        timeout=Cuebot.Timeout)
        return [Action(action) for action in response.actions.actions]

    def getMatchers(self):
        """Returns the filter matchers.

        :rtype:  list<opencue.wrapper.filter.Matcher>
        :return: list of the filter matchers
        """
        response = self.stub.GetMatchers(filter_pb2.FilterGetMatchersRequest(filter=self.data),
                                         timeout=Cuebot.Timeout)
        return [Matcher(matcher) for matcher in response.matchers.matchers]

    def lowerOrder(self):
        """Lowers the order of the filter relative to other filters."""
        self.stub.LowerOrder(filter_pb2.FilterLowerOrderRequest(filter=self.data),
                             timeout=Cuebot.Timeout)

    def raiseOrder(self):
        """Raises the order of the filter relative to other filters."""
        self.stub.RaiseOrder(filter_pb2.FilterRaiseOrderRequest(filter=self.data),
                             timeout=Cuebot.Timeout)

    def orderFirst(self):
        """Orders the filter above all other filters."""
        self.stub.OrderFirst(filter_pb2.FilterOrderFirstRequest(filter=self.data),
                             timeout=Cuebot.Timeout)

    def orderLast(self):
        """Orders the filter below all other filters."""
        self.stub.OrderLast(filter_pb2.FilterOrderLastRequest(filter=self.data),
                            timeout=Cuebot.Timeout)

    def runFilterOnGroup(self, group):
        """Runs the filter on the group provided.

        :type  group: opencue.wrapper.group.Group
        :param group: group to run the filter on
        """
        self.stub.RunFilterOnGroup(
            filter_pb2.FilterRunFilterOnGroupRequest(filter=self.data, group=group.data),
            timeout=Cuebot.Timeout)

    def runFilterOnJobs(self, jobs):
        """Runs the filter on the list of jobs provided.

        :type  jobs: list<opencue.wrapper.job.Job>
        :param jobs: jobs to run the filter on
        """
        jobSeq = job_pb2.JobSeq(jobs=[job.data for job in jobs])
        self.stub.RunFilterOnJobs(
            filter_pb2.FilterRunFilterOnJobsRequest(filter=self.data, jobs=jobSeq),
            timeout=Cuebot.Timeout)

    def setEnabled(self, value):
        """Enables or disables the filter.

        :type  value: bool
        :param value: true to enable the filter and false to disable it
        """
        self.stub.SetEnabled(filter_pb2.FilterSetEnabledRequest(filter=self.data, enabled=value),
                             timeout=Cuebot.Timeout)

    def setName(self, name):
        """Sets the name of the filter.

        :type  name: str
        :param name: new filter name
        """
        self.stub.SetName(filter_pb2.FilterSetNameRequest(filter=self.data, name=name),
                          timeout=Cuebot.Timeout)

    def setType(self, filterType):
        """Changes the filter type.

        :type  filterType: opencue_proto.filter_pb2.FilterType
        :param filterType: the new filter type
        """
        self.stub.SetType(filter_pb2.FilterSetTypeRequest(filter=self.data, type=filterType),
                          timeout=Cuebot.Timeout)

    def setOrder(self, order):
        """Directly sets the order of the filter.

        :type  order: int
        :param order: the new filter order
        """
        self.stub.SetOrder(filter_pb2.FilterSetOrderRequest(filter=self.data, order=order),
                           timeout=Cuebot.Timeout)

    def name(self):
        """Returns the filter name.

        :rtype:  str
        :return: the filter name
        """
        return self.data.name

    def type(self):
        """Returns the filter type.

        :rtype:  opencue_proto.filter_pb2.FilterType
        :return: the filter type
        """
        return self.data.type

    def order(self):
        """Returns the current position of the filter.

        :rtype:  float
        :return: the current position of the filter"""
        return self.data.order

    def isEnabled(self):
        """Returns whether the filter is enabled.

        :rtype:  bool
        :return: whether the filter is enabled
        """
        return self.data.enabled

    def id(self):
        """Returns the id of the filter.

        :rtype:  str
        :return: id of the filter
        """
        return self.data.id


class Action(object):
    """This class contains the grpc implementation related to an Action."""

    class ActionType(enum.IntEnum):
        """Enum representing the type of Action to be performed."""
        MOVE_JOB_TO_GROUP = filter_pb2.MOVE_JOB_TO_GROUP
        PAUSE_JOB = filter_pb2.PAUSE_JOB
        SET_JOB_MIN_CORES = filter_pb2.SET_JOB_MIN_CORES
        SET_JOB_MAX_CORES = filter_pb2.SET_JOB_MAX_CORES
        STOP_PROCESSING = filter_pb2.STOP_PROCESSING
        SET_JOB_PRIORITY = filter_pb2.SET_JOB_PRIORITY
        SET_ALL_RENDER_LAYER_TAGS = filter_pb2.SET_ALL_RENDER_LAYER_TAGS
        SET_ALL_RENDER_LAYER_MEMORY = filter_pb2.SET_ALL_RENDER_LAYER_MEMORY
        SET_ALL_RENDER_LAYER_MIN_CORES = filter_pb2.SET_ALL_RENDER_LAYER_MIN_CORES
        SET_ALL_RENDER_LAYER_MAX_CORES = filter_pb2.SET_ALL_RENDER_LAYER_MAX_CORES
        SET_MEMORY_OPTIMIZER = filter_pb2.SET_MEMORY_OPTIMIZER

    class ActionValueType(enum.IntEnum):
        """Enum representing the type of the action's object."""
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
        """Returns the filter the action belongs to.

        :rtype: opencue.wrappers.filter.Filter
        :return: the filter the action belongs to
        """
        response = self.stub.GetParentFilter(
            filter_pb2.ActionGetParentFilterRequest(action=self.data),
            timeout=Cuebot.Timeout)
        return Filter(response.filter)

    def delete(self):
        """Deletes the action."""
        self.stub.Delete(filter_pb2.ActionDeleteRequest(action=self.data), timeout=Cuebot.Timeout)

    def commit(self):
        """Commits any changes to the action to the database."""
        if self.isNew():
            raise Exception(
                "unable to commit action that has not been created, proxy does not exist")
        self.stub.Commit(filter_pb2.ActionCommitRequest(action=self.data), timeout=Cuebot.Timeout)

    def isNew(self):
        """Returns whether the action has been initialized yet.

        :rtype: bool
        :return: True if the action has been initialized with data from the database
        """
        return self.data is None

    def name(self):
        """Returns the name of the action.

        :rtype: str
        :return: name of the action
        """
        if self.value() is None:
            return "%s" % ActionType.Name(self.type())
        return "%s %s" % (ActionType.Name(self.type()), self.value())

    def value(self):
        """Returns the value of the action; what will happen if the filter is matched.

        Type of value returned depends on the action's value_type.

        :rtype: str/int/float/bool
        :return: value of the action
        """
        valueType = self.data.value_type
        if valueType == filter_pb2.GROUP_TYPE:
            return self.data.group_value
        if valueType == filter_pb2.STRING_TYPE:
            return self.data.string_value
        if valueType == filter_pb2.INTEGER_TYPE:
            return self.data.integer_value
        if valueType == filter_pb2.FLOAT_TYPE:
            return self.data.float_value
        if valueType == filter_pb2.BOOLEAN_TYPE:
            return self.data.boolean_value
        return None

    def type(self):
        """Returns the type of the action.

        An action's type determines what will happen if the action is triggered by its filter.
        For example, if the type is GROUP_TYPE, the object which has triggered the filter will
        be assigned to the group specified by the action's value.

        :rtype: filter_pb2.ActionValueType
        :return: the type of the action
        """
        return self.data.type

    def setTypeAndValue(self, actionType, value):
        """Sets a new type and value for the action.

        These fields should be set together as the value can be only be properly validated and
        stored in the correct database field if the type is also known.

        :type  actionType: filter_pb2.ActionValueType
        :param actionType: the new type of the action
        :type  value: str/int/float/bool
        :param value: the new value of the action
        """
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
                            filter_pb2.SET_ALL_RENDER_LAYER_MIN_CORES,
                            filter_pb2.SET_ALL_RENDER_LAYER_MAX_CORES):
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
        """Returns the id of the action.

        :rtype:  str
        :return: id of the action
        """
        return self.data.id


class Matcher(object):
    """This class contains the grpc implementation related to a Matcher.

    Matchers belong to a single filter, and indicate the conditions where a given object will
    satisfy that filter, i.e. if it will trigger the actions in that filter.
    """

    class MatchSubject(enum.IntEnum):
        """Enum representing the type of the subject; the thing being matched."""
        JOB_NAME = filter_pb2.JOB_NAME
        SHOW = filter_pb2.SHOW
        SHOT = filter_pb2.SHOT
        USER = filter_pb2.USER
        SERVICE_NAME = filter_pb2.SERVICE_NAME
        PRIORITY = filter_pb2.PRIORITY
        FACILITY = filter_pb2.FACILITY
        LAYER_NAME = filter_pb2.LAYER_NAME

    class MatchType(enum.IntEnum):
        """Enum representing the type of matching that will occur."""
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
        """Returns the filter the matcher belongs to.

        :rtype: opencue.wrappers.filter.Filter
        :return: the filter the matcher belongs to
        """
        response = self.stub.GetParentFilter(
            filter_pb2.MatcherGetParentFilterRequest(matcher=self.data),
            timeout=Cuebot.Timeout)
        return Filter(response.filter)

    def delete(self):
        """Deletes the matcher."""
        self.stub.Delete(filter_pb2.MatcherDeleteRequest(matcher=self.data), timeout=Cuebot.Timeout)

    def commit(self):
        """Commits any changes to the matcher to the database."""
        if self.isNew():
            raise Exception(
                "unable to commit matcher that has not been created, proxy does not exist")
        self.data.input = self.data.input.replace(" ", "")
        self.stub.Commit(filter_pb2.MatcherCommitRequest(matcher=self.data), timeout=Cuebot.Timeout)

    def isNew(self):
        """Returns whether the matcher has been initialized yet with data from the database.

        :rtype: bool
        :return: True if the matcher has been initialized
        """
        return self.data is None

    def name(self):
        """Returns the name of the matcher.

        :rtype: str
        :return: the name of the matcher
        """
        return "%s %s %s" % (
            MatchSubject.Name(self.data.subject), MatchType.Name(self.data.type), self.data.input)

    def subject(self):
        """Returns the subject of the matcher; the type of object to be matched.

        :rtype: filter_pb2.MatchSubject
        :return: the subject of the matcher
        """
        return self.data.subject

    def type(self):
        """Returns the type of the matcher; the kind of comparison used to determine a match.

        :rtype: filter_pb2.MatchType
        :return: the type of the matcher
        """
        return self.data.type

    def input(self):
        """Returns the input data of the matcher; the value to be matched against.

        :rtype: str
        :return: input data of the matcher
        """
        return self.data.input

    def id(self):
        """Returns the id of the matcher.

        :rtype:  str
        :return: id of the matcher
        """
        return self.data.id

    def setSubject(self, value):
        """Sets a new subject for the matcher.

        :type  value: str
        :param value: new subject for the matcher
        """
        self.data.subject = value
        self.commit()

    def setType(self, value):
        """Sets a new type for the matcher.

        :type  value: filter_pb2.MatchType
        :param value: new type for the matcher
        """
        self.data.type = value
        self.commit()

    def setInput(self, value):
        """Set new input data for the matcher.

        :type  value: str
        :param value: new input data for the matcher
        """
        value = value.replace(" ", "")
        self.data.input = str(value)
        self.commit()
