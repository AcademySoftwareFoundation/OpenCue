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

"""Tests for `opencue.wrappers.layer`"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import getpass
import os
import platform
import unittest

import mock

from opencue_proto import depend_pb2
from opencue_proto import job_pb2
import opencue.wrappers.frame
import opencue.wrappers.layer
import opencue.wrappers.job


TEST_LAYER_NAME = 'testLayer'
TEST_OUTPUT_PATH = '/path/to/file.txt'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class LayerTests(unittest.TestCase):
    """Tests for `opencue.wrappers.layer.Layer`."""

    def testKill(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.KillFrames.return_value = job_pb2.LayerKillFramesResponse()
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        username = getpass.getuser()
        pid = os.getpid()
        host_kill = platform.uname()[1]
        reason = "Frames Kill Request"
        layer.kill(username=username, pid=pid, host_kill=host_kill, reason=reason)

        stubMock.KillFrames.assert_called_with(
            job_pb2.LayerKillFramesRequest(layer=layer.data,
                                           username=username,
                                           pid=str(pid),
                                           host_kill=host_kill,
                                           reason=reason), timeout=mock.ANY)

    def testEat(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.EatFrames.return_value = job_pb2.LayerEatFramesResponse()
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.eat()

        stubMock.EatFrames.assert_called_with(
            job_pb2.LayerEatFramesRequest(layer=layer.data), timeout=mock.ANY)

    def testRetry(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.RetryFrames.return_value = job_pb2.LayerRetryFramesResponse()
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.retry()

        stubMock.RetryFrames.assert_called_with(
            job_pb2.LayerRetryFramesRequest(layer=layer.data), timeout=mock.ANY)

    def testMarkdone(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.MarkdoneFrames.return_value = job_pb2.LayerMarkdoneFramesResponse()
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.markdone()

        stubMock.MarkdoneFrames.assert_called_with(
            job_pb2.LayerMarkdoneFramesRequest(layer=layer.data), timeout=mock.ANY)

    def testAddLimit(self, getStubMock):
        test_limit_id = 'lll-llll-lll'
        stubMock = mock.Mock()
        stubMock.AddLimit.return_value = job_pb2.LayerAddLimitResponse()
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.addLimit(test_limit_id)

        stubMock.AddLimit.assert_called_with(
            job_pb2.LayerAddLimitRequest(layer=layer.data, limit_id=test_limit_id),
            timeout=mock.ANY)

    def testDropLimit(self, getStubMock):
        test_limit_id = 'lll-llll-lll'
        stubMock = mock.Mock()
        stubMock.DropLimit.return_value = job_pb2.LayerDropLimitResponse()
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.dropLimit(test_limit_id)

        stubMock.DropLimit.assert_called_with(
            job_pb2.LayerDropLimitRequest(layer=layer.data, limit_id=test_limit_id),
            timeout=mock.ANY)

    def testEnableMemoryOptimizerTrue(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.EnableMemoryOptimizer.return_value = job_pb2.LayerEnableMemoryOptimizerResponse()
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.enableMemoryOptimizer(True)

        stubMock.EnableMemoryOptimizer.assert_called_with(
            job_pb2.LayerEnableMemoryOptimizerRequest(layer=layer.data, value=True),
            timeout=mock.ANY)

    def testEnableMemoryOptimizerFalse(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.EnableMemoryOptimizer.return_value = job_pb2.LayerEnableMemoryOptimizerResponse()
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.enableMemoryOptimizer(False)

        stubMock.EnableMemoryOptimizer.assert_called_with(
            job_pb2.LayerEnableMemoryOptimizerRequest(layer=layer.data, value=False),
            timeout=mock.ANY)

    def testGetFrames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetFrames.return_value = job_pb2.LayerGetFramesResponse(
            frames=job_pb2.FrameSeq(frames=[job_pb2.Frame(layer_name=TEST_LAYER_NAME)]))
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        frames = layer.getFrames()

        stubMock.GetFrames.assert_called_with(
            job_pb2.LayerGetFramesRequest(
                layer=layer.data,
                s=opencue.search.FrameSearch.criteriaFromOptions()),
            timeout=mock.ANY)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].data.layer_name, TEST_LAYER_NAME)

    def testGetOutputPaths(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetOutputPaths.return_value = job_pb2.LayerGetOutputPathsResponse(
            output_paths=[TEST_OUTPUT_PATH])
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        outputPaths = layer.getOutputPaths()

        stubMock.GetOutputPaths.assert_called_with(
            job_pb2.LayerGetOutputPathsRequest(layer=layer.data), timeout=mock.ANY)
        self.assertEqual(len(outputPaths), 1)
        self.assertEqual(outputPaths[0], TEST_OUTPUT_PATH)

    def testSetTags(self, getStubMock):
        tags = ['cloud', 'local']
        stubMock = mock.Mock()
        stubMock.SetTags.return_value = job_pb2.LayerSetTagsResponse()
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.setTags(tags)

        stubMock.SetTags.assert_called_with(
            job_pb2.LayerSetTagsRequest(layer=layer.data, tags=tags), timeout=mock.ANY)

    def testSetMaxCores(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetMaxCores.return_value = job_pb2.LayerSetMaxCoresResponse()
        getStubMock.return_value = stubMock

        testCores = 100
        testCoresActual = testCores/100.0
        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.setMaxCores(testCores)

        stubMock.SetMaxCores.assert_called_with(
            job_pb2.LayerSetMaxCoresRequest(layer=layer.data, cores=testCoresActual),
            timeout=mock.ANY)

    def testSetMinGpuMemory(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetMinGpuMemory.return_value = job_pb2.LayerSetMinGpuResponse()
        getStubMock.return_value = stubMock

        testCores = 100
        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.setMinGpuMemory(testCores)

        stubMock.SetMinGpuMemory.assert_called_with(
            job_pb2.LayerSetMinGpuMemoryRequest(layer=layer.data, gpu_memory=testCores),
            timeout=mock.ANY)

    def testSetMinMemory(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetMinMemory.return_value = job_pb2.LayerSetMinMemoryResponse()
        getStubMock.return_value = stubMock

        memory = 2048
        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.setMinMemory(memory)

        stubMock.SetMinMemory.assert_called_with(
            job_pb2.LayerSetMinMemoryRequest(layer=layer.data, memory=memory),
            timeout=mock.ANY)

    def testSetThreadable(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetThreadable.return_value = job_pb2.LayerSetThreadableResponse()
        getStubMock.return_value = stubMock

        value = True
        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.setThreadable(value)

        stubMock.SetThreadable.assert_called_with(
            job_pb2.LayerSetThreadableRequest(layer=layer.data, threadable=value),
            timeout=mock.ANY)

    def testGetWhatDependsOnThis(self, getStubMock):
        dependId = 'dddd-ddd-dddd'
        stubMock = mock.Mock()
        stubMock.GetWhatDependsOnThis.return_value = job_pb2.LayerGetWhatDependsOnThisResponse(
            depends=depend_pb2.DependSeq(depends=[depend_pb2.Depend(id=dependId)]))
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        depends = layer.getWhatDependsOnThis()

        stubMock.GetWhatDependsOnThis.assert_called_with(
            job_pb2.LayerGetWhatDependsOnThisRequest(layer=layer.data),
            timeout=mock.ANY)
        self.assertEqual(len(depends), 1)
        self.assertEqual(depends[0].id(), dependId)

    def testGetWhatThisDependsOn(self, getStubMock):
        dependId = 'dddd-ddd-dddd'
        stubMock = mock.Mock()
        stubMock.GetWhatThisDependsOn.return_value = job_pb2.LayerGetWhatThisDependsOnResponse(
            depends=depend_pb2.DependSeq(depends=[depend_pb2.Depend(id=dependId)]))
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        depends = layer.getWhatThisDependsOn()

        stubMock.GetWhatThisDependsOn.assert_called_with(
            job_pb2.LayerGetWhatThisDependsOnRequest(layer=layer.data),
            timeout=mock.ANY)
        self.assertEqual(len(depends), 1)
        self.assertEqual(depends[0].id(), dependId)

    def testCreateDependencyOnJob(self, getStubMock):
        dependId = 'dddd-ddd-dddd'
        jobId = 'jjjj-jjj-jjjj'
        stubMock = mock.Mock()
        stubMock.CreateDependencyOnJob.return_value = job_pb2.LayerCreateDependOnJobResponse(
            depend=depend_pb2.Depend(id=dependId))
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        job = opencue.wrappers.job.Job(
            job_pb2.Job(id=jobId))
        depend = layer.createDependencyOnJob(job)

        stubMock.CreateDependencyOnJob.assert_called_with(
            job_pb2.LayerCreateDependOnJobRequest(layer=layer.data, job=job.data),
            timeout=mock.ANY)
        self.assertEqual(depend.id(), dependId)

    def testCreateDependencyOnLayer(self, getStubMock):
        dependId = 'dddd-ddd-dddd'
        layerId = 'llll-lll-llll'
        stubMock = mock.Mock()
        stubMock.CreateDependencyOnLayer.return_value = job_pb2.LayerCreateDependOnLayerResponse(
            depend=depend_pb2.Depend(id=dependId))
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        dependLayer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(id=layerId))
        depend = layer.createDependencyOnLayer(dependLayer)

        stubMock.CreateDependencyOnLayer.assert_called_with(
            job_pb2.LayerCreateDependOnLayerRequest(layer=layer.data,
                                                    depend_on_layer=dependLayer.data),
            timeout=mock.ANY)
        self.assertEqual(depend.id(), dependId)

    def testCreateDependencyOnFrame(self, getStubMock):
        dependId = 'dddd-ddd-dddd'
        frameId = 'ffff-fff-ffff'
        stubMock = mock.Mock()
        stubMock.CreateDependencyOnFrame.return_value = job_pb2.LayerCreateDependOnFrameResponse(
            depend=depend_pb2.Depend(id=dependId))
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        frame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(id=frameId))
        depend = layer.createDependencyOnFrame(frame)

        stubMock.CreateDependencyOnFrame.assert_called_with(
            job_pb2.LayerCreateDependOnFrameRequest(layer=layer.data, frame=frame.data),
            timeout=mock.ANY)
        self.assertEqual(depend.id(), dependId)

    def testCreateFrameByFrameDependency(self, getStubMock):
        dependId = 'dddd-ddd-dddd'
        layerId = 'llll-lll-llll'
        stubMock = mock.Mock()
        stubMock.CreateFrameByFrameDependency.return_value = \
            job_pb2.LayerCreateFrameByFrameDependResponse(depend=depend_pb2.Depend(id=dependId))
        getStubMock.return_value = stubMock

        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        dependLayer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(id=layerId))
        depend = layer.createFrameByFrameDependency(dependLayer)

        stubMock.CreateFrameByFrameDependency.assert_called_with(
            job_pb2.LayerCreateFrameByFrameDependRequest(layer=layer.data,
                                                         depend_layer=dependLayer.data,
                                                         any_frame=False),
            timeout=mock.ANY)
        self.assertEqual(depend.id(), dependId)

    def testRegisterOutputPath(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.RegisterOutputPath.return_value = job_pb2.LayerRegisterOutputPathResponse()
        getStubMock.return_value = stubMock

        outputPath = '/test/output/path'
        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.registerOutputPath(outputPath)

        stubMock.RegisterOutputPath.assert_called_with(
            job_pb2.LayerRegisterOutputPathRequest(layer=layer.data, spec=outputPath),
            timeout=mock.ANY)

    def testReorderFrames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.ReorderFrames.return_value = job_pb2.LayerReorderFramesResponse()
        getStubMock.return_value = stubMock

        frameRange = '1-10'
        order = job_pb2.REVERSE
        layer = opencue.wrappers.layer.Layer(job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.reorderFrames(frameRange, order)

        stubMock.ReorderFrames.assert_called_with(
            job_pb2.LayerReorderFramesRequest(layer=layer.data, range=frameRange, order=order),
            timeout=mock.ANY)

    def testStaggerFrames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.StaggerFrames.return_value = job_pb2.LayerStaggerFramesResponse()
        getStubMock.return_value = stubMock

        frameRange = '1-10'
        stagger = 4
        layer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=TEST_LAYER_NAME))
        layer.staggerFrames(frameRange, stagger)

        stubMock.StaggerFrames.assert_called_with(
            job_pb2.LayerStaggerFramesRequest(layer=layer.data, range=frameRange, stagger=stagger),
            timeout=mock.ANY)


class LayerEnumTests(unittest.TestCase):

    def testLayerType(self):
        self.assertEqual(opencue.api.Layer.LayerType.PRE, job_pb2.PRE)
        self.assertEqual(opencue.api.Layer.LayerType.PRE, 0)

    def testOrder(self):
        self.assertEqual(opencue.api.Layer.Order.LAST, job_pb2.LAST)
        self.assertEqual(opencue.api.Layer.Order.LAST, 1)


if __name__ == '__main__':
    unittest.main()
