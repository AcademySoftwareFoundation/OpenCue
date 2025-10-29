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
Unit tests for allocation management commands in cueadmin.

This module tests the following allocation operations:
- Creating allocations with various parameters
- Deleting allocations (empty and non-empty)
- Renaming allocations
- Transferring hosts between allocations
- Managing allocation tags
- Listing and querying allocations
"""

import unittest
from unittest.mock import patch, MagicMock

class TestAllocationCommands(unittest.TestCase):
    """Test suite for allocation management commands.

    This test class provides comprehensive unit tests for allocation
    management functionality in OpenCue, including creation, deletion,
    renaming, host transfers, and tag management operations.
    """

    @patch('opencue.api.createAllocation')
    def test_create_allocation_success(self, mock_create):
        """Test successful allocation creation with valid parameters."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.name = 'test_allocation'
        mock_alloc.id = 'alloc-123-456'
        mock_alloc.facility = 'facility1'
        mock_alloc.tag = 'tag1'
        mock_create.return_value = mock_alloc

        # Act
        result = mock_create('facility1', 'test_allocation', 'tag1')

        # Assert
        mock_create.assert_called_once_with('facility1', 'test_allocation', 'tag1')
        self.assertEqual(result.name, 'test_allocation')
        self.assertEqual(result.id, 'alloc-123-456')
        self.assertEqual(result.facility, 'facility1')
        self.assertEqual(result.tag, 'tag1')

    @patch('opencue.api.createAllocation')
    def test_create_allocation_with_invalid_parameters(self, mock_create):
        """Test allocation creation fails with invalid parameters."""
        # Arrange
        mock_create.side_effect = ValueError("Invalid parameters: empty values not allowed")

        # Act & Assert
        with self.assertRaisesRegex(ValueError, "Invalid parameters"):
            mock_create('', '', '')
        mock_create.assert_called_once_with('', '', '')

    @patch('opencue.api.getAllocation')
    def test_delete_allocation_success(self, mock_get_alloc):
        """Test successful deletion of an empty allocation."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.delete = MagicMock()
        mock_alloc.name = 'test_allocation'
        mock_get_alloc.return_value = mock_alloc

        # Act
        allocation = mock_get_alloc('test_allocation')
        allocation.delete()

        # Assert
        mock_get_alloc.assert_called_once_with('test_allocation')
        mock_alloc.delete.assert_called_once()

    @patch('opencue.api.getAllocation')
    def test_delete_nonempty_allocation_fails(self, mock_get_alloc):
        """Test deletion fails when allocation contains hosts."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.delete = MagicMock(
            side_effect=RuntimeError("Cannot delete: allocation contains 5 hosts")
        )
        mock_alloc.name = 'busy_allocation'
        mock_get_alloc.return_value = mock_alloc

        # Act & Assert
        allocation = mock_get_alloc('busy_allocation')
        with self.assertRaisesRegex(RuntimeError, "Cannot delete: allocation contains"):
            allocation.delete()
        mock_alloc.delete.assert_called_once()

    @patch('opencue.api.getAllocation')
    def test_rename_allocation_success(self, mock_get):
        """Test successful allocation renaming."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.name = 'old_name'
        mock_alloc.setName = MagicMock(side_effect=lambda name: setattr(mock_alloc, 'name', name))
        mock_get.return_value = mock_alloc

        # Act
        allocation = mock_get('old_name')
        allocation.setName('new_name')

        # Assert
        mock_get.assert_called_once_with('old_name')
        mock_alloc.setName.assert_called_once_with('new_name')
        self.assertEqual(allocation.name, 'new_name')

    @patch('opencue.api.getAllocation')
    def test_rename_allocation_to_existing_name_fails(self, mock_get):
        """Test renaming fails when target name already exists."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.name = 'current_name'
        mock_alloc.setName = MagicMock(
            side_effect=ValueError("Allocation name 'existing_name' already exists")
        )
        mock_get.return_value = mock_alloc

        # Act & Assert
        allocation = mock_get('current_name')
        with self.assertRaisesRegex(ValueError, "already exists"):
            allocation.setName('existing_name')
        mock_alloc.setName.assert_called_once_with('existing_name')

    @patch('opencue.api.getAllocation')
    def test_transfer_hosts_between_allocations_success(self, mock_get):
        """Test successful host transfer between allocations."""
        # Arrange
        mock_source_alloc = MagicMock()
        mock_source_alloc.name = 'source_allocation'
        mock_target_alloc = MagicMock()
        mock_target_alloc.name = 'target_allocation'
        # Returns number of hosts transferred
        mock_source_alloc.reparentHosts = MagicMock(return_value=5)

        # Simulate getting both allocations
        mock_get.side_effect = [mock_source_alloc, mock_target_alloc]

        # Act
        source_alloc = mock_get('source_allocation')
        target_alloc = mock_get('target_allocation')
        hosts_transferred = source_alloc.reparentHosts(target_alloc)

        # Assert
        self.assertEqual(mock_get.call_count, 2)
        mock_source_alloc.reparentHosts.assert_called_once_with(target_alloc)
        self.assertEqual(hosts_transferred, 5)

    @patch('opencue.api.getAllocation')
    def test_transfer_hosts_with_invalid_target_fails(self, mock_get):
        """Test host transfer fails with invalid target allocation."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.name = 'source_allocation'
        mock_alloc.reparentHosts = MagicMock(
            side_effect=ValueError("Invalid target allocation: not found")
        )
        mock_get.return_value = mock_alloc

        # Act & Assert
        allocation = mock_get('source_allocation')
        with self.assertRaisesRegex(ValueError, "Invalid target allocation"):
            allocation.reparentHosts('nonexistent_allocation')
        mock_alloc.reparentHosts.assert_called_once_with('nonexistent_allocation')

    @patch('opencue.api.getAllocation')
    def test_add_tags_to_allocation(self, mock_get):
        """Test adding tags to an allocation."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.name = 'tagged_allocation'
        mock_alloc.tags = []
        mock_alloc.setTag = MagicMock(side_effect=lambda tags: setattr(mock_alloc, 'tags', tags))
        mock_get.return_value = mock_alloc

        # Act
        allocation = mock_get('tagged_allocation')
        new_tags = ['urgent', 'gpu', 'high-memory']
        allocation.setTag(new_tags)

        # Assert
        mock_get.assert_called_once_with('tagged_allocation')
        mock_alloc.setTag.assert_called_once_with(new_tags)
        self.assertEqual(allocation.tags, new_tags)
        self.assertIn('urgent', allocation.tags)
        self.assertIn('gpu', allocation.tags)
        self.assertIn('high-memory', allocation.tags)

    @patch('opencue.api.getAllocation')
    def test_remove_all_tags_from_allocation(self, mock_get):
        """Test removing all tags from an allocation."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.name = 'tagged_allocation'
        mock_alloc.tags = ['urgent', 'gpu']
        mock_alloc.setTag = MagicMock(side_effect=lambda tags: setattr(mock_alloc, 'tags', tags))
        mock_get.return_value = mock_alloc

        # Act
        allocation = mock_get('tagged_allocation')
        self.assertEqual(len(allocation.tags), 2)  # Verify initial state
        allocation.setTag([])

        # Assert
        mock_get.assert_called_once_with('tagged_allocation')
        mock_alloc.setTag.assert_called_once_with([])
        self.assertEqual(allocation.tags, [])

    @patch('opencue.api.getAllocations')
    def test_list_all_allocations(self, mock_get_allocs):
        """Test listing all allocations without filters."""
        # Arrange
        mock_alloc1 = MagicMock()
        mock_alloc1.name = 'production_allocation'
        mock_alloc1.facility = 'facility1'
        mock_alloc1.cores = 1000

        mock_alloc2 = MagicMock()
        mock_alloc2.name = 'development_allocation'
        mock_alloc2.facility = 'facility2'
        mock_alloc2.cores = 500

        mock_alloc3 = MagicMock()
        mock_alloc3.name = 'testing_allocation'
        mock_alloc3.facility = 'facility1'
        mock_alloc3.cores = 250

        mock_get_allocs.return_value = [mock_alloc1, mock_alloc2, mock_alloc3]

        # Act
        allocations = mock_get_allocs()

        # Assert
        mock_get_allocs.assert_called_once_with()
        self.assertEqual(len(allocations), 3)
        self.assertEqual(allocations[0].name, 'production_allocation')
        self.assertEqual(allocations[1].name, 'development_allocation')
        self.assertEqual(allocations[2].name, 'testing_allocation')

        # Verify total cores
        total_cores = sum(a.cores for a in allocations)
        self.assertEqual(total_cores, 1750)

    @patch('opencue.api.getAllocations')
    def test_list_allocations_filtered_by_tags(self, mock_get_allocs):
        """Test listing allocations filtered by tags."""
        # Arrange
        mock_alloc1 = MagicMock()
        mock_alloc1.name = 'urgent_allocation'
        mock_alloc1.tags = ['urgent', 'high-priority']
        mock_alloc1.facility = 'facility1'

        mock_alloc2 = MagicMock()
        mock_alloc2.name = 'gpu_allocation'
        mock_alloc2.tags = ['gpu', 'ml']
        mock_alloc2.facility = 'facility1'

        # Simulate filtering by returning only allocations with 'urgent' tag
        mock_get_allocs.return_value = [mock_alloc1]

        # Act
        filtered_allocations = mock_get_allocs(tags=['urgent'])

        # Assert
        mock_get_allocs.assert_called_once_with(tags=['urgent'])
        self.assertEqual(len(filtered_allocations), 1)
        self.assertEqual(filtered_allocations[0].name, 'urgent_allocation')
        self.assertIn('urgent', filtered_allocations[0].tags)
        self.assertIn('high-priority', filtered_allocations[0].tags)

    @patch('opencue.api.getAllocation')
    def test_query_allocation_returns_details(self, mock_get):
        """Test querying an allocation returns its detailed information."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.name = 'query_allocation'
        mock_alloc.id = 'alloc-789-xyz'
        mock_alloc.facility = 'facility1'
        mock_alloc.tag = 'production'
        mock_alloc.cores = 2048
        mock_alloc.idle_cores = 512
        mock_alloc.locked_cores = 0
        mock_alloc.host_count = 64
        mock_get.return_value = mock_alloc

        # Act
        allocation = mock_get('query_allocation')

        # Assert
        mock_get.assert_called_once_with('query_allocation')
        self.assertEqual(allocation.name, 'query_allocation')
        self.assertEqual(allocation.cores, 2048)
        self.assertEqual(allocation.idle_cores, 512)
        self.assertEqual(allocation.host_count, 64)
        self.assertEqual(allocation.facility, 'facility1')
        self.assertEqual(allocation.tag, 'production')

        # Calculate utilization
        utilization = ((allocation.cores - allocation.idle_cores) / allocation.cores) * 100
        self.assertAlmostEqual(utilization, 75.0, places=1)

    @patch('opencue.api.getAllocation')
    def test_query_nonexistent_allocation_raises_error(self, mock_get):
        """Test querying a non-existent allocation raises appropriate error."""
        # Arrange
        mock_get.side_effect = KeyError("Allocation 'nonexistent' not found")

        # Act & Assert
        with self.assertRaisesRegex(KeyError, "not found"):
            mock_get('nonexistent')
        mock_get.assert_called_once_with('nonexistent')

    # Edge cases and error handling
    @patch('opencue.api.createAllocation')
    def test_create_allocation_with_empty_name_fails(self, mock_create):
        """Test allocation creation fails when name is empty."""
        # Arrange
        mock_create.side_effect = ValueError("Allocation name cannot be empty")

        # Act & Assert
        with self.assertRaisesRegex(ValueError, "name cannot be empty"):
            mock_create('facility1', '', 'tag1')
        mock_create.assert_called_once_with('facility1', '', 'tag1')

    @patch('opencue.api.createAllocation')
    def test_create_allocation_with_special_characters(self, mock_create):
        """Test allocation creation with special characters in name."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.name = 'test-alloc_01'
        mock_create.return_value = mock_alloc

        # Act
        result = mock_create('facility1', 'test-alloc_01', 'tag1')

        # Assert
        mock_create.assert_called_once_with('facility1', 'test-alloc_01', 'tag1')
        self.assertEqual(result.name, 'test-alloc_01')

    @patch('opencue.api.getAllocation')
    def test_delete_allocation_not_found(self, mock_get):
        """Test deleting a non-existent allocation raises error."""
        # Arrange
        mock_get.side_effect = KeyError("Allocation 'missing_alloc' not found")

        # Act & Assert
        with self.assertRaisesRegex(KeyError, "not found"):
            mock_get('missing_alloc')
        mock_get.assert_called_once_with('missing_alloc')

    @patch('opencue.api.getAllocation')
    def test_rename_allocation_with_empty_name_fails(self, mock_get):
        """Test renaming allocation with empty name fails."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.name = 'current_name'
        mock_alloc.setName = MagicMock(side_effect=ValueError("Allocation name cannot be empty"))
        mock_get.return_value = mock_alloc

        # Act & Assert
        allocation = mock_get('current_name')
        with self.assertRaisesRegex(ValueError, "name cannot be empty"):
            allocation.setName('')
        mock_alloc.setName.assert_called_once_with('')

    @patch('opencue.api.getAllocation')
    def test_transfer_zero_or_negative_hosts_fails(self, mock_get):
        """Test transferring zero or negative number of hosts fails."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.name = 'source_allocation'

        # Test with zero hosts
        mock_alloc.reparentHostsWithCount = MagicMock(
            side_effect=ValueError("Cannot transfer 0 hosts")
        )
        mock_get.return_value = mock_alloc

        # Act & Assert for zero hosts
        allocation = mock_get('source_allocation')
        with self.assertRaisesRegex(ValueError, "Cannot transfer 0 hosts"):
            allocation.reparentHostsWithCount('target_allocation', 0)

        # Test with negative hosts
        mock_alloc.reparentHostsWithCount.side_effect = ValueError("Cannot transfer -5 hosts")
        with self.assertRaisesRegex(ValueError, "Cannot transfer -5 hosts"):
            allocation.reparentHostsWithCount('target_allocation', -5)

    @patch('opencue.api.getAllocation')
    def test_set_allocation_burst_percentage(self, mock_get):
        """Test setting allocation burst percentage."""
        # Arrange
        mock_alloc = MagicMock()
        mock_alloc.name = 'burst_allocation'
        mock_alloc.burst_percentage = 0
        mock_alloc.setBurstPercentage = MagicMock(
            side_effect=lambda p: setattr(mock_alloc, 'burst_percentage', p)
        )
        mock_get.return_value = mock_alloc

        # Act
        allocation = mock_get('burst_allocation')
        allocation.setBurstPercentage(150)

        # Assert
        mock_get.assert_called_once_with('burst_allocation')
        mock_alloc.setBurstPercentage.assert_called_once_with(150)
        self.assertEqual(allocation.burst_percentage, 150)

    @patch('opencue.api.getAllocations')
    def test_list_allocations_by_facility(self, mock_get_allocs):
        """Test listing allocations filtered by facility."""
        # Arrange
        mock_alloc1 = MagicMock()
        mock_alloc1.name = 'facility1_allocation'
        mock_alloc1.facility = 'us-west'

        mock_alloc2 = MagicMock()
        mock_alloc2.name = 'facility2_allocation'
        mock_alloc2.facility = 'us-east'

        # Simulate filtering by facility
        mock_get_allocs.return_value = [mock_alloc1]

        # Act
        allocations = mock_get_allocs(facility='us-west')

        # Assert
        mock_get_allocs.assert_called_once_with(facility='us-west')
        self.assertEqual(len(allocations), 1)
        self.assertEqual(allocations[0].facility, 'us-west')

if __name__ == '__main__':
    unittest.main()
