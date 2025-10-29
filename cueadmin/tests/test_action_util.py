#!/usr/bin/env python

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


"""Unit tests for cueadmin.common.ActionUtil class."""


from __future__ import absolute_import, division, print_function

import unittest

import mock
from opencue_proto import filter_pb2

import cueadmin.common


class ActionUtilFactoryTests(unittest.TestCase):
    """Test cases for ActionUtil.factory() method.

    This class tests the creation of Action objects with various types
    including PAUSE_JOB, MOVE_JOB_TO_GROUP, SET_JOB_PRIORITY, and others.
    """

    # pylint: disable=no-member
    def test_factory_pause_job(self):
        """Test creating a PAUSE_JOB action with boolean value."""
        action = cueadmin.common.ActionUtil.factory("PAUSE_JOB", True)

        self.assertEqual(action.type, filter_pb2.PAUSE_JOB)
        self.assertEqual(action.value_type, filter_pb2.BOOLEAN_TYPE)
        self.assertTrue(action.boolean_value)

    def test_factory_pause_job_false(self):
        """Test creating a PAUSE_JOB action with False value (unpause)."""
        action = cueadmin.common.ActionUtil.factory("PAUSE_JOB", False)

        self.assertEqual(action.type, filter_pb2.PAUSE_JOB)
        self.assertEqual(action.value_type, filter_pb2.BOOLEAN_TYPE)
        self.assertFalse(action.boolean_value)

    @mock.patch('opencue.proxy')
    def test_factory_move_job_to_group(self, proxy_mock):
        """Test creating a MOVE_JOB_TO_GROUP action with group value."""
        mock_group = mock.Mock()
        mock_group_id = "group123"
        proxy_mock.return_value = mock_group_id

        action = cueadmin.common.ActionUtil.factory("MOVE_JOB_TO_GROUP", mock_group)

        self.assertEqual(action.type, filter_pb2.MOVE_JOB_TO_GROUP)
        self.assertEqual(action.value_type, filter_pb2.GROUP_TYPE)
        self.assertEqual(action.group_value, mock_group_id)
        proxy_mock.assert_called_with(mock_group, "Group")

    def test_factory_set_job_priority(self):
        """Test creating a SET_JOB_PRIORITY action with integer value."""
        priority = 200
        action = cueadmin.common.ActionUtil.factory("SET_JOB_PRIORITY", priority)

        self.assertEqual(action.type, filter_pb2.SET_JOB_PRIORITY)
        self.assertEqual(action.value_type, filter_pb2.INTEGER_TYPE)
        self.assertEqual(action.integer_value, priority)

    def test_factory_set_all_render_layer_memory(self):
        """Test creating a SET_ALL_RENDER_LAYER_MEMORY action with integer value."""
        memory = 4096
        action = cueadmin.common.ActionUtil.factory("SET_ALL_RENDER_LAYER_MEMORY", memory)

        self.assertEqual(action.type, filter_pb2.SET_ALL_RENDER_LAYER_MEMORY)
        self.assertEqual(action.value_type, filter_pb2.INTEGER_TYPE)
        self.assertEqual(action.integer_value, memory)

    def test_factory_set_job_min_cores(self):
        """Test creating a SET_JOB_MIN_CORES action with float value."""
        min_cores = 2.5
        action = cueadmin.common.ActionUtil.factory("SET_JOB_MIN_CORES", min_cores)

        self.assertEqual(action.type, filter_pb2.SET_JOB_MIN_CORES)
        self.assertEqual(action.value_type, filter_pb2.FLOAT_TYPE)
        self.assertEqual(action.float_value, min_cores)

    def test_factory_set_job_max_cores(self):
        """Test creating a SET_JOB_MAX_CORES action with float value."""
        max_cores = 10.0
        action = cueadmin.common.ActionUtil.factory("SET_JOB_MAX_CORES", max_cores)

        self.assertEqual(action.type, filter_pb2.SET_JOB_MAX_CORES)
        self.assertEqual(action.value_type, filter_pb2.FLOAT_TYPE)
        self.assertEqual(action.float_value, max_cores)

    def test_factory_set_all_render_layer_cores(self):
        """Test creating a SET_ALL_RENDER_LAYER_CORES action with float value."""
        cores = 4.0
        action = cueadmin.common.ActionUtil.factory("SET_ALL_RENDER_LAYER_CORES", cores)

        self.assertEqual(action.type, filter_pb2.SET_ALL_RENDER_LAYER_CORES)
        self.assertEqual(action.value_type, filter_pb2.FLOAT_TYPE)
        self.assertEqual(action.float_value, cores)

    def test_factory_set_all_render_layer_tags(self):
        """Test creating a SET_ALL_RENDER_LAYER_TAGS action with string value."""
        tags = "urgent,high_priority"
        action = cueadmin.common.ActionUtil.factory("SET_ALL_RENDER_LAYER_TAGS", tags)

        self.assertEqual(action.type, filter_pb2.SET_ALL_RENDER_LAYER_TAGS)
        self.assertEqual(action.value_type, filter_pb2.STRING_TYPE)
        self.assertEqual(action.string_value, tags)

    def test_factory_stop_processing(self):
        """Test creating a STOP_PROCESSING action with no value."""
        action = cueadmin.common.ActionUtil.factory("STOP_PROCESSING", None)

        self.assertEqual(action.type, filter_pb2.STOP_PROCESSING)
        self.assertEqual(action.value_type, filter_pb2.NONE_TYPE)

    def test_factory_invalid_action_type(self):
        """Test that factory raises ValueError for invalid action type."""
        with self.assertRaises(ValueError) as context:
            cueadmin.common.ActionUtil.factory("INVALID_ACTION", "value")

        self.assertIn("invalid action type", str(context.exception).lower())

    def test_factory_with_numeric_string_for_integer(self):
        """Test creating an action with numeric string that gets converted to int."""
        action = cueadmin.common.ActionUtil.factory("SET_JOB_PRIORITY", "150")

        self.assertEqual(action.type, filter_pb2.SET_JOB_PRIORITY)
        self.assertEqual(action.integer_value, 150)

    def test_factory_with_numeric_string_for_float(self):
        """Test creating an action with numeric string that gets converted to float."""
        action = cueadmin.common.ActionUtil.factory("SET_JOB_MIN_CORES", "3.5")

        self.assertEqual(action.type, filter_pb2.SET_JOB_MIN_CORES)
        self.assertAlmostEqual(action.float_value, 3.5)


class ActionUtilGetValueTests(unittest.TestCase):
    """Test cases for ActionUtil.getValue() method.

    This class tests extracting values from Action objects based on their
    value types (GROUP_TYPE, STRING_TYPE, INTEGER_TYPE, FLOAT_TYPE, BOOLEAN_TYPE).
    """

    def test_get_value_boolean(self):
        """Test getting a boolean value from an action."""
        action = mock.Mock()
        action.data.value_type = "BooleanType"
        action.data.boolean_value = True

        value = cueadmin.common.ActionUtil.getValue(action)

        self.assertTrue(value)

    def test_get_value_integer(self):
        """Test getting an integer value from an action."""
        action = mock.Mock()
        action.data.value_type = "IntegerType"
        action.data.integer_value = 100

        value = cueadmin.common.ActionUtil.getValue(action)

        self.assertEqual(value, 100)

    def test_get_value_float(self):
        """Test getting a float value from an action."""
        action = mock.Mock()
        action.data.value_type = "FloatType"
        action.data.float_value = 2.5

        value = cueadmin.common.ActionUtil.getValue(action)

        self.assertEqual(value, 2.5)

    def test_get_value_string(self):
        """Test getting a string value from an action."""
        action = mock.Mock()
        action.data.value_type = "StringType"
        action.data.string_value = "test_string"

        value = cueadmin.common.ActionUtil.getValue(action)

        self.assertEqual(value, "test_string")

    def test_get_value_group(self):
        """Test getting a group value from an action."""
        action = mock.Mock()
        action.data.value_type = "GroupType"
        mock_group = mock.Mock()
        action.data.group_value = mock_group

        value = cueadmin.common.ActionUtil.getValue(action)

        self.assertEqual(value, mock_group)

    def test_get_value_none_type(self):
        """Test getting value from an action with no value (NONE_TYPE)."""
        action = mock.Mock()
        action.data.value_type = "NoneType"

        value = cueadmin.common.ActionUtil.getValue(action)

        self.assertIsNone(value)

    def test_get_value_unknown_type(self):
        """Test getting value from an action with unknown value type."""
        action = mock.Mock()
        action.data.value_type = "UnknownType"

        value = cueadmin.common.ActionUtil.getValue(action)

        self.assertIsNone(value)


class ActionUtilSetValueTests(unittest.TestCase):
    """Test cases for ActionUtil.setValue() method.

    This class tests setting values on Action objects for various action types
    including pause, priority, cores, memory, tags, and group assignments.
    """

    # pylint: disable=no-member
    @mock.patch('opencue.proxy')
    def test_set_value_move_job_to_group(self, proxy_mock):
        """Test setting a group value on MOVE_JOB_TO_GROUP action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.MOVE_JOB_TO_GROUP
        mock_group = mock.Mock()
        mock_group_id = "group123"
        proxy_mock.return_value = mock_group_id

        cueadmin.common.ActionUtil.setValue(action, mock_group)

        self.assertEqual(action.value_type, filter_pb2.GROUP_TYPE)
        self.assertEqual(action.group_value, mock_group_id)
        proxy_mock.assert_called_with(mock_group, "Group")

    def test_set_value_pause_job_true(self):
        """Test setting boolean value True on PAUSE_JOB action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.PAUSE_JOB

        cueadmin.common.ActionUtil.setValue(action, True)

        self.assertEqual(action.value_type, filter_pb2.BOOLEAN_TYPE)
        self.assertTrue(action.boolean_value)

    def test_set_value_pause_job_false(self):
        """Test setting boolean value False on PAUSE_JOB action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.PAUSE_JOB

        cueadmin.common.ActionUtil.setValue(action, False)

        self.assertEqual(action.value_type, filter_pb2.BOOLEAN_TYPE)
        self.assertFalse(action.boolean_value)

    def test_set_value_job_priority(self):
        """Test setting integer value on SET_JOB_PRIORITY action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.SET_JOB_PRIORITY
        priority = 250

        cueadmin.common.ActionUtil.setValue(action, priority)

        self.assertEqual(action.value_type, filter_pb2.INTEGER_TYPE)
        self.assertEqual(action.integer_value, priority)

    def test_set_value_render_layer_memory(self):
        """Test setting integer value on SET_ALL_RENDER_LAYER_MEMORY action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.SET_ALL_RENDER_LAYER_MEMORY
        memory = 8192

        cueadmin.common.ActionUtil.setValue(action, memory)

        self.assertEqual(action.value_type, filter_pb2.INTEGER_TYPE)
        self.assertEqual(action.integer_value, memory)

    def test_set_value_job_min_cores(self):
        """Test setting float value on SET_JOB_MIN_CORES action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.SET_JOB_MIN_CORES
        min_cores = 1.5

        cueadmin.common.ActionUtil.setValue(action, min_cores)

        self.assertEqual(action.value_type, filter_pb2.FLOAT_TYPE)
        self.assertEqual(action.float_value, min_cores)

    def test_set_value_job_max_cores(self):
        """Test setting float value on SET_JOB_MAX_CORES action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.SET_JOB_MAX_CORES
        max_cores = 20.0

        cueadmin.common.ActionUtil.setValue(action, max_cores)

        self.assertEqual(action.value_type, filter_pb2.FLOAT_TYPE)
        self.assertEqual(action.float_value, max_cores)

    def test_set_value_render_layer_cores(self):
        """Test setting float value on SET_ALL_RENDER_LAYER_CORES action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.SET_ALL_RENDER_LAYER_CORES
        cores = 8.0

        cueadmin.common.ActionUtil.setValue(action, cores)

        self.assertEqual(action.value_type, filter_pb2.FLOAT_TYPE)
        self.assertEqual(action.float_value, cores)

    def test_set_value_render_layer_tags(self):
        """Test setting string value on SET_ALL_RENDER_LAYER_TAGS action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.SET_ALL_RENDER_LAYER_TAGS
        tags = "priority,urgent"

        cueadmin.common.ActionUtil.setValue(action, tags)

        self.assertEqual(action.value_type, filter_pb2.STRING_TYPE)
        self.assertEqual(action.string_value, tags)

    def test_set_value_stop_processing(self):
        """Test setting value on STOP_PROCESSING action (NONE_TYPE)."""
        action = filter_pb2.Action()
        action.type = filter_pb2.STOP_PROCESSING

        cueadmin.common.ActionUtil.setValue(action, None)

        self.assertEqual(action.value_type, filter_pb2.NONE_TYPE)

    def test_set_value_invalid_action_type(self):
        """Test that setValue raises TypeError for invalid action type."""
        action = filter_pb2.Action()
        action.type = 9999  # Invalid action type

        with self.assertRaises(TypeError) as context:
            cueadmin.common.ActionUtil.setValue(action, "value")

        self.assertIn("invalid action type", str(context.exception).lower())

    def test_set_value_integer_from_string(self):
        """Test setting integer value from string on SET_JOB_PRIORITY action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.SET_JOB_PRIORITY

        cueadmin.common.ActionUtil.setValue(action, "300")

        self.assertEqual(action.value_type, filter_pb2.INTEGER_TYPE)
        self.assertEqual(action.integer_value, 300)

    def test_set_value_float_from_string(self):
        """Test setting float value from string on SET_JOB_MIN_CORES action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.SET_JOB_MIN_CORES

        cueadmin.common.ActionUtil.setValue(action, "2.75")

        self.assertEqual(action.value_type, filter_pb2.FLOAT_TYPE)
        self.assertAlmostEqual(action.float_value, 2.75)

    def test_set_value_float_from_integer(self):
        """Test setting float value from integer on SET_JOB_MIN_CORES action."""
        action = filter_pb2.Action()
        action.type = filter_pb2.SET_JOB_MIN_CORES

        cueadmin.common.ActionUtil.setValue(action, 4)

        self.assertEqual(action.value_type, filter_pb2.FLOAT_TYPE)
        self.assertEqual(action.float_value, 4.0)


class ActionUtilIntegrationTests(unittest.TestCase):
    """Integration tests for ActionUtil methods working together.

    These tests verify that Actions created with factory() can be properly
    read with getValue() and modified with setValue().
    """

    # pylint: disable=no-member
    def test_factory_and_get_value_pause_job(self):
        """Test creating a PAUSE_JOB action and retrieving its value."""
        action = cueadmin.common.ActionUtil.factory("PAUSE_JOB", True)

        # Simulate getting value by creating mock data structure
        mock_action = mock.Mock()
        mock_action.data.value_type = "BooleanType"
        mock_action.data.boolean_value = action.boolean_value

        value = cueadmin.common.ActionUtil.getValue(mock_action)

        self.assertTrue(value)

    def test_factory_and_get_value_priority(self):
        """Test creating a SET_JOB_PRIORITY action and retrieving its value."""
        priority = 175
        action = cueadmin.common.ActionUtil.factory("SET_JOB_PRIORITY", priority)

        # Simulate getting value
        mock_action = mock.Mock()
        mock_action.data.value_type = "IntegerType"
        mock_action.data.integer_value = action.integer_value

        value = cueadmin.common.ActionUtil.getValue(mock_action)

        self.assertEqual(value, priority)

    def test_factory_and_get_value_cores(self):
        """Test creating a SET_JOB_MIN_CORES action and retrieving its value."""
        min_cores = 3.5
        action = cueadmin.common.ActionUtil.factory("SET_JOB_MIN_CORES", min_cores)

        # Simulate getting value
        mock_action = mock.Mock()
        mock_action.data.value_type = "FloatType"
        mock_action.data.float_value = action.float_value

        value = cueadmin.common.ActionUtil.getValue(mock_action)

        self.assertEqual(value, min_cores)

    def test_set_value_multiple_times(self):
        """Test setting different values on the same action multiple times."""
        action = filter_pb2.Action()
        action.type = filter_pb2.SET_JOB_PRIORITY

        # Set initial value
        cueadmin.common.ActionUtil.setValue(action, 100)
        self.assertEqual(action.integer_value, 100)

        # Update value
        cueadmin.common.ActionUtil.setValue(action, 200)
        self.assertEqual(action.integer_value, 200)

        # Update again
        cueadmin.common.ActionUtil.setValue(action, 50)
        self.assertEqual(action.integer_value, 50)

    def test_factory_with_boundary_values_integer(self):
        """Test creating actions with boundary integer values."""
        # Test with 0
        action_zero = cueadmin.common.ActionUtil.factory("SET_JOB_PRIORITY", 0)
        self.assertEqual(action_zero.integer_value, 0)

        # Test with negative value
        action_negative = cueadmin.common.ActionUtil.factory("SET_JOB_PRIORITY", -100)
        self.assertEqual(action_negative.integer_value, -100)

        # Test with large value
        action_large = cueadmin.common.ActionUtil.factory("SET_JOB_PRIORITY", 999999)
        self.assertEqual(action_large.integer_value, 999999)

    def test_factory_with_boundary_values_float(self):
        """Test creating actions with boundary float values."""
        # Test with 0.0
        action_zero = cueadmin.common.ActionUtil.factory("SET_JOB_MIN_CORES", 0.0)
        self.assertEqual(action_zero.float_value, 0.0)

        # Test with very small value
        action_small = cueadmin.common.ActionUtil.factory("SET_JOB_MIN_CORES", 0.1)
        self.assertAlmostEqual(action_small.float_value, 0.1)

        # Test with large value
        action_large = cueadmin.common.ActionUtil.factory("SET_JOB_MIN_CORES", 1000.5)
        self.assertAlmostEqual(action_large.float_value, 1000.5)

    def test_factory_with_empty_string(self):
        """Test creating a SET_ALL_RENDER_LAYER_TAGS action with empty string."""
        action = cueadmin.common.ActionUtil.factory("SET_ALL_RENDER_LAYER_TAGS", "")

        self.assertEqual(action.type, filter_pb2.SET_ALL_RENDER_LAYER_TAGS)
        self.assertEqual(action.string_value, "")

    def test_multiple_action_types_in_sequence(self):
        """Test creating multiple different action types in sequence."""
        # Create various actions
        pause_action = cueadmin.common.ActionUtil.factory("PAUSE_JOB", True)
        priority_action = cueadmin.common.ActionUtil.factory("SET_JOB_PRIORITY", 150)
        cores_action = cueadmin.common.ActionUtil.factory("SET_JOB_MIN_CORES", 2.0)
        tags_action = cueadmin.common.ActionUtil.factory(
            "SET_ALL_RENDER_LAYER_TAGS", "test"
        )

        # Verify each action has correct type and value
        self.assertEqual(pause_action.type, filter_pb2.PAUSE_JOB)
        self.assertTrue(pause_action.boolean_value)

        self.assertEqual(priority_action.type, filter_pb2.SET_JOB_PRIORITY)
        self.assertEqual(priority_action.integer_value, 150)

        self.assertEqual(cores_action.type, filter_pb2.SET_JOB_MIN_CORES)
        self.assertEqual(cores_action.float_value, 2.0)

        self.assertEqual(tags_action.type, filter_pb2.SET_ALL_RENDER_LAYER_TAGS)
        self.assertEqual(tags_action.string_value, "test")


if __name__ == "__main__":
    unittest.main()
