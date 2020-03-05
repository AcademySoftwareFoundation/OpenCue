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


import mock
import unittest

import opencue.compiled_proto.job_pb2
import opencue.wrappers.job
import cuegui.Utils


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
            opencue.compiled_proto.job_pb2.Job(id=jobId, name=jobName))
        findJobMock.return_value = expectedJob

        returnedJob = cuegui.Utils.findJob(jobName)

        findJobMock.assert_called_with(jobName)
        self.assertEqual(jobId, returnedJob.id())

    @mock.patch('opencue.api.findJob', new=mock.Mock(side_effect=Exception()))
    def test_shouldSwallowExceptionAndReturnNone(self):
        jobName = 'show_name-and_shot.name-some$other#stuff'

        self.assertIsNone(cuegui.Utils.findJob(jobName))


if __name__ == '__main__':
    unittest.main()
