from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
import unittest

import mock

import opencue_proto.facility_pb2
import opencue_proto.host_pb2
import opencue_proto.job_pb2
import opencue_proto.service_pb2
import opencue_proto.show_pb2
import opencue_proto.subscription_pb2
import opencue.wrappers.allocation
import opencue.wrappers.host
import opencue.wrappers.proc
import opencue.wrappers.service
import opencue.wrappers.show
import opencue.wrappers.subscription

import cueadmin.common

TEST_ALLOC = "test_alloc"
TEST_HOST1 = "test_host1"
TEST_HOST2 = "test_host2"
TEST_FACILITY = 'some-non-default-facility'


@mock.patch("opencue.api.getHosts")
class ListHostsTest(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

        host1 = opencue.wrappers.host.Host(
                opencue_proto.host_pb2.Host(
                    name='host1',
                    load=25,
                    nimby_enabled=False,
                    free_memory=3500000,
                    free_swap=1040000,
                    free_mcp=84782900,
                    cores=6,
                    memory=4500000,
                    idle_cores=5,
                    idle_memory=3000000,
                    os='Linux',
                    boot_time=1556836762,
                    state=1,
                    lock_state=1,
                    alloc_name='alloc01',
                    thread_mode=1
                )
            )
        
        self.mock_hosts = [host1] 

    def testListHostsNoFilter(self, getHostsMock):
        """Tests the -lh command without any filters"""

        args = self.parser.parse_args(["-lh"])

        getHostsMock.return_value = self.mock_hosts
        cueadmin.common.handleArgs(args)

        getHostsMock.assert_called_with(alloc=[], match=[], state=[])

    def testListHostsState(self, getHostsMock):

        """Tests the -state implementation without other combinations"""

        args = self.parser.parse_args(["-lh", "-state", "UP", "DOWN", "REPAIR"])

        getHostsMock.return_value = self.mock_hosts
        cueadmin.common.handleArgs(args=args)

        getHostsMock.assert_called_with(
            alloc=[],
            match=[],
            state=[
                opencue.api.host_pb2.UP,
                opencue.api.host_pb2.DOWN,
                opencue.api.host_pb2.REPAIR,
            ],
        )
    
    def testListHostsInvalidState(self, getHostsMock):
        
        """Throws error when state is not UP, DOWN, REPAIR"""

        args = self.parser.parse_args(["-lh", "-state", "Invalid"])
        
        getHostsMock.return_value = self.mock_hosts
        with self.assertRaisesRegex(ValueError, "invalid hardware state: INVALID"):
            cueadmin.common.handleArgs(args=args)
    
    def testListHostsAlloc(self, getHostsMock):

        """Checks whether -alloc along with substring is received or not"""

        args = self.parser.parse_args(["-lh", "-alloc", TEST_ALLOC])

        getHostsMock.return_value = self.mock_hosts
        cueadmin.common.handleArgs(args=args)

        getHostsMock.assert_called_with(
            alloc=[TEST_ALLOC],
            match=[],
            state=[],
        )
    
    def testListHostsEmptyAllocArg(self, getHostsMock):

        """System Exit when substring not provided with -alloc flag"""
        
        with self.assertRaises(SystemExit):
            args = self.parser.parse_args(["-lh", "-alloc"])
            cueadmin.common.handleArgs(args=args)
        
    def testListHostsCombinations(self, getHostsMock):

        """Tests the -lh command for various combinations"""

        test_cases = [
            (["-lh"], [], [], []),
            (["-lh", "-state", "UP", "DOWN"], [], [], [opencue.api.host_pb2.UP, opencue.api.host_pb2.DOWN]),
            (["-lh", "-alloc", TEST_ALLOC], [TEST_ALLOC], [], []),
            (["-lh", "substring"], [], ["substring"], []),
            (["-lh", "substring", "-alloc", TEST_ALLOC], [TEST_ALLOC], ["substring"], []),
            (["-lh", "substring", "-state", "UP", "-alloc", TEST_ALLOC], [TEST_ALLOC], ["substring"], [opencue.api.host_pb2.UP]),
        ]

        getHostsMock.return_value = self.mock_hosts
        for cli_args, expected_alloc, expected_match, expected_state in test_cases:
            with self.subTest(cli_args=cli_args):
                args = self.parser.parse_args(cli_args)
                cueadmin.common.handleArgs(args)
                getHostsMock.assert_called_with(
                    alloc=expected_alloc,
                    match=expected_match,
                    state=expected_state,
                )

@mock.patch("opencue.search.HostSearch")
class LockUnlockHostsTest(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    def testLockMultipleHosts(self, hostSearchMock):
        args = self.parser.parse_args(['-lock', '-host', TEST_HOST1, TEST_HOST2, '-force'])
        hostMock1 = mock.Mock()
        hostMock2 = mock.Mock()

        hostSearchMock.byName.return_value = [hostMock1, hostMock2]

        cueadmin.common.handleArgs(args=args)

        hostSearchMock.byName.assert_called_with([TEST_HOST1, TEST_HOST2])
        hostMock1.lock.assert_called_with()
        hostMock2.lock.assert_called_with()
    
    def testUnlockMultipleHosts(self, hostSearchMock):
        args = self.parser.parse_args(['-unlock', '-host', TEST_HOST1, TEST_HOST2, '-force'])
        hostMock1 = mock.Mock()
        hostMock2 = mock.Mock()

        hostSearchMock.byName.return_value = [hostMock1, hostMock2]

        cueadmin.common.handleArgs(args=args)

        hostSearchMock.byName.assert_called_with([TEST_HOST1, TEST_HOST2])
        hostMock1.unlock.assert_called_with()
        hostMock2.unlock.assert_called_with()

@mock.patch('opencue.search.HostSearch')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class AllocationTest(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    @mock.patch('opencue.api.findAllocation')
    def testInvalidAllocationName(self, findAllocMock, getStubMock, hostSearchMock):

        """Raises error when allocation does not exist"""

        allocName = '%s.%s' % (TEST_FACILITY, "InvalidAlloc")
        args = self.parser.parse_args(['-move', allocName, '-host', TEST_HOST1, '-force'])
        host = opencue.wrappers.host.Host(opencue_proto.host_pb2.Host())
        host.setAllocation = mock.Mock()
        hostSearchMock.byName.return_value = [host]

        from opencue.exception import EntityNotFoundException
        findAllocMock.side_effect = EntityNotFoundException(
            "Object does not exist. Incorrect result size: expected 1, actual 0."
        )

        with self.assertRaises(EntityNotFoundException):
            cueadmin.common.handleArgs(args)

        hostSearchMock.byName.assert_called_with([TEST_HOST1])
        findAllocMock.assert_called_with(allocName)
        host.setAllocation.assert_not_called()


@mock.patch('opencue.search.HostSearch')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class DeleteHostTests(unittest.TestCase):

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    def testDeleteHost(self, getStubMock, hostSearchMock):
        args = self.parser.parse_args(["-delete-host", "-host", TEST_HOST1, "-force"])

        hostProto = opencue_proto.host_pb2.Host(
            name=TEST_HOST1,
            load=25,
            nimby_enabled=False,
            free_memory=3500000,
            free_swap=1040000,
            free_mcp=84782900,
            cores=6,
            memory=4500000,
            idle_cores=5,
            idle_memory=3000000,
            os="Linux",
            boot_time=1556836762,
            state=1,
            lock_state=1,
            alloc_name="alloc01",
            thread_mode=1,
        )
        host = opencue.wrappers.host.Host(hostProto)
        host.delete = mock.Mock(side_effect=RuntimeError)

        hostSearchMock.byName.return_value = [host]

        with self.assertRaises(RuntimeError):
            cueadmin.common.handleArgs(args)

        host.delete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
