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
Project: Cue3 Library

Module: filter.py - Cue3 Library implementation of spank filter

Created: May 15, 2008

Contact: Middle-Tier Group (middle-tier@imageworks.com)

"""
from cue.CueIce import FilterType, MatchSubject, MatchType, ActionValueType, ActionType
from cue.CueClientIce import ActionData, MatcherData, FilterData
import cue.CueClientIce as CueClientIce

from ..api import *


__all__ = ["Filter", "Action", "Matcher",
           "FilterData", "ActionData", "MatcherData",
           "FilterType", "ActionType", "MatchType",
           "ActionValueType", "MatchSubject"]


class Filter(CueClientIce.Filter):
    """This class contains the ice implementation related to a spank Filter."""
    def __init__(self):
        """_Filter class initialization"""
        CueClientIce.Filter.__init__(self)

    def delete(self):
        """Deletes the filter"""
        self.proxy.delete()

    def createMatcher(self, subject, matchType, query):
        """Creates a matcher for this filter
        @type  subject: Cue3.MatchSubject.*
        @param subject: The job attribute to match
        @type  matchType: Cue3.MatchType.*
        @param matchType: The type of match to perform
        @type  query: string
        @param query: The value to match
        @rtype:  Matcher
        @return: The new matcher object"""
        m = MatcherData()
        m.subject = subject
        m.type = matchType
        m.input = query.replace(" ", "")
        return self.proxy.createMatcher(m)

    def createAction(self, actionType, value):
        """Creates an action for this filter.
        @type  actionType: Cue3.ActionType.*
        @param actionType: The action to perform
        @type  value: Group or str, or int or bool
        @param value: Value relevant to the type selected
        @rtype:  Action
        @return: The new Action object"""
        a = ActionData()
        a.type = actionType
        a.groupValue = None
        a.stringValue = None
        a.integerValue = 0
        a.floatValue = 0.0;
        a.booleanValue = False

        if isinstance(value, CueClientIce.Group):
            a.valueType = ActionValueType.GroupType
            a.groupValue = value.proxy
        elif isinstance(value, str):
            a.valueType = ActionValueType.StringType
            a.stringValue = value
        elif isinstance(value, bool):
            a.valueType = ActionValueType.BooleanType
            a.booleanValue = value
        elif isinstance(value, int):
            a.valueType = ActionValueType.IntegerType
            a.integerValue = value
        elif isinstance(value, float):
            a.valueType = ActionValueType.FloatType
            a.floatValue = value
        else:
            a.valueType = ActionValueType.NoneType

        return self.proxy.createAction(a)

    def getActions(self):
        """Returns the actions in this filter
        @rtype: list<Action>
        @return: A list of the actions in this filter"""
        return self.proxy.getActions()

    def getMatchers(self):
        """Returns the matchers in this filter
        @rtype:  list<Matcher>
        @return: A list of the matchers in this filter"""
        return self.proxy.getMatchers()

    def lowerOrder(self):
        """Lowers the order of this filter relative to the other filters"""
        self.proxy.lowerOrder()

    def raiseOrder(self):
        """Raises the order of this filter relative to the other filters"""
        self.proxy.raiseOrder()

    def orderFirst(self):
        """Orders this filter above all the other filters"""
        self.proxy.orderFirst()

    def orderLast(self):
        """Orders this filter below all the other filters"""
        self.proxy.orderLast()

    def runFilterOnGroup(self, group):
        self.proxy.runFilterOnGroup(group.proxy)

    def runFilterOnJobs(self, jobs):
        """Runs the filter on the list of jobs provided
        @type  jobs: list<JobInterfacePrx or Job or id or str jobname>
        @param jobs: The jobs to add to this group"""
        proxies = proxy(jobs, "Job")
        self.proxy.runFilterOnJobs(proxies)

    def setEnabled(self, value):
        """Enables or disables the filter
        @type  value: bool
        @param value: True to enable the filter and false to disable it"""
        self.proxy.setEnabled(value)

    def setName(self, name):
        """Sets the name of this filter
        @type  name: str
        @param name: The new name for this filter"""
        self.proxy.setName(name)

    def setType(self, filterType):
        """Changes the filter type
        @type  filterType: FilterType
        @param filterType: The new filter type"""
        self.proxy.setType(filterType)

    def setOrder(self, order):
        self.proxy.setOrder(order);

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
        return self.proxy.ice_getIdentity().name

class Action(CueClientIce.Action):
    def __init__(self):
        CueClientIce.Action.__init__(self)

    def getParentFilter():
        return self.proxy.getParentFilter()

    def delete(self):
        self.proxy.delete()

    def commit(self):
        if self.isNew():
            raise Exception("unable to commit action that has not been created, proxy does not exist")
        self.proxy.commit(self.data)

    def isNew(self):
        return self.proxy is None

    def name(self):
        if self.value() is None:
            return "%s" % self.type()
        else:
            return "%s %s" % (self.type(), self.value())

    def value(self):
        valueType = str(self.data.valueType)
        if valueType == "GroupType":
            return self.data.groupValue.ice_getIdentity().name
        elif valueType == "StringType":
            return self.data.stringValue
        elif valueType == "IntegerType":
            return self.data.integerValue
        elif valueType == "FloatType":
            return self.data.floatValue
        elif valueType == "BooleanType":
            return self.data.booleanValue
        else:
            return None

    def type(self):
        return self.data.type

    def setTypeAndValue(self, actionType, value):
        self.data.type = actionType
        if actionType in (ActionType.MoveJobToGroup,):
            if not isinstance(value, CueClientIce.Group):
                raise TypeError("invalid group argument, not a group")
            if not value.proxy:
                raise ValueError("group did not have a valid proxy")
            self.data.groupValue = value.proxy
            self.data.valueType =  ActionValueType.GroupType

        elif actionType in (ActionType.PauseJob,):
            self.data.booleanValue = value
            self.data.valueType =  ActionValueType.BooleanType

        elif actionType in (ActionType.SetJobPriority,
                            ActionType.SetAllRenderLayerMemory):
            self.data.integerValue = int(value)
            self.data.valueType =  ActionValueType.IntegerType

        elif actionType in (ActionType.SetJobMinCores,
                            ActionType.SetJobMaxCores,
                            ActionType.SetAllRenderLayerCores):
            self.data.floatValue = float(value)
            self.data.valueType = ActionValueType.FloatType

        elif actionType in (ActionType.SetAllRenderLayerTags,):
            self.data.stringValue = value
            self.data.valueType =  ActionValueType.StringType

        elif actionType in (ActionType.StopProcessing,):
            self.data.valueType =  ActionValueType.NoneType

        elif actionType in (ActionType.SetMemoryOptimizer,):
            self.data.booleanValue = value
            self.data.valueType = ActionValueType.BooleanType

        else:
           raise Exception("invalid action type: %s" % actionType)

        self.commit()

    def id(self):
        """Returns the id of the action
        @rtype:  str
        @return: Action uuid"""
        return self.proxy.ice_getIdentity().name

class Matcher(CueClientIce.Matcher):
    def __init__(self):
        CueClientIce.Matcher.__init__(self)

    def getParentFilter():
        return self.proxy.getParentFilter()

    def delete(self):
        self.proxy.delete()

    def commit(self):
        if self.isNew():
            raise Exception("unable to commit matcher that has not been created, proxy does not exist")
        self.data.input = self.data.input.replace(" ", "")
        self.proxy.commit(self.data)

    def isNew(self):
        return self.proxy is None

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
        return self.proxy.ice_getIdentity().name

    def setSubject(self, value):
        self.data.subject = value
        self.proxy.commit(self.data)

    def setType(self, value):
        self.data.type = value
        self.proxy.commit(self.data)

    def setInput(self, value):
        value = value.replace(" ", "")
        self.data.input = str(value)
        self.proxy.commit(self.data)

