# Copyright Contributors to the OpenCue Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
Unit tests for DependUtil in cueadmin.common.
"""

import unittest
from unittest.mock import MagicMock, patch

from cueadmin.common import DependUtil


def _make_depend(name="dep", type_name="ANY"):
    """Create a minimal mock depend with a data.type and a satisfy() method."""
    d = MagicMock(name=name)
    d.data.type = type_name
    d.satisfy = MagicMock(name=f"{name}.satisfy")
    return d


class TestDependUtilDropAllDepends(unittest.TestCase):
    """Tests for dropping all dependencies at frame, layer, and job levels."""

    @patch('cueadmin.common.opencue.api.findFrame')
    def test_dropAllDepends_on_frame_calls_satisfy_for_each_depend(self, mock_find_frame):
        """Given job/layer/frame, use findFrame and satisfy all dependencies."""
        depends = [_make_depend("d1", "FrameOnSomething"), _make_depend("d2", "FrameOnOther")]
        frame_obj = MagicMock(name='frame_obj')
        frame_obj.getWhatThisDependsOn.return_value = depends
        mock_find_frame.return_value = frame_obj

        DependUtil.dropAllDepends(job="jobA", layer="layerX", frame=10)

        mock_find_frame.assert_called_once_with("jobA", "layerX", 10)
        frame_obj.getWhatThisDependsOn.assert_called_once()
        for dep in depends:
            dep.satisfy.assert_called_once()

    @patch('cueadmin.common.opencue.api.findLayer')
    def test_dropAllDepends_on_layer_calls_satisfy_for_each_depend(self, mock_find_layer):
        """Given job/layer, use findLayer and satisfy all dependencies."""
        depends = [_make_depend("d1", "LayerOnSomething")]
        layer_obj = MagicMock(name='layer_obj')
        layer_obj.getWhatThisDependsOn.return_value = depends
        mock_find_layer.return_value = layer_obj

        DependUtil.dropAllDepends(job="jobA", layer="layerY")

        mock_find_layer.assert_called_once_with("jobA", "layerY")
        layer_obj.getWhatThisDependsOn.assert_called_once()
        depends[0].satisfy.assert_called_once()

    @patch('cueadmin.common.opencue.id', return_value='id-abc')
    @patch('cueadmin.common.opencue.api.findJob')
    def test_dropAllDepends_on_job_calls_satisfy_for_each_depend(self, mock_find_job, _mock_id):
        """Given just job, use findJob and satisfy all dependencies."""
        depends = [_make_depend("d1", "JobOnJob"), _make_depend("d2", "JobOnLayer")]
        job_obj = MagicMock(name='job_obj')
        job_obj.getWhatThisDependsOn.return_value = depends
        mock_find_job.return_value = job_obj

        DependUtil.dropAllDepends(job="jobB")

        mock_find_job.assert_called_once_with("jobB")
        job_obj.getWhatThisDependsOn.assert_called_once()
        for dep in depends:
            dep.satisfy.assert_called_once()

    @patch('cueadmin.common.opencue.api.findJob')
    def test_dropAllDepends_handles_no_dependencies_gracefully(self, mock_find_job):
        """If there are zero dependencies, no errors should occur and nothing is satisfied."""
        job_obj = MagicMock(name='job_obj')
        job_obj.getWhatThisDependsOn.return_value = []
        mock_find_job.return_value = job_obj

        DependUtil.dropAllDepends(job="emptyJob")

        mock_find_job.assert_called_once_with("emptyJob")
        job_obj.getWhatThisDependsOn.assert_called_once()

    @patch('cueadmin.common.opencue.api.findJob')
    def test_dropAllDepends_propagates_api_exception(self, mock_find_job):
        """If opencue API raises, DependUtil should propagate the exception."""
        mock_find_job.side_effect = Exception("API failure")

        with self.assertRaises(Exception) as ctx:
            DependUtil.dropAllDepends(job="badJob")

        self.assertIn("API failure", str(ctx.exception))

    @patch('cueadmin.common.opencue.api.findJob')
    def test_dropAllDepends_propagates_satisfy_exception(self, mock_find_job):
        """If a dependency satisfy() raises, the exception should propagate."""
        dep = _make_depend("d1", "JobOnJob")
        dep.satisfy.side_effect = RuntimeError("satisfy failed")
        job_obj = MagicMock(name='job_obj')
        job_obj.getWhatThisDependsOn.return_value = [dep]
        mock_find_job.return_value = job_obj

        with self.assertRaises(RuntimeError) as ctx:
            DependUtil.dropAllDepends(job="jobWithBadDepend")

        self.assertIn("satisfy failed", str(ctx.exception))

    @patch('cueadmin.common.logger')
    @patch('cueadmin.common.opencue.id', return_value='id-log')
    @patch('cueadmin.common.opencue.api.findJob')
    def test_dropAllDepends_logs_dependency_type_and_id(self, mock_find_job, _mock_id, mock_logger):
        """Verify logger.debug logs dependency type and id for job case."""
        dep = _make_depend("d1", "JobOnLayer")
        job_obj = MagicMock(name='job_obj')
        job_obj.getWhatThisDependsOn.return_value = [dep]
        mock_find_job.return_value = job_obj

        DependUtil.dropAllDepends(job="jobC")

        mock_find_job.assert_called_once_with("jobC")
        # logger.debug("dropping depend %s %s", depend.data.type, opencue.id(depend))
        mock_logger.debug.assert_any_call("dropping depend %s %s", dep.data.type, 'id-log')

if __name__ == '__main__':
    unittest.main()
