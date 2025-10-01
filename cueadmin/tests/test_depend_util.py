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

import opencue.api
from cueadmin.common import DependUtil


def _make_depend(name="dep", type_name="ANY", active=True):
    """Create a minimal mock depend with a data.type and a satisfy() method."""
    d = MagicMock(name=name)
    d.data.type = type_name
    d.data.active = active
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


class TestDependUtilParseDependType(unittest.TestCase):
    """Tests for parsing and validating dependency types."""

    def test_parseDependType_returns_correct_enum_for_valid_type(self):
        """Valid dependency type strings should return the correct enum value."""
        result = DependUtil.parseDependType("JOB_ON_JOB")
        self.assertEqual(result, opencue.api.depend_pb2.JOB_ON_JOB)

    def test_parseDependType_is_case_insensitive(self):
        """Dependency type parsing should be case-insensitive."""
        result_lower = DependUtil.parseDependType("job_on_layer")
        result_upper = DependUtil.parseDependType("JOB_ON_LAYER")
        result_mixed = DependUtil.parseDependType("Job_On_Layer")

        self.assertEqual(result_lower, opencue.api.depend_pb2.JOB_ON_LAYER)
        self.assertEqual(result_upper, opencue.api.depend_pb2.JOB_ON_LAYER)
        self.assertEqual(result_mixed, opencue.api.depend_pb2.JOB_ON_LAYER)

    def test_parseDependType_raises_error_for_invalid_type(self):
        """Invalid dependency type should raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            DependUtil.parseDependType("INVALID_TYPE")

        self.assertIn("Invalid dependency type", str(ctx.exception))

    def test_parseDependType_supports_all_dependency_types(self):
        """All standard dependency types should be parseable."""
        types_to_test = [
            'JOB_ON_JOB', 'JOB_ON_LAYER', 'JOB_ON_FRAME',
            'LAYER_ON_JOB', 'LAYER_ON_LAYER', 'LAYER_ON_FRAME',
            'FRAME_ON_JOB', 'FRAME_ON_LAYER', 'FRAME_ON_FRAME',
            'FRAME_BY_FRAME', 'LAYER_ON_SIM_FRAME'
        ]

        for depend_type in types_to_test:
            result = DependUtil.parseDependType(depend_type)
            self.assertIsNotNone(result)


class TestDependUtilCreateJobOnJobDepend(unittest.TestCase):
    """Tests for creating job-on-job dependencies."""

    @patch('cueadmin.common.opencue.api.findJob')
    def test_createJobOnJobDepend_creates_dependency(self, mock_find_job):
        """createJobOnJobDepend should find both jobs and create dependency."""
        job = MagicMock(name='job')
        depend_on_job = MagicMock(name='depend_on_job')
        mock_depend = MagicMock(name='created_depend')

        job.createDependencyOnJob.return_value = mock_depend
        mock_find_job.side_effect = [job, depend_on_job]

        result = DependUtil.createJobOnJobDepend("jobA", "jobB")

        self.assertEqual(mock_find_job.call_count, 2)
        mock_find_job.assert_any_call("jobA")
        mock_find_job.assert_any_call("jobB")
        job.createDependencyOnJob.assert_called_once_with(depend_on_job)
        self.assertEqual(result, mock_depend)

    @patch('cueadmin.common.opencue.api.findJob')
    def test_createJobOnJobDepend_propagates_exceptions(self, mock_find_job):
        """Exceptions from findJob should propagate."""
        mock_find_job.side_effect = Exception("Job not found")

        with self.assertRaises(Exception) as ctx:
            DependUtil.createJobOnJobDepend("jobA", "jobB")

        self.assertIn("Job not found", str(ctx.exception))


class TestDependUtilCreateLayerOnLayerDepend(unittest.TestCase):
    """Tests for creating layer-on-layer dependencies."""

    @patch('cueadmin.common.opencue.api.findLayer')
    def test_createLayerOnLayerDepend_creates_dependency(self, mock_find_layer):
        """createLayerOnLayerDepend should find both layers and create dependency."""
        layer = MagicMock(name='layer')
        depend_on_layer = MagicMock(name='depend_on_layer')
        mock_depend = MagicMock(name='created_depend')

        layer.createDependencyOnLayer.return_value = mock_depend
        mock_find_layer.side_effect = [layer, depend_on_layer]

        result = DependUtil.createLayerOnLayerDepend("jobA", "layerX", "jobB", "layerY")

        self.assertEqual(mock_find_layer.call_count, 2)
        mock_find_layer.assert_any_call("jobA", "layerX")
        mock_find_layer.assert_any_call("jobB", "layerY")
        layer.createDependencyOnLayer.assert_called_once_with(depend_on_layer)
        self.assertEqual(result, mock_depend)

    @patch('cueadmin.common.opencue.api.findLayer')
    def test_createLayerOnLayerDepend_propagates_exceptions(self, mock_find_layer):
        """Exceptions from findLayer should propagate."""
        mock_find_layer.side_effect = Exception("Layer not found")

        with self.assertRaises(Exception) as ctx:
            DependUtil.createLayerOnLayerDepend("jobA", "layerX", "jobB", "layerY")

        self.assertIn("Layer not found", str(ctx.exception))


class TestDependUtilCreateFrameByFrameDepend(unittest.TestCase):
    """Tests for creating frame-by-frame dependencies."""

    @patch('cueadmin.common.opencue.api.findLayer')
    def test_createFrameByFrameDepend_creates_dependency(self, mock_find_layer):
        """createFrameByFrameDepend should find both layers and create frame-by-frame dependency."""
        layer = MagicMock(name='layer')
        depend_on_layer = MagicMock(name='depend_on_layer')
        mock_depend = MagicMock(name='created_depend')

        layer.createFrameByFrameDependency.return_value = mock_depend
        mock_find_layer.side_effect = [layer, depend_on_layer]

        result = DependUtil.createFrameByFrameDepend("jobA", "layerX", "jobB", "layerY")

        self.assertEqual(mock_find_layer.call_count, 2)
        mock_find_layer.assert_any_call("jobA", "layerX")
        mock_find_layer.assert_any_call("jobB", "layerY")
        layer.createFrameByFrameDependency.assert_called_once_with(depend_on_layer)
        self.assertEqual(result, mock_depend)

    @patch('cueadmin.common.opencue.api.findLayer')
    def test_createFrameByFrameDepend_propagates_exceptions(self, mock_find_layer):
        """Exceptions from findLayer should propagate."""
        mock_find_layer.side_effect = Exception("Layer not found")

        with self.assertRaises(Exception) as ctx:
            DependUtil.createFrameByFrameDepend("jobA", "layerX", "jobB", "layerY")

        self.assertIn("Layer not found", str(ctx.exception))


class TestDependUtilCheckDependSatisfaction(unittest.TestCase):
    """Tests for checking if dependencies are satisfied."""

    @patch('cueadmin.common.opencue.api.findJob')
    def test_checkDependSatisfaction_returns_true_when_all_satisfied(self, mock_find_job):
        """When all dependencies are inactive (satisfied), should return True."""
        job_obj = MagicMock(name='job')
        # All dependencies are inactive (satisfied)
        job_obj.getWhatThisDependsOn.return_value = [
            _make_depend("d1", "JOB_ON_JOB", active=False),
            _make_depend("d2", "JOB_ON_LAYER", active=False)
        ]
        mock_find_job.return_value = job_obj

        result = DependUtil.checkDependSatisfaction("jobA")

        self.assertTrue(result)
        mock_find_job.assert_called_once_with("jobA")

    @patch('cueadmin.common.opencue.api.findJob')
    def test_checkDependSatisfaction_returns_false_when_dependencies_active(self, mock_find_job):
        """When there are active dependencies, should return False."""
        job_obj = MagicMock(name='job')
        job_obj.getWhatThisDependsOn.return_value = [
            _make_depend("d1", "JOB_ON_JOB", active=True),
            _make_depend("d2", "JOB_ON_LAYER", active=False)
        ]
        mock_find_job.return_value = job_obj

        result = DependUtil.checkDependSatisfaction("jobA")

        self.assertFalse(result)

    @patch('cueadmin.common.opencue.api.findJob')
    def test_checkDependSatisfaction_returns_true_when_no_dependencies(self, mock_find_job):
        """When there are no dependencies, should return True."""
        job_obj = MagicMock(name='job')
        job_obj.getWhatThisDependsOn.return_value = []
        mock_find_job.return_value = job_obj

        result = DependUtil.checkDependSatisfaction("jobA")

        self.assertTrue(result)

    @patch('cueadmin.common.opencue.api.findLayer')
    def test_checkDependSatisfaction_works_for_layer(self, mock_find_layer):
        """checkDependSatisfaction should work for layers."""
        layer_obj = MagicMock(name='layer')
        layer_obj.getWhatThisDependsOn.return_value = [
            _make_depend("d1", "LAYER_ON_LAYER", active=False)
        ]
        mock_find_layer.return_value = layer_obj

        result = DependUtil.checkDependSatisfaction("jobA", layer_name="layerX")

        self.assertTrue(result)
        mock_find_layer.assert_called_once_with("jobA", "layerX")

    @patch('cueadmin.common.opencue.api.findFrame')
    def test_checkDependSatisfaction_works_for_frame(self, mock_find_frame):
        """checkDependSatisfaction should work for frames."""
        frame_obj = MagicMock(name='frame')
        frame_obj.getWhatThisDependsOn.return_value = []
        mock_find_frame.return_value = frame_obj

        result = DependUtil.checkDependSatisfaction("jobA", layer_name="layerX", frame_num=10)

        self.assertTrue(result)
        mock_find_frame.assert_called_once_with("jobA", "layerX", 10)


class TestDependUtilDetectCircularDepend(unittest.TestCase):
    """Tests for detecting circular dependencies."""

    def test_detectCircularDepend_detects_self_dependency(self):
        """Detecting circular dependency when job depends on itself."""
        result = DependUtil.detectCircularDepend("jobA", "jobA")
        self.assertTrue(result)

    @patch('cueadmin.common.opencue.api.findJob')
    def test_detectCircularDepend_returns_false_for_valid_dependency(self, mock_find_job):
        """No circular dependency when jobs are different and no reverse dependency exists."""
        job_a = MagicMock(name='jobA')
        job_b = MagicMock(name='jobB')
        job_a.data.id = "id_a"
        job_b.data.id = "id_b"

        # jobB has no dependencies
        job_b.getWhatThisDependsOn.return_value = []
        mock_find_job.side_effect = [job_a, job_b]

        result = DependUtil.detectCircularDepend("jobA", "jobB")

        self.assertFalse(result)

    @patch('cueadmin.common.opencue.api.findJob')
    def test_detectCircularDepend_detects_direct_circular(self, mock_find_job):
        """Detects circular dependency when jobB already depends on jobA."""
        job_a = MagicMock(name='jobA')
        job_b = MagicMock(name='jobB')
        job_a.data.id = "id_a"
        job_b.data.id = "id_b"

        # jobB already depends on jobA
        depend = MagicMock()
        depend.data.depend_on_job = "id_a"
        job_b.getWhatThisDependsOn.return_value = [depend]
        mock_find_job.side_effect = [job_a, job_b]

        result = DependUtil.detectCircularDepend("jobA", "jobB")

        self.assertTrue(result)

    @patch('cueadmin.common.opencue.api.findJob')
    def test_detectCircularDepend_handles_exception_gracefully(self, mock_find_job):
        """When findJob fails, detectCircularDepend should return False."""
        mock_find_job.side_effect = Exception("Job not found")

        result = DependUtil.detectCircularDepend("jobA", "jobB")

        self.assertFalse(result)


class TestDependUtilFormatDependStatus(unittest.TestCase):
    """Tests for formatting dependency status."""

    def test_formatDependStatus_formats_active_dependency(self):
        """Active dependency should be formatted with ACTIVE status."""
        depend = _make_depend("d1", "JOB_ON_JOB", active=True)

        result = DependUtil.formatDependStatus(depend)

        self.assertIn("JOB_ON_JOB", result)
        self.assertIn("ACTIVE", result)

    def test_formatDependStatus_formats_satisfied_dependency(self):
        """Satisfied (inactive) dependency should be formatted with SATISFIED status."""
        depend = _make_depend("d1", "LAYER_ON_LAYER", active=False)

        result = DependUtil.formatDependStatus(depend)

        self.assertIn("LAYER_ON_LAYER", result)
        self.assertIn("SATISFIED", result)

    def test_formatDependStatus_handles_different_dependency_types(self):
        """formatDependStatus should work with all dependency types."""
        types_to_test = ["JOB_ON_JOB", "LAYER_ON_LAYER", "FRAME_ON_FRAME", "FRAME_BY_FRAME"]

        for depend_type in types_to_test:
            depend = _make_depend("d", depend_type, active=True)
            result = DependUtil.formatDependStatus(depend)

            self.assertIn(depend_type, result)
            self.assertIn("ACTIVE", result)


if __name__ == '__main__':
    unittest.main()
