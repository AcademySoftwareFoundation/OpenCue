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

"""Unit tests for CueAdmin host management commands."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import unittest

import mock

import opencue.wrappers.allocation
import opencue.wrappers.host
import opencue.wrappers.proc
import opencue.wrappers.service
import opencue.wrappers.show
import opencue.wrappers.subscription
from opencue.exception import EntityNotFoundException

import cueadmin.common

TEST_ALLOC = "test_alloc"
TEST_HOST1 = "test_host1"
TEST_HOST2 = "test_host2"
TEST_FACILITY = 'some-non-default-facility'


@mock.patch("opencue.api.getHosts")
@mock.patch('opencue.cuebot.Cuebot.getStub')
@mock.patch('cueadmin.output.displayHosts')
class ListHostsTest(unittest.TestCase):
    """Test cases for the -lh (list hosts) command functionality.

    This class tests various scenarios of listing hosts including:
    - Basic host listing without filters
    - Filtering by state (UP, DOWN, REPAIR)
    - Filtering by allocation
    - Substring matching
    - Invalid argument handling
    - Various combinations of filters
    """

    def setUp(self):
        """Set up test fixtures for ListHostsTest.

        Creates a mock host object with typical render farm host
        properties for use in testing list hosts functionality.
        """
        self.parser = cueadmin.common.getParser()

        # Create a mock host object with proper data attribute structure
        host1 = mock.Mock()
        host1.data = mock.Mock()
        host1.data.name = 'host1'
        host1.data.load = 25
        host1.data.nimby_enabled = False
        host1.data.free_memory = 3500000
        host1.data.free_swap = 1040000
        host1.data.free_mcp = 84782900
        host1.data.cores = 6
        host1.data.memory = 4500000
        host1.data.idle_cores = 5
        host1.data.idle_memory = 3000000
        host1.data.os = 'Linux'
        host1.data.boot_time = 1556836762
        host1.data.state = 1
        host1.data.lock_state = 1
        host1.data.alloc_name = 'alloc01'
        host1.data.thread_mode = 1

        self.mock_hosts = [host1]

    def test_list_hosts_no_filter(self, display_hosts_mock, get_stub_mock, get_hosts_mock):
        """Test the -lh command without any filters.

        Verifies that the list hosts command works correctly when no
        filtering options are provided, should return all hosts.

        Args:
            display_hosts_mock: Mock for cueadmin.output.displayHosts (unused)
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            get_hosts_mock: Mock for opencue.api.getHosts function
        """
        # pylint: disable=unused-argument

        args = self.parser.parse_args(["-lh"])

        get_hosts_mock.return_value = self.mock_hosts
        cueadmin.common.handleArgs(args)

        get_hosts_mock.assert_called_with(alloc=[], match=[], state=[])

    def test_list_hosts_state(self, display_hosts_mock, get_stub_mock, get_hosts_mock):
        """Test the -lh command with state filtering.

        Verifies that the -state filter correctly passes hardware states
        (UP, DOWN, REPAIR) to the opencue.api.getHosts function.

        Args:
            display_hosts_mock: Mock for cueadmin.output.displayHosts (unused)
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            get_hosts_mock: Mock for opencue.api.getHosts function
        """
        # pylint: disable=unused-argument

        args = self.parser.parse_args(["-lh", "-state", "UP", "DOWN", "REPAIR"])

        get_hosts_mock.return_value = self.mock_hosts
        cueadmin.common.handleArgs(args=args)

        get_hosts_mock.assert_called_with(
            alloc=[],
            match=[],
            state=[
                opencue.api.host_pb2.HardwareState.Value('UP'),
                opencue.api.host_pb2.HardwareState.Value('DOWN'),
                opencue.api.host_pb2.HardwareState.Value('REPAIR'),
            ],
        )

    def test_list_hosts_invalid_state(self, display_hosts_mock, get_stub_mock, get_hosts_mock):
        """Test that invalid hardware states raise ValueError.

        Verifies that providing an invalid state string to the -state
        filter raises a ValueError with an appropriate error message.

        Args:
            display_hosts_mock: Mock for cueadmin.output.displayHosts (unused)
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            get_hosts_mock: Mock for opencue.api.getHosts function
        """
        # pylint: disable=unused-argument

        args = self.parser.parse_args(["-lh", "-state", "Invalid"])

        get_hosts_mock.return_value = self.mock_hosts
        with self.assertRaisesRegex(ValueError, "invalid hardware state: INVALID"):
            cueadmin.common.handleArgs(args=args)

    def test_list_hosts_alloc(self, display_hosts_mock, get_stub_mock, get_hosts_mock):
        """Test the -lh command with allocation filtering.

        Verifies that the -alloc filter correctly passes allocation names
        to the opencue.api.getHosts function for filtering hosts.

        Args:
            display_hosts_mock: Mock for cueadmin.output.displayHosts (unused)
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            get_hosts_mock: Mock for opencue.api.getHosts function
        """
        # pylint: disable=unused-argument

        args = self.parser.parse_args(["-lh", "-alloc", TEST_ALLOC])

        get_hosts_mock.return_value = self.mock_hosts
        cueadmin.common.handleArgs(args=args)

        get_hosts_mock.assert_called_with(
            alloc=[TEST_ALLOC],
            match=[],
            state=[],
        )

    def test_list_hosts_empty_alloc_arg(self, display_hosts_mock, get_stub_mock, get_hosts_mock):
        """Test that -alloc flag without arguments causes SystemExit.

        Verifies that providing the -alloc flag without any allocation
        names raises SystemExit due to missing required argument.

        Args:
            display_hosts_mock: Mock for cueadmin.output.displayHosts (unused)
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            get_hosts_mock: Mock for opencue.api.getHosts function (unused)
        """
        # pylint: disable=unused-argument

        with self.assertRaises(SystemExit):
            args = self.parser.parse_args(["-lh", "-alloc"])
            cueadmin.common.handleArgs(args=args)

    def test_list_hosts_combinations(self, display_hosts_mock, get_stub_mock, get_hosts_mock):
        """Test the -lh command with various filter combinations.

        Performs comprehensive testing of different combinations of filters
        including state, allocation, and substring matching to ensure all
        combinations work correctly together.

        Args:
            display_hosts_mock: Mock for cueadmin.output.displayHosts (unused)
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            get_hosts_mock: Mock for opencue.api.getHosts function
        """
        # pylint: disable=unused-argument

        test_cases = [
            (["-lh"], [], [], []),
            (["-lh", "-state", "UP", "DOWN"], [], [],
             [opencue.api.host_pb2.HardwareState.Value('UP'),
              opencue.api.host_pb2.HardwareState.Value('DOWN')]),
            (["-lh", "-alloc", TEST_ALLOC], [TEST_ALLOC], [], []),
            (["-lh", "substring"], [], ["substring"], []),
            (["-lh", "substring", "-alloc", TEST_ALLOC], [TEST_ALLOC], ["substring"], []),
            (["-lh", "substring", "-state", "UP", "-alloc", TEST_ALLOC],
             [TEST_ALLOC], ["substring"], [opencue.api.host_pb2.HardwareState.Value('UP')]),
        ]

        get_hosts_mock.return_value = self.mock_hosts
        for cli_args, expected_alloc, expected_match, expected_state in test_cases:
            with self.subTest(cli_args=cli_args):
                args = self.parser.parse_args(cli_args)
                cueadmin.common.handleArgs(args)
                get_hosts_mock.assert_called_with(
                    alloc=expected_alloc,
                    match=expected_match,
                    state=expected_state,
                )

@mock.patch("opencue.search.HostSearch")
@mock.patch('opencue.cuebot.Cuebot.getStub')
class LockUnlockHostsTest(unittest.TestCase):
    """Test cases for host locking and unlocking operations.

    This class tests the -lock and -unlock commands that allow
    administrators to lock/unlock multiple hosts for maintenance
    or operational purposes.
    """

    def setUp(self):
        """Set up test fixtures for LockUnlockHostsTest.

        Initializes the command line parser for testing host lock/unlock operations.
        """
        self.parser = cueadmin.common.getParser()

    def test_lock_multiple_hosts(self, get_stub_mock, host_search_mock):
        """Test locking multiple hosts with the -lock command.

        Verifies that the -lock command properly searches for hosts by name
        and calls the lock method on each found host.

        Args:
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            host_search_mock: Mock for opencue.search.HostSearch
        """
        # pylint: disable=unused-argument
        args = self.parser.parse_args(['-lock', '-host', TEST_HOST1, TEST_HOST2, '-force'])
        host_mock1 = mock.Mock()
        host_mock2 = mock.Mock()

        host_search_mock.byName.return_value = [host_mock1, host_mock2]

        cueadmin.common.handleArgs(args=args)

        host_search_mock.byName.assert_called_with([TEST_HOST1, TEST_HOST2])
        host_mock1.lock.assert_called_with()
        host_mock2.lock.assert_called_with()

    def test_unlock_multiple_hosts(self, get_stub_mock, host_search_mock):
        """Test unlocking multiple hosts with the -unlock command.

        Verifies that the -unlock command properly searches for hosts by name
        and calls the unlock method on each found host.

        Args:
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            host_search_mock: Mock for opencue.search.HostSearch
        """
        # pylint: disable=unused-argument
        args = self.parser.parse_args(['-unlock', '-host', TEST_HOST1, TEST_HOST2, '-force'])
        host_mock1 = mock.Mock()
        host_mock2 = mock.Mock()

        host_search_mock.byName.return_value = [host_mock1, host_mock2]

        cueadmin.common.handleArgs(args=args)

        host_search_mock.byName.assert_called_with([TEST_HOST1, TEST_HOST2])
        host_mock1.unlock.assert_called_with()
        host_mock2.unlock.assert_called_with()

@mock.patch('opencue.search.HostSearch')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class AllocationTest(unittest.TestCase):
    """Test cases for host allocation management.

    This class tests the -move command that allows moving hosts
    between different allocations, including error handling for
    invalid or non-existent allocations.
    """

    def setUp(self):
        """Set up test fixtures for AllocationTest.

        Initializes the command line parser for testing host allocation operations.
        """
        self.parser = cueadmin.common.getParser()

    @mock.patch('opencue.api.findAllocation')
    def test_invalid_allocation_name(self, find_alloc_mock, get_stub_mock, host_search_mock):
        """Test that moving hosts to invalid allocation raises EntityNotFoundException.

        Verifies that attempting to move a host to a non-existent allocation
        properly raises EntityNotFoundException and does not attempt to
        perform the move operation.

        Args:
            find_alloc_mock: Mock for opencue.api.findAllocation function
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            host_search_mock: Mock for opencue.search.HostSearch
        """
        # pylint: disable=unused-argument

        alloc_name = f'{TEST_FACILITY}.InvalidAlloc'
        args = self.parser.parse_args(['-move', alloc_name, '-host', TEST_HOST1, '-force'])
        host = mock.Mock()
        host.setAllocation = mock.Mock()
        host_search_mock.byName.return_value = [host]

        find_alloc_mock.side_effect = EntityNotFoundException(
            "Object does not exist. Incorrect result size: expected 1, actual 0."
        )

        with self.assertRaises(EntityNotFoundException):
            cueadmin.common.handleArgs(args)

        host_search_mock.byName.assert_called_with([TEST_HOST1])
        find_alloc_mock.assert_called_with(alloc_name)
        host.setAllocation.assert_not_called()


@mock.patch('opencue.search.HostSearch')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class DeleteHostTests(unittest.TestCase):
    """Test cases for host deletion operations.

    This class tests the -delete-host command that allows
    administrators to remove hosts from the render farm,
    including proper error handling during deletion.
    """

    def setUp(self):
        """Set up test fixtures for DeleteHostTests.

        Initializes the command line parser for testing host deletion operations.
        """
        self.parser = cueadmin.common.getParser()

    def test_delete_host(self, get_stub_mock, host_search_mock):
        """Test host deletion with the -delete-host command.

        Verifies that the -delete-host command properly searches for the host
        by name and calls the delete method. Also tests that RuntimeError
        during deletion is properly propagated.

        Args:
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            host_search_mock: Mock for opencue.search.HostSearch
        """
        # pylint: disable=unused-argument
        args = self.parser.parse_args(["-delete-host", "-host", TEST_HOST1, "-force"])

        # Create mock host instead of real Host wrapper to avoid gRPC connection
        host = mock.Mock()
        host.name = TEST_HOST1
        host.load = 25
        host.nimby_enabled = False
        host.free_memory = 3500000
        host.free_swap = 1040000
        host.free_mcp = 84782900
        host.cores = 6
        host.memory = 4500000
        host.idle_cores = 5
        host.idle_memory = 3000000
        host.os = "Linux"
        host.boot_time = 1556836762
        host.state = 1
        host.lock_state = 1
        host.alloc_name = "alloc01"
        host.thread_mode = 1
        host.delete = mock.Mock(side_effect=RuntimeError)

        host_search_mock.byName.return_value = [host]

        with self.assertRaises(RuntimeError):
            cueadmin.common.handleArgs(args)

        host.delete.assert_called_once()


@mock.patch('opencue.search.HostSearch')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class HostStateManagementTest(unittest.TestCase):
    """Test cases for host state management commands.

    This class tests the -repair and -fixed commands that allow
    administrators to change host hardware states for maintenance
    and operational purposes.
    """

    def setUp(self):
        """Set up test fixtures for HostStateManagementTest.

        Initializes the command line parser for testing host state operations.
        """
        self.parser = cueadmin.common.getParser()

    def test_repair_host(self, get_stub_mock, host_search_mock):
        """Test setting host to REPAIR state with -repair command.

        Verifies that the -repair command properly searches for hosts by name
        and calls setHardwareState with REPAIR state.

        Args:
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            host_search_mock: Mock for opencue.search.HostSearch
        """
        # pylint: disable=unused-argument
        args = self.parser.parse_args(['-repair', '-host', TEST_HOST1, '-force'])
        host_mock = mock.Mock()
        host_search_mock.byName.return_value = [host_mock]

        cueadmin.common.handleArgs(args=args)

        host_search_mock.byName.assert_called_with([TEST_HOST1])
        host_mock.setHardwareState.assert_called_with(opencue.api.host_pb2.REPAIR)

    def test_fixed_host(self, get_stub_mock, host_search_mock):
        """Test setting host to UP state with -fixed command.

        Verifies that the -fixed command properly searches for hosts by name
        and calls setHardwareState with UP state.

        Args:
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            host_search_mock: Mock for opencue.search.HostSearch
        """
        # pylint: disable=unused-argument
        args = self.parser.parse_args(['-fixed', '-host', TEST_HOST1, '-force'])
        host_mock = mock.Mock()
        host_search_mock.byName.return_value = [host_mock]

        cueadmin.common.handleArgs(args=args)

        host_search_mock.byName.assert_called_with([TEST_HOST1])
        host_mock.setHardwareState.assert_called_with(opencue.api.host_pb2.UP)

    def test_thread_command(self, get_stub_mock, host_search_mock):
        """Test setting host thread mode with -thread command.

        Verifies that the -thread command properly searches for hosts by name
        and calls setThreadMode with the specified thread mode.

        Args:
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            host_search_mock: Mock for opencue.search.HostSearch
        """
        # pylint: disable=unused-argument
        args = self.parser.parse_args(['-thread', 'auto', '-host', TEST_HOST1, '-force'])
        host_mock = mock.Mock()
        host_search_mock.byName.return_value = [host_mock]

        cueadmin.common.handleArgs(args=args)

        host_search_mock.byName.assert_called_with([TEST_HOST1])
        host_mock.setThreadMode.assert_called_with(opencue.api.host_pb2.AUTO)

    def test_safe_reboot_host(self, get_stub_mock, host_search_mock):
        """Test safe reboot with -safe-reboot command.

        Verifies that the -safe-reboot command properly searches for hosts by name
        and calls rebootWhenIdle method.

        Args:
            get_stub_mock: Mock for opencue.cuebot.Cuebot.getStub (unused)
            host_search_mock: Mock for opencue.search.HostSearch
        """
        # pylint: disable=unused-argument
        args = self.parser.parse_args(['-safe-reboot', '-host', TEST_HOST1, '-force'])
        host_mock = mock.Mock()
        host_search_mock.byName.return_value = [host_mock]

        cueadmin.common.handleArgs(args=args)

        host_search_mock.byName.assert_called_with([TEST_HOST1])
        host_mock.rebootWhenIdle.assert_called_with()


if __name__ == "__main__":
    unittest.main()
