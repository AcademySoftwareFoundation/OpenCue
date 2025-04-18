#  Copyright (c) OpenCue Project Authors
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


"""Tests for cuegui.Utils."""


import unittest

import mock

import opencue_proto.job_pb2
import opencue.wrappers.job
import cuegui.Utils
import cuegui.Constants


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class UtilsTests(unittest.TestCase):
    def test_shouldReturnJobAsIs(self):
        originalJob = opencue.wrappers.job.Job()

        returnedJob = cuegui.Utils.findJob(originalJob)

        self.assertEqual(originalJob, returnedJob)

    def test_shouldReturnNoneForString(self):
        self.assertIsNone(cuegui.Utils.findJob('arbitrary-string'))

    @mock.patch('opencue.api.getJob')
    def test_shouldSearchForJobById(self, getJobMock):
        jobId = '666f6f20-6261-7220-6261-740a616e6420'

        cuegui.Utils.findJob(jobId)

        getJobMock.assert_called_with(jobId)

    def test_shouldReturnNoneForInvalidJobName(self):
        invalidJobId = 'arbitrary$String##With*Disallowed@Characters'

        self.assertIsNone(cuegui.Utils.findJob(invalidJobId))

    @mock.patch('opencue.api.findJob')
    def test_shouldSearchForJobByName(self, findJobMock):
        jobId = 'arbitrary-job-id'
        jobName = 'show_name-and_shot.name-some$other#stuff'
        expectedJob = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(id=jobId, name=jobName))
        findJobMock.return_value = expectedJob

        returnedJob = cuegui.Utils.findJob(jobName)

        findJobMock.assert_called_with(jobName)
        self.assertEqual(jobId, returnedJob.id())

    @mock.patch('opencue.api.findJob', new=mock.Mock(side_effect=Exception()))
    def test_shouldSwallowExceptionAndReturnNone(self):
        jobName = 'show_name-and_shot.name-some$other#stuff'

        self.assertIsNone(cuegui.Utils.findJob(jobName))

    def test_shouldReturnResourceLimitsFromYaml(self):
        result = cuegui.Utils.getResourceConfig()

        self.assertEqual({
            'max_cores': 256,
            'max_gpu_memory': 128,
            'max_gpus': 8,
            'max_memory': 512,
            'max_proc_hour_cutoff': 30,
            'redirect_wasted_cores_threshold': 100,
        }, result)

class UtilsViewerTests(unittest.TestCase):
    def test_shouldLaunchViewerUsingEmptyPaths(self):
        # Test launching without empty paths
        self.assertIsNone(cuegui.Utils.launchViewerUsingPaths([], "test", test_mode=True))

    def test_shouldLaunchViewerUsingSimplePath(self):
        # Test launching without regexp
        cuegui.Constants.OUTPUT_VIEWERS = [{"action_text": "test",
                                            "extract_args_regex": None,
                                            "cmd_pattern": 'echo'}]
        out = cuegui.Utils.launchViewerUsingPaths(["/shots/test_show/test_shot/something/else"],
                                                  "test",
                                                  test_mode=True)
        self.assertEqual('echo /shots/test_show/test_shot/something/else', out)

    def test_shouldNotLaunchViewerUsingInvalidCombination(self):
        # Test launching with invalig regex and pattern combination
        cuegui.Constants.OUTPUT_VIEWERS = [
            {"action_text": "test",
             "extract_args_regex": r'/shots/(?P<show>\w+)/(?P<name>shot\w+)/.*',
             "cmd_pattern": 'echo show={not_a_show}, shot={shot}'}]

        out = cuegui.Utils.launchViewerUsingPaths(["/shots/test_show/test_shot/something/else"],
                                                  "test",
                                                  test_mode=True)
        self.assertIsNone(out)

    def test_shouldLaunchViewerUsingRegextAndPattern(self):
        # Test launching with valid regex and pattern
        cuegui.Constants.OUTPUT_VIEWERS = [
            {"action_text": "test",
             "extract_args_regex": r'/shots/(?P<show>\w+)/(?P<shot>\w+)/.*',
             "cmd_pattern": 'echo show={show}, shot={shot}'}]

        out = cuegui.Utils.launchViewerUsingPaths(["/shots/test_show/test_shot/something/else"],
                                                  "test",
                                                  test_mode=True)
        self.assertEqual('echo show=test_show, shot=test_shot', out)

    def test_shouldLaunchViewerUsingStereoPaths(self):
        # Test launching with stereo output
        cuegui.Constants.OUTPUT_VIEWERS = [{"action_text": "test",
                                            "extract_args_regex": None,
                                            "cmd_pattern": 'echo',
                                            "stereo_modifiers": '_lf_,_rt_'}]

        out = cuegui.Utils.launchViewerUsingPaths(["/test/something_lf_something",
                                                   "/test/something_rt_something"],
                                                  "test",
                                                   test_mode=True)
        self.assertEqual('echo /test/something_lf_something', out)

    def test_shouldLaunchViewerUsingMultiplePaths(self):
        # Test launching multiple outputs
        cuegui.Constants.OUTPUT_VIEWERS = [{"action_text": "test",
                                            "extract_args_regex": None,
                                            "cmd_pattern": 'echo'}]

        out = cuegui.Utils.launchViewerUsingPaths(["/test/something_1", "/test/something_2"],
                                                  "test",
                                                  test_mode=True)
        self.assertEqual('echo /test/something_1 /test/something_2', out)


if __name__ == '__main__':
    unittest.main()
