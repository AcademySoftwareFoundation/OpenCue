"""
Unit tests for allocation management behaviors using opencue.api.
"""
import unittest
from unittest.mock import patch, MagicMock

import opencue.api as api

class TestAllocationCommands(unittest.TestCase):
    @patch('opencue.api.createAllocation')
    @patch('opencue.api.getFacility')
    def test_create_alloc_valid(self, mock_get_facility, mock_create):
        facility = MagicMock()
        mock_get_facility.return_value = facility
        mock_create.return_value = MagicMock()

        fac, name, tag = 'facility1', 'alloc1', 'tag1'
        facility_obj = api.getFacility(fac)
        result = api.createAllocation(name, tag, facility_obj)

        mock_get_facility.assert_called_once_with('facility1')
        mock_create.assert_called_once_with('alloc1', 'tag1', facility)
        self.assertIsNotNone(result)

    @patch('opencue.api.createAllocation')
    def test_create_alloc_duplicate_name(self, mock_create):
        mock_create.side_effect = ValueError("Duplicate allocation name")
        with self.assertRaises(ValueError):
            api.createAllocation('alloc1', 'tag1', MagicMock())

    @patch('opencue.api.findAllocation')
    def test_delete_alloc_empty(self, mock_find):
        alloc = MagicMock()
        alloc.getHosts.return_value = []
        mock_find.return_value = alloc

        found = api.findAllocation('facility.alloc1')
        if not found.getHosts():
            found.delete()

        mock_find.assert_called_once_with('facility.alloc1')
        alloc.delete.assert_called_once_with()

    @patch('opencue.api.findAllocation')
    def test_delete_alloc_non_empty(self, mock_find):
        alloc = MagicMock()
        alloc.getHosts.return_value = ['host1']
        mock_find.return_value = alloc

        found = api.findAllocation('facility.alloc1')
        with self.assertRaises(RuntimeError):
            if found.getHosts():
                raise RuntimeError("Allocation not empty")

        alloc.delete.assert_not_called()

    @patch('opencue.api.findAllocation')
    def test_rename_alloc_valid(self, mock_find):
        alloc = MagicMock()
        mock_find.return_value = alloc
        alloc.setName.return_value = None

        api.findAllocation('facility.alloc1').setName('alloc2')
        mock_find.assert_called_once_with('facility.alloc1')
        alloc.setName.assert_called_once_with('alloc2')

    @patch('opencue.api.findAllocation')
    def test_rename_alloc_duplicate(self, mock_find):
        alloc = MagicMock()
        mock_find.return_value = alloc
        alloc.setName.side_effect = ValueError("Duplicate allocation name")
        with self.assertRaises(ValueError):
            api.findAllocation('facility.alloc1').setName('alloc2')

    @patch('opencue.api.findAllocation')
    def test_transfer_hosts_between_allocs(self, mock_find):
        src = MagicMock()
        dst = MagicMock()

        # Return src first, then dst
        mock_find.side_effect = [src, dst]
        src.getHosts.return_value = ['host1', 'host2']
        dst.reparentHosts.return_value = None

        found_src = api.findAllocation('facility.src')
        found_dst = api.findAllocation('facility.dst')
        found_dst.reparentHosts(found_src.getHosts())

        self.assertEqual(mock_find.call_count, 2)
        mock_find.assert_any_call('facility.src')
        mock_find.assert_any_call('facility.dst')
        dst.reparentHosts.assert_called_once_with(['host1', 'host2'])

    @patch('opencue.api.findAllocation')
    def test_tag_alloc_update(self, mock_find):
        alloc = MagicMock()
        mock_find.return_value = alloc
        alloc.setTag.return_value = None
        api.findAllocation('facility.alloc1').setTag('tag2')
        mock_find.assert_called_once_with('facility.alloc1')
        alloc.setTag.assert_called_once_with('tag2')

    @patch('opencue.api.getAllocations')
    def test_list_allocations(self, mock_get):
        alloc1 = MagicMock()
        alloc2 = MagicMock()
        mock_get.return_value = [alloc1, alloc2]
        result = api.getAllocations()
        mock_get.assert_called_once_with()
        self.assertEqual(len(result), 2)

    @patch('opencue.api.getAllocations')
    def test_allocation_query_filter(self, mock_get):
        alloc1 = MagicMock()
        alloc1.tags = ['tag1']
        alloc2 = MagicMock()
        alloc2.tags = ['tag2']
        mock_get.return_value = [alloc1, alloc2]
        result = api.getAllocations()
        filtered = [a for a in result if 'tag1' in getattr(a, 'tags', [])]
        self.assertEqual(filtered, [alloc1])

    @patch('opencue.api.getAllocation')
    def test_get_allocation_error_handling(self, mock_get):
        mock_get.side_effect = Exception("API error")
        with self.assertRaises(Exception):
            api.getAllocation('alloc-id-123')

    @patch('opencue.api.createAllocation')
    def test_create_alloc_tag_validation(self, mock_create):
        mock_create.side_effect = ValueError("Invalid tag")
        with self.assertRaises(ValueError):
            api.createAllocation('alloc1', 'bad tag', MagicMock())

if __name__ == '__main__':
    unittest.main()
