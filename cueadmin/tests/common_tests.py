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


import mock
import unittest

import opencue.compiled_proto.show_pb2
import opencue.wrappers.show
import cueadmin.common


TEST_SHOW = 'test_show'
TEST_FACILITY = 'some-non-default-facility'
TEST_ALLOC = 'test_alloc'


class ShowTests(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    @mock.patch('opencue.api.createShow')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testCreateShow(self, getStubMock, createShowMock):
        args = self.parser.parse_args(['-create-show', TEST_SHOW, '-force'])

        cueadmin.common.handleArgs(args)

        createShowMock.assert_called_with(TEST_SHOW)

    @mock.patch('opencue.api.findShow')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testDeleteShow(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-delete-show', TEST_SHOW, '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.delete.assert_called_with()

    @mock.patch('opencue.api.findShow')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testEnableBooking(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-booking', TEST_SHOW, 'on', '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.enableBooking.assert_called_with(True)

    @mock.patch('opencue.api.findShow')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testDisableBooking(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-booking', TEST_SHOW, 'off', '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.enableBooking.assert_called_with(False)

    @mock.patch('opencue.api.findShow')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testEnableDispatch(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-dispatching', TEST_SHOW, 'on', '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.enableDispatching.assert_called_with(True)

    @mock.patch('opencue.api.findShow')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testDisableDispatch(self, getStubMock, findShowMock):
        args = self.parser.parse_args(['-dispatching', TEST_SHOW, 'off', '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.enableDispatching.assert_called_with(False)

    @mock.patch('opencue.api.findShow')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testDefaultMinCores(self, getStubMock, findShowMock):
        arbitraryCoreCount = 873
        args = self.parser.parse_args(
            ['-default-min-cores', TEST_SHOW, str(arbitraryCoreCount), '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.setDefaultMinCores.assert_called_with(arbitraryCoreCount)

    @mock.patch('opencue.api.findShow')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testDefaultMaxCores(self, getStubMock, findShowMock):
        arbitraryCoreCount = 9349
        args = self.parser.parse_args(
            ['-default-max-cores', TEST_SHOW, str(arbitraryCoreCount), '-force'])
        showMock = mock.Mock()
        findShowMock.return_value = showMock

        cueadmin.common.handleArgs(args)

        showMock.setDefaultMaxCores.assert_called_with(arbitraryCoreCount)


class AllocTests(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    @mock.patch('opencue.api.createAllocation')
    @mock.patch('opencue.api.getFacility')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testCreateAlloc(self, getStubMock, getFacilityMock, createAllocMock):
        tagName = 'random-tag'
        args = self.parser.parse_args(
            ['-create-alloc', TEST_FACILITY, TEST_ALLOC, tagName, '-force'])
        facMock = mock.Mock()
        getFacilityMock.return_value = facMock

        cueadmin.common.handleArgs(args)

        getFacilityMock.assert_called_with(TEST_FACILITY)
        createAllocMock.assert_called_with(TEST_ALLOC, tagName, facMock)

    @mock.patch('opencue.api.findAllocation')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testDeleteAlloc(self, getStubMock, findAllocMock):
        args = self.parser.parse_args(
            ['-delete-alloc', '%s.%s' % (TEST_FACILITY, TEST_ALLOC), '-force'])
        allocMock = mock.Mock()
        findAllocMock.return_value = allocMock

        cueadmin.common.handleArgs(args)

        allocMock.delete.assert_called_with()

    @mock.patch('opencue.api.findAllocation')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testRenameAlloc(self, getStubMock, findAllocMock):
        oldFullName = '%s.%s' % (TEST_FACILITY, TEST_ALLOC)
        newName = 'some_new_alloc_name'
        newFullName = '%s.%s' % (TEST_FACILITY, newName)
        args = self.parser.parse_args(['-rename-alloc', oldFullName, newFullName, '-force'])
        allocMock = mock.Mock()
        findAllocMock.return_value = allocMock

        cueadmin.common.handleArgs(args)

        findAllocMock.assert_called_with(oldFullName)
        allocMock.setName.assert_called_with(newName)

    @mock.patch('opencue.api.findAllocation')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testTagAlloc(self):
        tagName = "new_tag"
        args = self.parser.parse_args(["-tag-alloc", entity, new_tag, "-force"])

        deleteAlloc(entity)

        facility.createAllocation("test_alloc", entity)
        common.handleArgs(args)
        s = opencue.api.findAllocation(entity)
        self.assertEqual(s.data.tag, new_tag)
        s.delete()
