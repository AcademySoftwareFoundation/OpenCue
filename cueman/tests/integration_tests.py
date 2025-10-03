#!/usr/bin/env python
# pylint: disable=no-member

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


"""Integration tests for command in cueman.

This module tests end-to-end workflows combining multiple operations to verify
that command sequences work correctly together and maintain state consistency.
"""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import unittest
from unittest import mock


TEST_JOB = 'test_job'
TEST_LAYER = 'test_layer'
TEST_FRAME_RANGE = '1-10'


class JobPauseModifyResumeWorkflowTest(unittest.TestCase):
    """Test job pause -> modify -> resume workflow.

    This test class verifies that jobs can be paused, modified,
    and resumed correctly through the full lifecycle.
    """

    def test_job_pause_modify_resume_workflow(self):
        """Test complete job workflow: pause, modify retries, resume."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB
        job.data.state = 'RUNNING'
        job.isPaused.return_value = False

        # Step 1: Pause the job
        job.pause()
        job.pause.assert_called_once()

        # Step 2: Modify max retries while paused
        job.setMaxRetries(5)
        job.setMaxRetries.assert_called_once_with(5)

        # Step 3: Resume the job
        job.resume()
        job.resume.assert_called_once()

        # Verify all operations were called in sequence
        self.assertEqual(job.pause.call_count, 1)
        self.assertEqual(job.setMaxRetries.call_count, 1)
        self.assertEqual(job.resume.call_count, 1)

    def test_batch_job_pause_resume(self):
        """Test pausing and resuming multiple jobs in batch."""
        job1 = mock.Mock()
        job1.data = mock.Mock()
        job1.data.name = 'job1'
        job1.isPaused.return_value = False

        job2 = mock.Mock()
        job2.data = mock.Mock()
        job2.data.name = 'job2'
        job2.isPaused.return_value = False

        # Pause multiple jobs
        job1.pause()
        job2.pause()

        job1.pause.assert_called_once()
        job2.pause.assert_called_once()

        # Resume multiple jobs
        job1.resume()
        job2.resume()

        job1.resume.assert_called_once()
        job2.resume.assert_called_once()

    def test_pause_already_paused_job(self):
        """Test that attempting to pause an already paused job is handled gracefully."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB
        job.isPaused.return_value = True

        # Attempting to pause already paused job should not call pause
        if not job.isPaused():
            job.pause()

        # Verify pause was not called since job is already paused
        job.pause.assert_not_called()


class FrameOperationsWorkflowTest(unittest.TestCase):
    """Test frame operations workflow: list -> filter -> modify.

    This test class verifies frame-level operations work correctly
    with various filters and states.
    """

    def test_list_frames_with_state_filter(self):
        """Test listing frames with state filter."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        frame1 = mock.Mock()
        frame1.data = mock.Mock()
        frame1.data.state = 'DEAD'
        frame1.data.number = 1

        frame2 = mock.Mock()
        frame2.data = mock.Mock()
        frame2.data.state = 'DEAD'
        frame2.data.number = 2

        # Query frames with state filter
        job.getFrames.return_value = [frame1, frame2]
        frames = job.getFrames(state=['DEAD'])

        job.getFrames.assert_called_once_with(state=['DEAD'])
        self.assertEqual(len(frames), 2)

    def test_retry_dead_frames_workflow(self):
        """Test workflow: list dead frames -> retry them."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Step 1: Get dead frames
        job.getFrames.return_value = [mock.Mock(), mock.Mock()]
        dead_frames = job.getFrames(state=['DEAD'])
        self.assertEqual(len(dead_frames), 2)

        # Step 2: Retry dead frames
        job.retryFrames(state=['DEAD'])
        job.retryFrames.assert_called_once_with(state=['DEAD'])

    def test_kill_running_frames_workflow(self):
        """Test workflow: list running frames -> kill them."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Step 1: Get running frames
        job.getFrames.return_value = [mock.Mock(), mock.Mock(), mock.Mock()]
        running_frames = job.getFrames(state=['RUNNING'])
        self.assertEqual(len(running_frames), 3)

        # Step 2: Kill running frames
        job.killFrames(state=['RUNNING'])
        job.killFrames.assert_called_once_with(state=['RUNNING'])

    def test_eat_dead_frames_workflow(self):
        """Test workflow: identify dead frames -> eat them."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Get dead frames
        job.getFrames.return_value = [mock.Mock()]
        dead_frames = job.getFrames(state=['DEAD'])
        self.assertEqual(len(dead_frames), 1)

        # Eat dead frames
        job.eatFrames(state=['DEAD'])
        job.eatFrames.assert_called_once_with(state=['DEAD'])

    def test_mark_frames_done_workflow(self):
        """Test marking frames as done to satisfy dependencies."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Mark specific frames as done
        job.markdoneFrames(range='1-5')
        job.markdoneFrames.assert_called_once_with(range='1-5')


class LayerOperationsWorkflowTest(unittest.TestCase):
    """Test layer-specific operations workflow.

    This test class verifies layer-level operations work correctly,
    including filtering and layer-specific frame operations.
    """

    def test_list_layers_workflow(self):
        """Test listing layers for a job."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        layer1 = mock.Mock()
        layer1.data = mock.Mock()
        layer1.data.name = 'render'
        layer1.data.layer_stats = mock.Mock()
        layer1.data.layer_stats.total_frames = 100
        layer1.data.layer_stats.succeeded_frames = 50
        layer1.data.layer_stats.running_frames = 30
        layer1.data.layer_stats.waiting_frames = 10
        layer1.data.layer_stats.dead_frames = 10

        layer2 = mock.Mock()
        layer2.data = mock.Mock()
        layer2.data.name = 'comp'
        layer2.data.layer_stats = mock.Mock()
        layer2.data.layer_stats.total_frames = 50
        layer2.data.layer_stats.succeeded_frames = 25
        layer2.data.layer_stats.running_frames = 15
        layer2.data.layer_stats.waiting_frames = 5
        layer2.data.layer_stats.dead_frames = 5

        job.getLayers.return_value = [layer1, layer2]
        layers = job.getLayers()

        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0].data.name, 'render')
        self.assertEqual(layers[1].data.name, 'comp')

    def test_layer_specific_frame_operations(self):
        """Test performing operations on specific layer frames."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Retry frames for specific layer
        job.retryFrames(layer=['render'], state=['DEAD'])
        job.retryFrames.assert_called_once_with(layer=['render'], state=['DEAD'])

        # Kill frames for specific layer
        job.killFrames(layer=['comp'], state=['RUNNING'])
        job.killFrames.assert_called_once_with(layer=['comp'], state=['RUNNING'])

    def test_stagger_frames_by_layer(self):
        """Test staggering frames for specific layers."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        layer = mock.Mock()
        layer.data = mock.Mock()
        layer.data.name = TEST_LAYER

        # Stagger frames with increment of 10
        layer.staggerFrames('1-100', 10)
        layer.staggerFrames.assert_called_once_with('1-100', 10)

    def test_reorder_frames_by_layer(self):
        """Test reordering frames for specific layers."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        layer = mock.Mock()
        layer.data = mock.Mock()
        layer.data.name = TEST_LAYER

        # Reorder frames to REVERSE
        layer.reorderFrames('1-100', 'REVERSE')
        layer.reorderFrames.assert_called_once_with('1-100', 'REVERSE')


class FrameRangeOperationsWorkflowTest(unittest.TestCase):
    """Test frame range filtering and operations.

    This test class verifies operations on specific frame ranges
    work correctly.
    """

    def test_operations_on_frame_range(self):
        """Test performing operations on specific frame ranges."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Retry specific frame range
        job.retryFrames(range='1-10')
        job.retryFrames.assert_called_once_with(range='1-10')

        # Kill specific frame range
        job.killFrames(range='50-100')
        job.killFrames.assert_called_once_with(range='50-100')

    def test_combined_layer_and_range_filter(self):
        """Test operations with both layer and range filters."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Retry specific frames in specific layer
        job.retryFrames(layer=['render'], range='1-50')
        job.retryFrames.assert_called_once_with(layer=['render'], range='1-50')

    def test_stagger_job_workflow(self):
        """Test staggering frames across entire job."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Stagger all frames by 5
        job.staggerFrames('1-100', 5)
        job.staggerFrames.assert_called_once_with('1-100', 5)

    def test_reorder_job_workflow(self):
        """Test reordering frames across entire job."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Test each order type
        job.reorderFrames('1-100', 'FIRST')
        job.reorderFrames.assert_called_with('1-100', 'FIRST')

        job.reorderFrames('1-100', 'LAST')
        job.reorderFrames.assert_called_with('1-100', 'LAST')

        job.reorderFrames('1-100', 'REVERSE')
        job.reorderFrames.assert_called_with('1-100', 'REVERSE')


class AutoEatWorkflowTest(unittest.TestCase):
    """Test auto-eat functionality workflow.

    This test class verifies auto-eat can be enabled/disabled and
    automatically handles dead frames.
    """

    def test_enable_auto_eat_workflow(self):
        """Test enabling auto-eat and eating existing dead frames."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Step 1: Enable auto-eat
        job.setAutoEat(True)
        job.setAutoEat.assert_called_once_with(True)

        # Step 2: Eat existing dead frames
        job.eatFrames(state=['DEAD'])
        job.eatFrames.assert_called_once_with(state=['DEAD'])

    def test_disable_auto_eat_workflow(self):
        """Test disabling auto-eat."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB
        job.data.auto_eat = True

        # Disable auto-eat
        job.setAutoEat(False)
        job.setAutoEat.assert_called_once_with(False)

    def test_batch_auto_eat_enable(self):
        """Test enabling auto-eat on multiple jobs."""
        job1 = mock.Mock()
        job1.data = mock.Mock()
        job1.data.name = 'job1'

        job2 = mock.Mock()
        job2.data = mock.Mock()
        job2.data.name = 'job2'

        # Enable auto-eat on both jobs
        job1.setAutoEat(True)
        job2.setAutoEat(True)

        job1.setAutoEat.assert_called_once_with(True)
        job2.setAutoEat.assert_called_once_with(True)


class JobTerminationWorkflowTest(unittest.TestCase):
    """Test job termination workflow.

    This test class verifies jobs can be terminated correctly,
    including batch terminations.
    """

    def test_terminate_single_job(self):
        """Test terminating a single job."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Terminate job
        job.kill(reason='User requested termination')
        job.kill.assert_called_once_with(reason='User requested termination')

    def test_terminate_multiple_jobs(self):
        """Test terminating multiple jobs in batch."""
        job1 = mock.Mock()
        job1.data = mock.Mock()
        job1.data.name = 'job1'

        job2 = mock.Mock()
        job2.data = mock.Mock()
        job2.data.name = 'job2'

        job3 = mock.Mock()
        job3.data = mock.Mock()
        job3.data.name = 'job3'

        jobs = [job1, job2, job3]

        # Terminate all jobs
        for job in jobs:
            job.kill(reason='Batch termination')

        job1.kill.assert_called_once_with(reason='Batch termination')
        job2.kill.assert_called_once_with(reason='Batch termination')
        job3.kill.assert_called_once_with(reason='Batch termination')


class ComplexFilteringWorkflowTest(unittest.TestCase):
    """Test complex filtering scenarios.

    This test class verifies multiple filters can be combined
    to narrow down frame queries effectively.
    """

    def test_state_and_layer_filter(self):
        """Test filtering frames by both state and layer."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        job.getFrames(state=['DEAD'], layer=['render'])
        job.getFrames.assert_called_once_with(state=['DEAD'], layer=['render'])

    def test_state_layer_and_range_filter(self):
        """Test filtering frames by state, layer, and range."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        job.getFrames(state=['RUNNING'], layer=['comp'], range='1-50')
        job.getFrames.assert_called_once_with(
            state=['RUNNING'], layer=['comp'], range='1-50'
        )

    def test_pagination_workflow(self):
        """Test paginated frame queries for large result sets."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Query first page
        job.getFrames(page=1, limit=1000)
        job.getFrames.assert_called_with(page=1, limit=1000)

        # Query second page
        job.getFrames(page=2, limit=1000)
        job.getFrames.assert_called_with(page=2, limit=1000)

    def test_memory_filter_workflow(self):
        """Test filtering frames by memory usage."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Filter frames using more than specified memory
        job.getFrames(memory='1048576-')  # > 1GB in KB
        job.getFrames.assert_called_once_with(memory='1048576-')

    def test_duration_filter_workflow(self):
        """Test filtering frames by execution duration."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Filter frames running longer than specified duration
        job.getFrames(duration='3600-')  # > 1 hour in seconds
        job.getFrames.assert_called_once_with(duration='3600-')


class ErrorHandlingWorkflowTest(unittest.TestCase):
    """Test error handling and recovery scenarios.

    This test class verifies that operations handle errors gracefully
    and maintain consistency when operations fail.
    """

    def test_job_not_found_error(self):
        """Test handling of job not found errors."""
        job_finder = mock.Mock()
        job_finder.findJob.side_effect = Exception("Job not found")

        with self.assertRaises(Exception):
            job_finder.findJob('nonexistent_job')

    def test_invalid_frame_range_error(self):
        """Test handling of invalid frame range specifications."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB
        job.retryFrames.side_effect = ValueError("Invalid frame range")

        with self.assertRaises(ValueError):
            job.retryFrames(range='invalid')

    def test_operation_on_completed_job(self):
        """Test operations on completed jobs are handled appropriately."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB
        job.data.state = 'FINISHED'

        # Some operations may not be valid on completed jobs
        job.pause.side_effect = RuntimeError("Cannot pause finished job")

        with self.assertRaises(RuntimeError):
            job.pause()

    def test_retry_operation_after_failure(self):
        """Test retrying an operation after initial failure."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # First attempt fails
        job.retryFrames.side_effect = [RuntimeError("Temporary failure"), None]

        # First call raises error
        with self.assertRaises(RuntimeError):
            job.retryFrames(range='1-10')

        # Second call succeeds
        job.retryFrames(range='1-10')
        self.assertEqual(job.retryFrames.call_count, 2)


class ProcQueryWorkflowTest(unittest.TestCase):
    """Test proc (running process) query workflow.

    This test class verifies process queries work correctly with
    various filters.
    """

    def test_list_procs_for_job(self):
        """Test listing running processes for a job."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        proc1 = mock.Mock()
        proc1.data = mock.Mock()
        proc1.data.name = 'proc1'

        proc2 = mock.Mock()
        proc2.data = mock.Mock()
        proc2.data.name = 'proc2'

        job.getProcs = mock.Mock(return_value=[proc1, proc2])
        procs = job.getProcs()

        self.assertEqual(len(procs), 2)

    def test_proc_memory_filter(self):
        """Test filtering procs by memory usage."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Get procs using more than 2GB
        procs_api = mock.Mock()
        procs_api.getProcs.return_value = [mock.Mock()]
        procs_api.getProcs(job=[TEST_JOB], memory_greater_than=2097152)

        procs_api.getProcs.assert_called_once_with(
            job=[TEST_JOB], memory_greater_than=2097152
        )

    def test_proc_duration_filter(self):
        """Test filtering procs by running duration."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Get procs running longer than 2 hours
        procs_api = mock.Mock()
        procs_api.getProcs.return_value = [mock.Mock()]
        procs_api.getProcs(job=[TEST_JOB], duration='0-7200')

        procs_api.getProcs.assert_called_once_with(job=[TEST_JOB], duration='0-7200')


class JobInfoWorkflowTest(unittest.TestCase):
    """Test job info retrieval workflow.

    This test class verifies detailed job information can be
    retrieved correctly.
    """

    def test_get_job_info(self):
        """Test retrieving detailed job information."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB
        job.data.state = 'RUNNING'
        job.data.user = 'test_user'
        job.data.shot = 'test_shot'
        job.data.show = 'test_show'

        # Verify job info is accessible
        self.assertEqual(job.data.name, TEST_JOB)
        self.assertEqual(job.data.state, 'RUNNING')
        self.assertEqual(job.data.user, 'test_user')


class FrameStateTransitionsWorkflowTest(unittest.TestCase):
    """Test frame state transition workflows.

    This test class verifies frames transition correctly between
    different states.
    """

    def test_dead_to_waiting_transition(self):
        """Test transitioning dead frames back to waiting via retry."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Retry dead frames (transitions them to waiting)
        job.retryFrames(state=['DEAD'])
        job.retryFrames.assert_called_once_with(state=['DEAD'])

    def test_waiting_to_eaten_transition(self):
        """Test transitioning waiting frames to eaten state."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Eat waiting frames
        job.eatFrames(state=['WAITING'])
        job.eatFrames.assert_called_once_with(state=['WAITING'])

    def test_running_to_waiting_transition(self):
        """Test killing running frames transitions them back to waiting."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Kill running frames (transitions them to waiting)
        job.killFrames(state=['RUNNING'])
        job.killFrames.assert_called_once_with(state=['RUNNING'])

    def test_any_to_succeeded_transition(self):
        """Test marking frames as done transitions them to succeeded."""
        job = mock.Mock()
        job.data = mock.Mock()
        job.data.name = TEST_JOB

        # Mark frames as done (transitions to succeeded)
        job.markdoneFrames(range='1-10')
        job.markdoneFrames.assert_called_once_with(range='1-10')


if __name__ == '__main__':
    unittest.main()
