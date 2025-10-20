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


"""
Unit tests for proc management commands in cueadmin.

This module tests the following proc operations:
- Listing running procs with various filters
- Listing frame log paths
- Killing specific procs
- Unbooking procs from hosts
- Memory filter parsing (ranges, gt/lt operators)
- Duration filter for long-running frames
- Limit result limiting
"""

import unittest
from unittest.mock import patch, MagicMock

import opencue
import opencue.wrappers.proc
import opencue_proto.host_pb2

import cueadmin.common


@patch('opencue.cuebot.Cuebot.getStub')
class TestProcListingCommands(unittest.TestCase):
    """Test suite for proc listing commands."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = cueadmin.common.getParser()

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_list_procs_no_filters(self, _mock_display, mock_search, _mock_get_stub):
        """Test listing procs without any filters."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            reserved_cores=16,
            used_memory=8388608,
            reserved_memory=16777216,
            job_name='test_job',
            frame_name='test_frame',
            dispatch_time=1234567890
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp'])
        cueadmin.common.handleArgs(args)

        # Assert
        mock_search.assert_called_once()
        _mock_display.assert_called_once()

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_list_procs_by_show(self, _mock_display, mock_search, _mock_get_stub):
        """Test listing procs filtered by show."""
        # Arrange
        show_name = 'test_show'
        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            show_name=show_name,
            reserved_cores=8,
            job_name='test_job'
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', show_name])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['show'], [show_name])

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_list_procs_by_job(self, _mock_display, mock_search, _mock_get_stub):
        """Test listing procs filtered by job."""
        # Arrange
        job_name = 'test_job'
        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            job_name=job_name
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-job', job_name])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['job'], [job_name])

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_list_procs_by_allocation(self, _mock_display, mock_search, _mock_get_stub):
        """Test listing procs filtered by allocation."""
        # Arrange
        alloc_name = 'test_alloc'
        mock_proc = opencue_proto.host_pb2.Proc(name='test_proc')
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-alloc', alloc_name])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['alloc'], [alloc_name])

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_list_procs_by_host(self, _mock_display, mock_search, _mock_get_stub):
        """Test listing procs filtered by host."""
        # Arrange
        host_name = 'render_host_01'
        mock_proc = opencue_proto.host_pb2.Proc(name='test_proc')
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-host', host_name])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['host'], [host_name])

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_list_procs_with_limit(self, _mock_display, mock_search, _mock_get_stub):
        """Test listing procs with result limit."""
        # Arrange
        limit = '25'
        mock_proc = opencue_proto.host_pb2.Proc(name='test_proc')
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-limit', limit])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['limit'], limit)

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_list_procs_multiple_filters(self, _mock_display, mock_search, _mock_get_stub):
        """Test listing procs with multiple filters combined."""
        # Arrange
        show_name = 'test_show'
        job_name = 'test_job'
        alloc_name = 'test_alloc'
        host_name = 'render01'
        limit = '50'

        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            show_name=show_name,
            job_name=job_name
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args([
            '-lp', show_name,
            '-job', job_name,
            '-alloc', alloc_name,
            '-host', host_name,
            '-limit', limit
        ])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['show'], [show_name])
        self.assertEqual(call_kwargs['job'], [job_name])
        self.assertEqual(call_kwargs['alloc'], [alloc_name])
        self.assertEqual(call_kwargs['host'], [host_name])
        self.assertEqual(call_kwargs['limit'], limit)


@patch('opencue.cuebot.Cuebot.getStub')
class TestMemoryFiltering(unittest.TestCase):
    """Test suite for memory filter parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = cueadmin.common.getParser()

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_memory_filter_greater_than(self, _mock_display, mock_search, _mock_get_stub):
        """Test memory filter with greater than operator."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            reserved_memory=17179869184  # 16 GB in KB
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-memory', 'gt8'])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        memory_criteria = call_kwargs['memory']
        self.assertEqual(len(memory_criteria), 1)
        self.assertIsInstance(
            memory_criteria[0],
            opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion
        )
        # 8 GB in KB = 8 * 1024 * 1024 = 8388608
        self.assertEqual(memory_criteria[0].value, 8388608)

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_memory_filter_less_than(self, _mock_display, mock_search, _mock_get_stub):
        """Test memory filter with less than operator."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            reserved_memory=4194304  # 4 GB in KB
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-memory', 'lt16'])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        memory_criteria = call_kwargs['memory']
        self.assertEqual(len(memory_criteria), 1)
        self.assertIsInstance(
            memory_criteria[0],
            opencue.api.criterion_pb2.LessThanIntegerSearchCriterion
        )
        # 16 GB in KB = 16 * 1024 * 1024 = 16777216
        self.assertEqual(memory_criteria[0].value, 16777216)

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_memory_filter_range(self, _mock_display, mock_search, _mock_get_stub):
        """Test memory filter with range specification."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            reserved_memory=10485760  # 10 GB in KB
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-memory', '8-16'])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        memory_criteria = call_kwargs['memory']
        self.assertEqual(len(memory_criteria), 1)
        self.assertIsInstance(
            memory_criteria[0],
            opencue.api.criterion_pb2.InRangeIntegerSearchCriterion
        )
        # 8 GB in KB = 8388608, 16 GB in KB = 16777216
        self.assertEqual(memory_criteria[0].min, 8388608)
        self.assertEqual(memory_criteria[0].max, 16777216)

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_memory_filter_single_value(self, _mock_display, mock_search, _mock_get_stub):
        """Test memory filter with single value (defaults to greater than)."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            reserved_memory=16777216  # 16 GB in KB
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-memory', '12'])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        memory_criteria = call_kwargs['memory']
        self.assertEqual(len(memory_criteria), 1)
        self.assertIsInstance(
            memory_criteria[0],
            opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion
        )
        # 12 GB in KB = 12582912
        self.assertEqual(memory_criteria[0].value, 12582912)


@patch('opencue.cuebot.Cuebot.getStub')
class TestDurationFiltering(unittest.TestCase):
    """Test suite for duration filter parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = cueadmin.common.getParser()

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_duration_filter_single_value(self, _mock_display, mock_search, _mock_get_stub):
        """Test duration filter with single value in hours."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(name='test_proc')
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-duration', '2'])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        duration_criteria = call_kwargs['duration']
        self.assertEqual(len(duration_criteria), 1)
        self.assertIsInstance(
            duration_criteria[0],
            opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion
        )
        # 2 hours in seconds = 7200
        self.assertEqual(duration_criteria[0].value, 7200)

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_duration_filter_decimal_hours(self, _mock_display, mock_search, _mock_get_stub):
        """Test duration filter with decimal hours."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(name='test_proc')
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-duration', '1.5'])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        duration_criteria = call_kwargs['duration']
        self.assertEqual(len(duration_criteria), 1)
        # 1.5 hours in seconds = 5400
        self.assertEqual(duration_criteria[0].value, 5400)

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_duration_filter_range(self, _mock_display, mock_search, _mock_get_stub):
        """Test duration filter with time range."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(name='test_proc')
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-duration', '2-4'])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        duration_criteria = call_kwargs['duration']
        self.assertEqual(len(duration_criteria), 1)
        self.assertIsInstance(
            duration_criteria[0],
            opencue.api.criterion_pb2.InRangeIntegerSearchCriterion
        )
        # 2 hours = 7200 seconds, 4 hours = 14400 seconds
        self.assertEqual(duration_criteria[0].min, 7200)
        self.assertEqual(duration_criteria[0].max, 14400)

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_duration_filter_greater_than(self, _mock_display, mock_search, _mock_get_stub):
        """Test duration filter with greater than operator."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(name='test_proc')
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-duration', 'gt3'])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        duration_criteria = call_kwargs['duration']
        self.assertEqual(len(duration_criteria), 1)
        # 3 hours = 10800 seconds
        self.assertEqual(duration_criteria[0].value, 10800)

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_duration_filter_less_than(self, _mock_display, mock_search, _mock_get_stub):
        """Test duration filter with less than operator."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(name='test_proc')
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-lp', '-duration', 'lt5'])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        duration_criteria = call_kwargs['duration']
        self.assertEqual(len(duration_criteria), 1)
        self.assertIsInstance(
            duration_criteria[0],
            opencue.api.criterion_pb2.LessThanIntegerSearchCriterion
        )
        # 5 hours = 18000 seconds
        self.assertEqual(duration_criteria[0].value, 18000)


@patch('opencue.cuebot.Cuebot.getStub')
class TestFrameLogPaths(unittest.TestCase):
    """Test suite for listing frame log paths."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = cueadmin.common.getParser()

    @patch('opencue.search.ProcSearch.byOptions')
    def test_list_frame_log_paths(self, mock_search, _mock_get_stub):
        """Test listing frame log paths."""
        # Arrange
        log_path = '/path/to/frame/log/file.log'
        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            log_path=log_path
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-ll'])
        cueadmin.common.handleArgs(args)

        # Assert
        mock_search.assert_called_once()

    @patch('opencue.search.ProcSearch.byOptions')
    def test_list_frame_log_paths_with_filters(self, mock_search, _mock_get_stub):
        """Test listing frame log paths with filters."""
        # Arrange
        show_name = 'test_show'
        job_name = 'test_job'
        log_path = '/path/to/log.log'

        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            show_name=show_name,
            job_name=job_name,
            log_path=log_path
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args([
            '-ll', show_name,
            '-job', job_name
        ])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['show'], [show_name])
        self.assertEqual(call_kwargs['job'], [job_name])

    @patch('opencue.search.ProcSearch.byOptions')
    def test_list_frame_log_paths_with_memory_filter(self, mock_search, _mock_get_stub):
        """Test listing frame log paths with memory filter."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            log_path='/log.log',
            reserved_memory=16777216
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args(['-ll', '-memory', '10-20'])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        memory_criteria = call_kwargs['memory']
        self.assertEqual(len(memory_criteria), 1)
        self.assertIsInstance(
            memory_criteria[0],
            opencue.api.criterion_pb2.InRangeIntegerSearchCriterion
        )

    @patch('opencue.search.ProcSearch.byOptions')
    def test_list_frame_log_paths_with_duration_and_limit(self, mock_search, _mock_get_stub):
        """Test listing frame log paths with duration filter and limit."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            log_path='/log.log'
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args([
            '-ll',
            '-duration', '2.5',
            '-limit', '100'
        ])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        duration_criteria = call_kwargs['duration']
        self.assertEqual(len(duration_criteria), 1)
        # 2.5 hours = 9000 seconds
        self.assertEqual(duration_criteria[0].value, 9000)
        self.assertEqual(call_kwargs['limit'], '100')


@patch('opencue.cuebot.Cuebot.getStub')
class TestProcKillCommand(unittest.TestCase):
    """Test suite for kill proc command."""

    def test_kill_proc_method(self, _mock_get_stub):
        """Test proc kill method."""
        # Arrange
        mock_proc_data = opencue_proto.host_pb2.Proc(
            id='proc-123',
            name='test_proc',
            job_name='test_job',
            frame_name='test_frame'
        )
        proc = opencue.wrappers.proc.Proc(mock_proc_data)
        proc.stub = MagicMock()

        # Act
        proc.kill()

        # Assert
        proc.stub.Kill.assert_called_once()
        call_args = proc.stub.Kill.call_args
        self.assertEqual(call_args[0][0].proc, mock_proc_data)

    def test_kill_multiple_procs(self, _mock_get_stub):
        """Test killing multiple procs."""
        # Arrange
        procs = []
        for i in range(3):
            mock_proc_data = opencue_proto.host_pb2.Proc(
                id=f'proc-{i}',
                name=f'test_proc_{i}',
                job_name='test_job'
            )
            proc = opencue.wrappers.proc.Proc(mock_proc_data)
            proc.stub = MagicMock()
            procs.append(proc)

        # Act
        for proc in procs:
            proc.kill()

        # Assert
        for proc in procs:
            proc.stub.Kill.assert_called_once()


@patch('opencue.cuebot.Cuebot.getStub')
class TestProcUnbookCommand(unittest.TestCase):
    """Test suite for unbook proc command."""

    def test_unbook_proc_without_kill(self, _mock_get_stub):
        """Test unbooking proc without killing frame."""
        # Arrange
        mock_proc_data = opencue_proto.host_pb2.Proc(
            id='proc-123',
            name='test_proc',
            job_name='test_job',
            frame_name='test_frame'
        )
        proc = opencue.wrappers.proc.Proc(mock_proc_data)
        proc.stub = MagicMock()

        # Act
        proc.unbook(kill=False)

        # Assert
        proc.stub.Unbook.assert_called_once()
        call_args = proc.stub.Unbook.call_args
        self.assertEqual(call_args[0][0].proc, mock_proc_data)
        self.assertFalse(call_args[0][0].kill)

    def test_unbook_proc_with_kill(self, _mock_get_stub):
        """Test unbooking proc with immediate kill."""
        # Arrange
        mock_proc_data = opencue_proto.host_pb2.Proc(
            id='proc-123',
            name='test_proc',
            job_name='test_job',
            frame_name='test_frame'
        )
        proc = opencue.wrappers.proc.Proc(mock_proc_data)
        proc.stub = MagicMock()

        # Act
        proc.unbook(kill=True)

        # Assert
        proc.stub.Unbook.assert_called_once()
        call_args = proc.stub.Unbook.call_args
        self.assertEqual(call_args[0][0].proc, mock_proc_data)
        self.assertTrue(call_args[0][0].kill)

    def test_unbook_multiple_procs(self, _mock_get_stub):
        """Test unbooking multiple procs from hosts."""
        # Arrange
        procs = []
        for i in range(5):
            mock_proc_data = opencue_proto.host_pb2.Proc(
                id=f'proc-{i}',
                name=f'render_proc_{i}',
                job_name='batch_job'
            )
            proc = opencue.wrappers.proc.Proc(mock_proc_data)
            proc.stub = MagicMock()
            procs.append(proc)

        # Act
        for proc in procs:
            proc.unbook(kill=False)

        # Assert
        for proc in procs:
            proc.stub.Unbook.assert_called_once()

    def test_unbook_proc_default_kill_parameter(self, _mock_get_stub):
        """Test unbook proc with default kill parameter (False)."""
        # Arrange
        mock_proc_data = opencue_proto.host_pb2.Proc(
            id='proc-123',
            name='test_proc'
        )
        proc = opencue.wrappers.proc.Proc(mock_proc_data)
        proc.stub = MagicMock()

        # Act
        proc.unbook()

        # Assert
        proc.stub.Unbook.assert_called_once()
        call_args = proc.stub.Unbook.call_args
        self.assertFalse(call_args[0][0].kill)


@patch('opencue.cuebot.Cuebot.getStub')
class TestProcDataAccess(unittest.TestCase):
    """Test suite for proc data access methods."""

    def test_proc_basic_properties(self, _mock_get_stub):
        """Test accessing basic proc properties."""
        # Arrange
        mock_proc_data = opencue_proto.host_pb2.Proc(
            id='proc-123',
            name='render_proc',
            job_name='test_job',
            frame_name='frame_0001',
            show_name='test_show',
            reserved_cores=16.0,
            reserved_memory=16777216,
            used_memory=8388608
        )
        proc = opencue.wrappers.proc.Proc(mock_proc_data)

        # Assert
        self.assertEqual(proc.id(), 'proc-123')
        self.assertEqual(proc.name(), 'render_proc')
        self.assertEqual(proc.jobName(), 'test_job')
        self.assertEqual(proc.frameName(), 'frame_0001')
        self.assertEqual(proc.showName(), 'test_show')
        self.assertEqual(proc.coresReserved(), 16.0)
        self.assertEqual(proc.memReserved(), 16777216)
        self.assertEqual(proc.memUsed(), 8388608)

    def test_proc_time_properties(self, _mock_get_stub):
        """Test accessing proc time-related properties."""
        # Arrange
        dispatch_time = 1234567900
        mock_proc_data = opencue_proto.host_pb2.Proc(
            id='proc-123',
            name='test_proc',
            dispatch_time=dispatch_time
        )
        proc = opencue.wrappers.proc.Proc(mock_proc_data)

        # Assert
        self.assertEqual(proc.dispatchTime(), dispatch_time)

    def test_proc_unbooked_status(self, _mock_get_stub):
        """Test proc unbooked status."""
        # Arrange
        mock_proc_data = opencue_proto.host_pb2.Proc(
            id='proc-123',
            name='test_proc',
            unbooked=True
        )
        proc = opencue.wrappers.proc.Proc(mock_proc_data)

        # Assert
        self.assertTrue(proc.isUnbooked())


@patch('opencue.cuebot.Cuebot.getStub')
class TestComplexProcScenarios(unittest.TestCase):
    """Test suite for complex proc management scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = cueadmin.common.getParser()

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_filter_high_memory_long_running_procs(
            self, _mock_display, mock_search, _mock_get_stub):
        """Test filtering procs by high memory usage and long duration."""
        # Arrange
        mock_proc = opencue_proto.host_pb2.Proc(
            name='high_mem_proc',
            reserved_memory=33554432,  # 32 GB in KB
            dispatch_time=1234567890
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args([
            '-lp',
            '-memory', 'gt24',
            '-duration', 'gt5',
            '-limit', '20'
        ])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        memory_criteria = call_kwargs['memory']
        duration_criteria = call_kwargs['duration']

        self.assertEqual(len(memory_criteria), 1)
        self.assertEqual(memory_criteria[0].value, 25165824)  # 24 GB in KB

        self.assertEqual(len(duration_criteria), 1)
        self.assertEqual(duration_criteria[0].value, 18000)  # 5 hours in seconds

        self.assertEqual(call_kwargs['limit'], '20')

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_filter_procs_by_show_and_allocation(self, _mock_display, mock_search, _mock_get_stub):
        """Test filtering procs by both show and allocation."""
        # Arrange
        show_name = 'feature_film'
        alloc_name = 'gpu_alloc'
        mock_proc = opencue_proto.host_pb2.Proc(
            name='test_proc',
            show_name=show_name
        )
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args([
            '-lp', show_name,
            '-alloc', alloc_name
        ])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['show'], [show_name])
        self.assertEqual(call_kwargs['alloc'], [alloc_name])

    @patch('opencue.search.ProcSearch.byOptions')
    @patch('cueadmin.output.displayProcs')
    def test_multiple_jobs_and_hosts(self, _mock_display, mock_search, _mock_get_stub):
        """Test filtering procs by multiple jobs and hosts."""
        # Arrange
        job1, job2 = 'job_a', 'job_b'
        host1, host2 = 'render01', 'render02'

        mock_proc = opencue_proto.host_pb2.Proc(name='test_proc')
        mock_search.return_value = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[mock_proc])
        )

        # Act
        args = self.parser.parse_args([
            '-lp',
            '-job', job1, job2,
            '-host', host1, host2
        ])
        cueadmin.common.handleArgs(args)

        # Assert
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs['job'], [job1, job2])
        self.assertEqual(call_kwargs['host'], [host1, host2])


@patch('opencue.cuebot.Cuebot.getStub')
class TestEdgeCasesAndValidation(unittest.TestCase):
    """Test suite for edge cases and validation."""

    def test_memory_filter_validation_zero_gb(self, _mock_get_stub):
        """Test memory filter with zero GB."""
        # Arrange & Act
        result = cueadmin.common.handleIntCriterion(
            '0',
            cueadmin.common.Convert.gigsToKB
        )

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].value, 0)

    def test_memory_filter_validation_large_value(self, _mock_get_stub):
        """Test memory filter with large memory value."""
        # Arrange & Act
        result = cueadmin.common.handleIntCriterion(
            '512',
            cueadmin.common.Convert.gigsToKB
        )

        # Assert
        self.assertEqual(len(result), 1)
        # 512 GB in KB = 536870912
        self.assertEqual(result[0].value, 536870912)

    def test_duration_filter_validation_fractional_hours(self, _mock_get_stub):
        """Test duration filter with fractional hours."""
        # Arrange & Act
        result = cueadmin.common.handleIntCriterion(
            '0.25',
            cueadmin.common.Convert.hoursToSeconds
        )

        # Assert
        self.assertEqual(len(result), 1)
        # 0.25 hours = 900 seconds
        self.assertEqual(result[0].value, 900)

    def test_empty_proc_list(self, _mock_get_stub):
        """Test handling empty proc list."""
        # Arrange
        empty_response = opencue_proto.host_pb2.ProcGetProcsResponse(
            procs=opencue_proto.host_pb2.ProcSeq(procs=[])
        )

        # Assert
        self.assertEqual(len(empty_response.procs.procs), 0)

    def test_proc_with_minimal_data(self, _mock_get_stub):
        """Test proc with minimal required data."""
        # Arrange
        mock_proc_data = opencue_proto.host_pb2.Proc(
            id='proc-minimal',
            name='minimal_proc'
        )
        proc = opencue.wrappers.proc.Proc(mock_proc_data)

        # Assert
        self.assertEqual(proc.id(), 'proc-minimal')
        self.assertEqual(proc.name(), 'minimal_proc')


if __name__ == '__main__':
    unittest.main()
