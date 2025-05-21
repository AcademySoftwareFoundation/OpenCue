#!/usr/bin/env python

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

"""Tests for `opencue.wrappers.host`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import os
import unittest

import mock

from opencue_proto import comment_pb2
from opencue_proto import facility_pb2
from opencue_proto import host_pb2
from opencue_proto import renderPartition_pb2
import opencue.wrappers.allocation
import opencue.wrappers.host


TEST_HOST_NAME = 'testHost'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class HostTests(unittest.TestCase):

    def testLock(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Lock.return_value = host_pb2.HostLockResponse()
        getStubMock.return_value = stubMock

        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.lock()

        stubMock.Lock.assert_called_with(
            host_pb2.HostLockRequest(host=host.data),
            timeout=mock.ANY)

    def testUnlock(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Unlock.return_value = host_pb2.HostUnlockResponse()
        getStubMock.return_value = stubMock

        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.unlock()

        stubMock.Unlock.assert_called_with(
            host_pb2.HostUnlockRequest(host=host.data),
            timeout=mock.ANY)

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = host_pb2.HostDeleteResponse()
        getStubMock.return_value = stubMock

        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.delete()

        stubMock.Delete.assert_called_with(
            host_pb2.HostDeleteRequest(host=host.data),
            timeout=mock.ANY)

    def testGetProcs(self, getStubMock):
        procName = 'testProc'
        stubMock = mock.Mock()
        stubMock.GetProcs.return_value = host_pb2.HostGetProcsResponse(
            procs=host_pb2.ProcSeq(procs=[host_pb2.Proc(name=procName)]))
        getStubMock.return_value = stubMock

        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        procs = host.getProcs()

        stubMock.GetProcs.assert_called_with(
            host_pb2.HostGetProcsRequest(host=host.data),
            timeout=mock.ANY)
        self.assertEqual(len(procs), 1)
        self.assertEqual(procs[0].name(), procName)

    def testGetRenderPartitions(self, getStubMock):
        renderPartId = 'rpr-rprp-rpr'
        stubMock = mock.Mock()
        stubMock.GetRenderPartitions.return_value = host_pb2.HostGetRenderPartitionsResponse(
            render_partitions=renderPartition_pb2.RenderPartitionSeq(
                render_partitions=[renderPartition_pb2.RenderPartition(id=renderPartId)]))
        getStubMock.return_value = stubMock

        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        renderParts = host.getRenderPartitions()

        stubMock.GetRenderPartitions.assert_called_with(
            host_pb2.HostGetRenderPartitionsRequest(host=host.data),
            timeout=mock.ANY)
        self.assertEqual(len(renderParts), 1)
        self.assertEqual(renderParts[0].data.id, renderPartId)

    def testRebootWhenIdle(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.RebootWhenIdle.return_value = host_pb2.HostRebootWhenIdleResponse()
        getStubMock.return_value = stubMock

        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.rebootWhenIdle()

        stubMock.RebootWhenIdle.assert_called_with(
            host_pb2.HostRebootWhenIdleRequest(host=host.data),
            timeout=mock.ANY)

    def testReboot(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Reboot.return_value = host_pb2.HostRebootResponse()
        getStubMock.return_value = stubMock

        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.reboot()

        stubMock.Reboot.assert_called_with(
            host_pb2.HostRebootRequest(host=host.data),
            timeout=mock.ANY)

    def testAddTags(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.AddTags.return_value = host_pb2.HostAddTagsResponse()
        getStubMock.return_value = stubMock

        tags = ['tags', 'are', 'fun']
        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.addTags(tags)

        stubMock.AddTags.assert_called_with(
            host_pb2.HostAddTagsRequest(host=host.data, tags=tags),
            timeout=mock.ANY)

    def testRemoveTags(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.RemoveTags.return_value = host_pb2.HostRemoveTagsResponse()
        getStubMock.return_value = stubMock

        tags = ['tags', 'are', 'fun']
        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.removeTags(tags)

        stubMock.RemoveTags.assert_called_with(
            host_pb2.HostRemoveTagsRequest(host=host.data, tags=tags),
            timeout=mock.ANY)

    def testRenameTag(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.RenameTag.return_value = host_pb2.HostRenameTagResponse()
        getStubMock.return_value = stubMock

        oldTag = 'sad'
        newTag = 'happy'
        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.renameTag(oldTag, newTag)

        stubMock.RenameTag.assert_called_with(
            host_pb2.HostRenameTagRequest(host=host.data, old_tag=oldTag, new_tag=newTag),
            timeout=mock.ANY)

    def testSetAllocation(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetAllocation.return_value = host_pb2.HostSetAllocationResponse()
        getStubMock.return_value = stubMock

        allocId = 'aaa-aaaa-aaa'
        alloc = opencue.wrappers.allocation.Allocation(facility_pb2.Allocation(id=allocId))
        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.setAllocation(alloc)

        stubMock.SetAllocation.assert_called_with(
            host_pb2.HostSetAllocationRequest(host=host.data, allocation_id=alloc.id()),
            timeout=mock.ANY)

    def testAddComment(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.AddComment.return_value = host_pb2.HostAddCommentResponse()
        getStubMock.return_value = stubMock

        subject = 'test'
        message = 'this is a test.'
        comment = comment_pb2.Comment(user=os.getenv("USER", "unknown"),
                                      subject=subject,
                                      message=message,
                                      timestamp=0)
        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.addComment(subject, message)

        stubMock.AddComment.assert_called_with(
            host_pb2.HostAddCommentRequest(host=host.data, new_comment=comment),
            timeout=mock.ANY)

    def testGetComments(self, getStubMock):
        message = 'this is a test.'
        stubMock = mock.Mock()
        stubMock.GetComments.return_value = host_pb2.HostGetCommentsResponse(
            comments=comment_pb2.CommentSeq(comments=[comment_pb2.Comment(message=message)]))
        getStubMock.return_value = stubMock

        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        comments = host.getComments()

        stubMock.GetComments.assert_called_with(
            host_pb2.HostGetCommentsRequest(host=host.data),
            timeout=mock.ANY)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].message(), message)

    def testSetHardwareState(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetHardwareState.return_value = host_pb2.HostSetHardwareStateResponse()
        getStubMock.return_value = stubMock

        state = host_pb2.REBOOTING
        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.setHardwareState(state)

        stubMock.SetHardwareState.assert_called_with(
            host_pb2.HostSetHardwareStateRequest(host=host.data, state=state),
            timeout=mock.ANY)

    def testSetOs(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetOs.return_value = host_pb2.HostSetOsResponse()
        getStubMock.return_value = stubMock

        osName = 'linux'
        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.setOs(osName)

        stubMock.SetOs.assert_called_with(
            host_pb2.HostSetOsRequest(host=host.data, os=osName),
            timeout=mock.ANY)

    def testSetThreadMode(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetThreadMode.return_value = host_pb2.HostSetThreadModeResponse()
        getStubMock.return_value = stubMock

        mode = host_pb2.VARIABLE
        host = opencue.wrappers.host.Host(
            host_pb2.Host(name=TEST_HOST_NAME))
        host.setThreadMode(mode)

        stubMock.SetThreadMode.assert_called_with(
            host_pb2.HostSetThreadModeRequest(host=host.data, mode=mode),
            timeout=mock.ANY)


class HostEnumTests(unittest.TestCase):

    def testHardwareState(self):
        self.assertEqual(opencue.api.Host.HardwareState.UP, host_pb2.UP)
        self.assertEqual(opencue.api.Host.HardwareState.UP, 0)

    def testHostTagType(self):
        self.assertEqual(opencue.api.Host.HostTagType.HARDWARE,
                         host_pb2.HARDWARE)
        self.assertEqual(opencue.api.Host.HostTagType.HARDWARE, 1)

    def testLockState(self):
        self.assertEqual(opencue.api.Host.LockState.NIMBY_LOCKED,
                         host_pb2.NIMBY_LOCKED)
        self.assertEqual(opencue.api.Host.LockState.NIMBY_LOCKED, 2)

    def testThreadMode(self):
        self.assertEqual(opencue.api.Host.ThreadMode.ALL,
                         host_pb2.ALL)
        self.assertEqual(opencue.api.Host.ThreadMode.ALL, 1)


if __name__ == '__main__':
    unittest.main()
