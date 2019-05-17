#!/usr/bin/env python

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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import mock
import unittest

import opencue
from opencue.compiled_proto import filter_pb2
from opencue.compiled_proto import job_pb2


TEST_ACTION_ID = 'aaa-aaaa-aaa'
TEST_FILTER_NAME = 'testFilter'
TEST_MATCHER_ID = 'mmm-mmmm-mmm'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class FilterTests(unittest.TestCase):

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = filter_pb2.FilterDeleteResponse()
        getStubMock.return_value = stubMock

        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.delete()

        stubMock.Delete.assert_called_with(
            filter_pb2.FilterDeleteRequest(filter=filter.data), timeout=mock.ANY)

    def testCreateMatcher(self, getStubMock):
        matcherId = 'mmm-mmmm-mmm'
        stubMock = mock.Mock()
        stubMock.CreateMatcher.return_value = filter_pb2.FilterCreateMatcherResponse(
            matcher=filter_pb2.Matcher(id=matcherId))
        getStubMock.return_value = stubMock

        queryStr = 'john'
        subject = filter_pb2.USER
        matcherType = filter_pb2.IS_NOT
        matcherData = opencue.wrappers.filter.MatcherData(subject=subject,
                                                          type=matcherType,
                                                          input=queryStr)
        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        matcher = filter.createMatcher(subject, matcherType, queryStr)

        stubMock.CreateMatcher.assert_called_with(
            filter_pb2.FilterCreateMatcherRequest(filter=filter.data, data=matcherData),
            timeout=mock.ANY)
        self.assertEqual(matcher.id(), matcherId)

    def testCreateAction(self, getStubMock):
        actionId = 'aaa-aaaa-aaa'
        stubMock = mock.Mock()
        stubMock.CreateAction.return_value = filter_pb2.FilterCreateActionResponse(
            action=filter_pb2.Action(id=actionId))
        getStubMock.return_value = stubMock

        actionType = filter_pb2.PAUSE_JOB
        value = 10
        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        action = filter.createAction(actionType, value)
        actionData = opencue.wrappers.filter.ActionData(
            type=actionType,
            value_type=filter_pb2.INTEGER_TYPE,
            group_value=None,
            string_value=None,
            integer_value=value,
            float_value=0.0,
            boolean_value=False)

        stubMock.CreateAction.assert_called_with(
            filter_pb2.FilterCreateActionRequest(filter=filter.data, data=actionData),
            timeout=mock.ANY)
        self.assertEqual(action.id(), actionId)

    def testGetActions(self, getStubMock):
        actionId = 'aaa-aaaa-aaa'
        stubMock = mock.Mock()
        stubMock.GetActions.return_value = filter_pb2.FilterGetActionsResponse(
            actions=filter_pb2.ActionSeq(actions=[filter_pb2.Action(id=actionId)]))
        getStubMock.return_value = stubMock

        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        actions = filter.getActions()

        stubMock.GetActions.assert_called_with(
            filter_pb2.FilterGetActionsRequest(filter=filter.data), timeout=mock.ANY)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].id(), actionId)

    def testGetMatchers(self, getStubMock):
        matcherId = 'mmm-mmmm-mmm'
        stubMock = mock.Mock()
        stubMock.GetMatchers.return_value = filter_pb2.FilterGetMatchersResponse(
            matchers=filter_pb2.MatcherSeq(matchers=[filter_pb2.Matcher(id=matcherId)]))
        getStubMock.return_value = stubMock

        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        matchers = filter.getMatchers()

        stubMock.GetMatchers.assert_called_with(
            filter_pb2.FilterGetMatchersRequest(filter=filter.data), timeout=mock.ANY)
        self.assertEqual(len(matchers), 1)
        self.assertEqual(matchers[0].id(), matcherId)

    def testLowerOrder(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.LowerOrder.return_value = filter_pb2.FilterLowerOrderResponse()
        getStubMock.return_value = stubMock

        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.lowerOrder()

        stubMock.LowerOrder.assert_called_with(
            filter_pb2.FilterLowerOrderRequest(filter=filter.data), timeout=mock.ANY)

    def testRaiseOrder(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.RaiseOrder.return_value = filter_pb2.FilterRaiseOrderResponse()
        getStubMock.return_value = stubMock

        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.raiseOrder()

        stubMock.RaiseOrder.assert_called_with(
            filter_pb2.FilterRaiseOrderRequest(filter=filter.data), timeout=mock.ANY)

    def testOrderFirst(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.OrderFirst.return_value = filter_pb2.FilterOrderFirstResponse()
        getStubMock.return_value = stubMock

        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.orderFirst()

        stubMock.OrderFirst.assert_called_with(
            filter_pb2.FilterOrderFirstRequest(filter=filter.data), timeout=mock.ANY)

    def testOrderLast(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.OrderLast.return_value = filter_pb2.FilterOrderLastResponse()
        getStubMock.return_value = stubMock

        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.orderLast()

        stubMock.OrderLast.assert_called_with(
            filter_pb2.FilterOrderLastRequest(filter=filter.data), timeout=mock.ANY)

    def testOrderLast(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.OrderLast.return_value = filter_pb2.FilterOrderLastResponse()
        getStubMock.return_value = stubMock

        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.orderLast()

        stubMock.OrderLast.assert_called_with(
            filter_pb2.FilterOrderLastRequest(filter=filter.data), timeout=mock.ANY)

    def testRunFilterOnGroup(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.RunFilterOnGroup.return_value = filter_pb2.FilterRunFilterOnGroupResponse()
        getStubMock.return_value = stubMock

        group = job_pb2.Group(name='testGroup')
        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.runFilterOnGroup(group)

        stubMock.RunFilterOnGroup.assert_called_with(
            filter_pb2.FilterRunFilterOnGroupRequest(filter=filter.data, group=group),
            timeout=mock.ANY)

    def testRunFilterOnJobs(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.RunFilterOnJobs.return_value = filter_pb2.FilterRunFilterOnJobsResponse()
        getStubMock.return_value = stubMock

        jobs = [job_pb2.Job(name='testJob')]
        jobSeq = job_pb2.JobSeq(jobs=jobs)
        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.runFilterOnJobs(jobs)

        stubMock.RunFilterOnJobs.assert_called_with(
            filter_pb2.FilterRunFilterOnJobsRequest(filter=filter.data, jobs=jobSeq),
            timeout=mock.ANY)

    def testSetEnabled(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetEnabled.return_value = filter_pb2.FilterSetEnabledResponse()
        getStubMock.return_value = stubMock

        value = True
        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.setEnabled(value)

        stubMock.SetEnabled.assert_called_with(
            filter_pb2.FilterSetEnabledRequest(filter=filter.data, enabled=value), timeout=mock.ANY)

    def testSetName(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetName.return_value = filter_pb2.FilterSetNameResponse()
        getStubMock.return_value = stubMock

        value = 'newname'
        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.setName(value)

        stubMock.SetName.assert_called_with(
            filter_pb2.FilterSetNameRequest(filter=filter.data, name=value), timeout=mock.ANY)

    def testSetType(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetType.return_value = filter_pb2.FilterSetTypeResponse()
        getStubMock.return_value = stubMock

        value = filter_pb2.MATCH_ALL
        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.setType(value)

        stubMock.SetType.assert_called_with(
            filter_pb2.FilterSetTypeRequest(filter=filter.data, type=value), timeout=mock.ANY)

    def testSetOrder(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetOrder.return_value = filter_pb2.FilterSetOrderResponse()
        getStubMock.return_value = stubMock

        value = 2
        filter = opencue.wrappers.filter.Filter(
            filter_pb2.Filter(name=TEST_FILTER_NAME))
        filter.setOrder(value)

        stubMock.SetOrder.assert_called_with(
            filter_pb2.FilterSetOrderRequest(filter=filter.data, order=value), timeout=mock.ANY)


@mock.patch('opencue.cuebot.Cuebot.getStub')
class ActionTests(unittest.TestCase):

    def testGetParentFilter(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetParentFilter.return_value = filter_pb2.ActionGetParentFilterResponse(
            filter=filter_pb2.Filter(name=TEST_FILTER_NAME))
        getStubMock.return_value = stubMock

        action = opencue.wrappers.filter.Action(
            filter_pb2.Action(id=TEST_ACTION_ID))
        filter = action.getParentFilter()

        stubMock.GetParentFilter.assert_called_with(
            filter_pb2.ActionGetParentFilterRequest(action=action.data), timeout=mock.ANY)
        self.assertEqual(filter.name(), TEST_FILTER_NAME)

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = filter_pb2.ActionDeleteResponse()
        getStubMock.return_value = stubMock

        action = opencue.wrappers.filter.Action(
            filter_pb2.Action(id=TEST_ACTION_ID))
        action.delete()

        stubMock.Delete.assert_called_with(
            filter_pb2.ActionDeleteRequest(action=action.data), timeout=mock.ANY)

    def testCommitNew(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Commit.return_value = filter_pb2.ActionCommitResponse()
        getStubMock.return_value = stubMock

        action = opencue.wrappers.filter.Action()
        with self.assertRaises(Exception):
            action.commit()

    def testCommit(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Commit.return_value = filter_pb2.ActionCommitResponse()
        getStubMock.return_value = stubMock

        action = opencue.wrappers.filter.Action(filter_pb2.Action(id=TEST_ACTION_ID))
        action.commit()

        stubMock.Commit.assert_called_with(
            filter_pb2.ActionCommitRequest(action=action.data), timeout=mock.ANY)

    def testIsNew(self, getStubMock):
        actionFalse = opencue.wrappers.filter.Action(filter_pb2.Action(id=TEST_ACTION_ID))
        self.assertFalse(actionFalse.isNew())

        actionTrue = opencue.wrappers.filter.Action()
        self.assertTrue(actionTrue.isNew())

    def testName(self, getStubMock):
        actionInt = opencue.wrappers.filter.Action(filter_pb2.Action(
            id=TEST_ACTION_ID, type=filter_pb2.PAUSE_JOB, value_type=filter_pb2.INTEGER_TYPE,
            integer_value=22))
        expected = "1 22"
        self.assertEqual(actionInt.name(), expected)

        actionNone = opencue.wrappers.filter.Action(filter_pb2.Action(
            id=TEST_ACTION_ID, type=filter_pb2.PAUSE_JOB, value_type=filter_pb2.NONE_TYPE))
        self.assertEqual(actionNone.name(), str(actionNone.type()))

    def testValue(self, getStubMock):
        groupValue = 'testGroup'
        stringValue = 'testString'
        intValue = 22
        floatValue = 22.2
        boolValue = True
        action = opencue.wrappers.filter.Action(
            filter_pb2.Action(
                id=TEST_ACTION_ID,
                type=filter_pb2.PAUSE_JOB,
                group_value=groupValue,
                string_value=stringValue,
                integer_value=intValue,
                float_value=floatValue,
                boolean_value=boolValue))

        action.data.value_type = filter_pb2.GROUP_TYPE
        self.assertEqual(action.value(), groupValue)

        action.data.value_type = filter_pb2.STRING_TYPE
        self.assertEqual(action.value(), stringValue)

        action.data.value_type = filter_pb2.INTEGER_TYPE
        self.assertEqual(action.value(), intValue)

        action.data.value_type = filter_pb2.FLOAT_TYPE
        threshold = abs(action.value() - floatValue)
        self.assertTrue(threshold < 0.0001)

        action.data.value_type = filter_pb2.BOOLEAN_TYPE
        self.assertEqual(action.value(), boolValue)

        action.data.value_type = filter_pb2.NONE_TYPE
        self.assertEqual(action.value(), None)

    def testSetTypeAndValueFail(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Commit.return_value = filter_pb2.ActionCommitResponse()
        getStubMock.return_value = stubMock

        action = opencue.wrappers.filter.Action(filter_pb2.Action(id=TEST_ACTION_ID))

        with self.assertRaises(Exception):
            action.setTypeAndValue('foo', 'bar')

    def testSetTypeAndValueGroup(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Commit.return_value = filter_pb2.ActionCommitResponse()
        getStubMock.return_value = stubMock

        testData = (filter_pb2.MOVE_JOB_TO_GROUP, job_pb2.Group(id='testGroup'))
        action = opencue.wrappers.filter.Action(filter_pb2.Action(id=TEST_ACTION_ID))

        action.setTypeAndValue(testData[0], testData[1])
        stubMock.Commit.assert_called_with(
            filter_pb2.ActionCommitRequest(action=action.data), timeout=mock.ANY)

    def testSetTypeAndValueString(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Commit.return_value = filter_pb2.ActionCommitResponse()
        getStubMock.return_value = stubMock

        testData = (filter_pb2.SET_ALL_RENDER_LAYER_TAGS, 'testString')
        action = opencue.wrappers.filter.Action(filter_pb2.Action(id=TEST_ACTION_ID))

        action.setTypeAndValue(testData[0], testData[1])
        stubMock.Commit.assert_called_with(
            filter_pb2.ActionCommitRequest(action=action.data), timeout=mock.ANY)

    def testSetTypeAndValueInt(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Commit.return_value = filter_pb2.ActionCommitResponse()
        getStubMock.return_value = stubMock

        testData = (filter_pb2.SET_JOB_PRIORITY, 22)
        action = opencue.wrappers.filter.Action(filter_pb2.Action(id=TEST_ACTION_ID))

        action.setTypeAndValue(testData[0], testData[1])
        stubMock.Commit.assert_called_with(
            filter_pb2.ActionCommitRequest(action=action.data), timeout=mock.ANY)

    def testSetTypeAndValueFloat(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Commit.return_value = filter_pb2.ActionCommitResponse()
        getStubMock.return_value = stubMock

        testData = (filter_pb2.SET_JOB_MIN_CORES, 22.2)
        action = opencue.wrappers.filter.Action(filter_pb2.Action(id=TEST_ACTION_ID))

        action.setTypeAndValue(testData[0], testData[1])
        stubMock.Commit.assert_called_with(
            filter_pb2.ActionCommitRequest(action=action.data), timeout=mock.ANY)

    def testSetTypeAndValueBool(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Commit.return_value = filter_pb2.ActionCommitResponse()
        getStubMock.return_value = stubMock

        testData = (filter_pb2.PAUSE_JOB, True)
        action = opencue.wrappers.filter.Action(filter_pb2.Action(id=TEST_ACTION_ID))

        action.setTypeAndValue(testData[0], testData[1])
        stubMock.Commit.assert_called_with(
            filter_pb2.ActionCommitRequest(action=action.data), timeout=mock.ANY)

    def testSetTypeAndValueNone(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Commit.return_value = filter_pb2.ActionCommitResponse()
        getStubMock.return_value = stubMock

        testData = (filter_pb2.STOP_PROCESSING, None)
        action = opencue.wrappers.filter.Action(filter_pb2.Action(id=TEST_ACTION_ID))

        action.setTypeAndValue(testData[0], testData[1])
        stubMock.Commit.assert_called_with(
            filter_pb2.ActionCommitRequest(action=action.data), timeout=mock.ANY)


@mock.patch('opencue.cuebot.Cuebot.getStub')
class MatcherTests(unittest.TestCase):

    def testGetParentFilter(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetParentFilter.return_value = filter_pb2.MatcherGetParentFilterResponse(
            filter=filter_pb2.Filter(name=TEST_FILTER_NAME))
        getStubMock.return_value = stubMock

        matcher = opencue.wrappers.filter.Matcher(
            filter_pb2.Matcher(id=TEST_MATCHER_ID))
        filter = matcher.getParentFilter()

        stubMock.GetParentFilter.assert_called_with(
            filter_pb2.MatcherGetParentFilterRequest(matcher=matcher.data), timeout=mock.ANY)
        self.assertEqual(filter.name(), TEST_FILTER_NAME)

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = filter_pb2.MatcherDeleteResponse()
        getStubMock.return_value = stubMock

        matcher = opencue.wrappers.filter.Matcher(
            filter_pb2.Matcher(id=TEST_MATCHER_ID))
        matcher.delete()

        stubMock.Delete.assert_called_with(
            filter_pb2.MatcherDeleteRequest(matcher=matcher.data), timeout=mock.ANY)

    def testCommitNew(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = filter_pb2.MatcherDeleteResponse()
        getStubMock.return_value = stubMock

        matcher = opencue.wrappers.filter.Matcher()
        with self.assertRaises(Exception):
            matcher.commit()

    def testCommit(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Commit.return_value = filter_pb2.MatcherCommitResponse()
        getStubMock.return_value = stubMock

        matcher = opencue.wrappers.filter.Matcher(
            filter_pb2.Matcher(id=TEST_MATCHER_ID, input='test'))
        matcher.commit()

        stubMock.Commit.assert_called_with(
            filter_pb2.MatcherCommitRequest(matcher=matcher.data), timeout=mock.ANY)

    def testIsNew(self, getStubMock):
        matcherFalse = opencue.wrappers.filter.Matcher(
            filter_pb2.Matcher(id=TEST_MATCHER_ID, input='test'))
        self.assertFalse(matcherFalse.isNew())

        matcherTrue = opencue.wrappers.filter.Matcher()
        self.assertTrue(matcherTrue.isNew())


if __name__ == '__main__':
    unittest.main()
