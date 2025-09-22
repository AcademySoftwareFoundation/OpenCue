"""
Unit tests for allocation management commands in cueadmin.
"""
import unittest
from unittest.mock import patch, MagicMock

class TestAllocationCommands(unittest.TestCase):

    @patch('opencue.api.createAllocation')
    def test_create_allocation_success(self, mock_create):
        alloc = MagicMock()
        alloc.name = 'alloc1'
        alloc.id = '123'
        mock_create.return_value = alloc
        result = mock_create('fac1', 'alloc1', 'tag1')
        self.assertEqual(result.name, 'alloc1')
        self.assertEqual(result.id, '123')

    @patch('opencue.api.createAllocation')
    def test_create_allocation_invalid(self, mock_create):
        mock_create.side_effect = ValueError("Invalid parameters")
        with self.assertRaises(ValueError):
            mock_create('', '', '')

    @patch('opencue.api.deleteAllocation')
    def test_delete_allocation_success(self, mock_delete):
        mock_delete.return_value = True
        self.assertTrue(mock_delete('alloc1'))

    @patch('opencue.api.deleteAllocation')
    def test_delete_nonempty_allocation(self, mock_delete):
        mock_delete.side_effect = RuntimeError("Allocation not empty")
        with self.assertRaises(RuntimeError):
            mock_delete('alloc_nonempty')

    @patch('opencue.api.getAllocation')
    def test_rename_allocation_success(self, mock_get):
        alloc = MagicMock()
        alloc.setName.return_value = None
        alloc.name = 'alloc2'
        mock_get.return_value = alloc
        result = mock_get('alloc1')
        result.setName('alloc2')
        self.assertEqual(result.name, 'alloc2')

    @patch('opencue.api.getAllocation')
    def test_rename_allocation_to_existing(self, mock_get):
        alloc = MagicMock()
        alloc.setName.side_effect = ValueError("Name already exists")
        mock_get.return_value = alloc
        with self.assertRaises(ValueError):
            alloc.setName('alloc_existing')

    @patch('opencue.api.getAllocation')
    def test_transfer_allocation_success(self, mock_get):
        alloc = MagicMock()
        alloc.reparentHosts.return_value = True
        mock_get.return_value = alloc
        self.assertTrue(alloc.reparentHosts('alloc2'))

    @patch('opencue.api.getAllocation')
    def test_transfer_allocation_invalid(self, mock_get):
        alloc = MagicMock()
        alloc.reparentHosts.side_effect = ValueError("Invalid transfer")
        mock_get.return_value = alloc
        with self.assertRaises(ValueError):
            alloc.reparentHosts('alloc2')

    @patch('opencue.api.getAllocation')
    def test_tag_allocation_add(self, mock_get):
        alloc = MagicMock()
        alloc.setTag.return_value = None
        alloc.tags = ['urgent', 'gpu']
        mock_get.return_value = alloc
        alloc.setTag(['urgent', 'gpu'])
        self.assertIn('urgent', alloc.tags)
        self.assertIn('gpu', alloc.tags)

    @patch('opencue.api.getAllocation')
    def test_tag_allocation_remove(self, mock_get):
        alloc = MagicMock()
        alloc.setTag.return_value = None
        alloc.tags = []
        mock_get.return_value = alloc
        alloc.setTag([])
        self.assertEqual(alloc.tags, [])

    @patch('opencue.api.getAllocations')
    def test_list_allocations(self, mock_get_allocs):
        alloc1 = MagicMock()
        alloc1.name = 'alloc1'
        alloc2 = MagicMock()
        alloc2.name = 'alloc2'
        mock_get_allocs.return_value = [alloc1, alloc2]
        result = mock_get_allocs()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, 'alloc1')

    @patch('opencue.api.getAllocations')
    def test_list_allocations_with_filter(self, mock_get_allocs):
        alloc1 = MagicMock(name='alloc1', tags=['urgent'])
        mock_get_allocs.return_value = [alloc1]
        result = mock_get_allocs(tags=['urgent'])
        self.assertEqual(result[0].tags, ['urgent'])

    @patch('opencue.api.getAllocation')
    def test_query_allocation_success(self, mock_get):
        alloc = MagicMock()
        alloc.name = 'alloc1'
        alloc.cores = 16
        mock_get.return_value = alloc
        result = mock_get('alloc1')
        self.assertEqual(result.name, 'alloc1')
        self.assertEqual(result.cores, 16)

    @patch('opencue.api.getAllocation')
    def test_query_allocation_not_found(self, mock_get):
        mock_get.side_effect = KeyError("Not found")
        with self.assertRaises(KeyError):
            mock_get('alloc_missing')

    # Edge cases
    @patch('opencue.api.createAllocation')
    def test_create_allocation_empty_name(self, mock_create):
        mock_create.side_effect = ValueError("Name required")
        with self.assertRaises(ValueError):
            mock_create('', '', '')

    @patch('opencue.api.deleteAllocation')
    def test_delete_allocation_not_found(self, mock_delete):
        mock_delete.side_effect = KeyError("Not found")
        with self.assertRaises(KeyError):
            mock_delete('alloc_missing')

    @patch('opencue.api.getAllocation')
    def test_rename_allocation_empty_name(self, mock_get):
        alloc = MagicMock()
        alloc.setName.side_effect = ValueError("Name required")
        mock_get.return_value = alloc
        with self.assertRaises(ValueError):
            alloc.setName('')

    @patch('opencue.api.getAllocation')
    def test_transfer_allocation_zero_negative(self, mock_get):
        alloc = MagicMock()
        alloc.reparentHosts.side_effect = ValueError("Invalid transfer")
        mock_get.return_value = alloc
        with self.assertRaises(ValueError):
            alloc.reparentHosts('alloc2')

if __name__ == '__main__':
    unittest.main()
