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


"""Tests for cuegui.Exception."""


import unittest

import cuegui.Exception


class CueGuiExceptionTests(unittest.TestCase):

    def test_instantiation(self):
        """Test basic instantiation of CueGuiException."""
        exception = cuegui.Exception.CueGuiException()
        self.assertIsInstance(exception, cuegui.Exception.CueGuiException)
        self.assertIsInstance(exception, Exception)

    def test_with_message(self):
        """Test instantiation with a custom message."""
        message = "Custom error message"
        exception = cuegui.Exception.CueGuiException(message)
        self.assertEqual(str(exception), message)

    def test_without_message(self):
        """Test instantiation without a message."""
        exception = cuegui.Exception.CueGuiException()
        # Base Exception class behavior - no message by default
        self.assertEqual(str(exception), "")

    def test_multiple_args(self):
        """Test instantiation with multiple arguments."""
        arg1 = "First argument"
        arg2 = "Second argument"
        exception = cuegui.Exception.CueGuiException(arg1, arg2)
        self.assertEqual(exception.args, (arg1, arg2))

    def test_inheritance_hierarchy(self):
        """Test that CueGuiException properly inherits from Exception."""
        exception = cuegui.Exception.CueGuiException()
        self.assertTrue(issubclass(cuegui.Exception.CueGuiException, Exception))
        self.assertIsInstance(exception, Exception)

    def test_raise_and_catch(self):
        """Test raising and catching CueGuiException."""
        message = "Test exception"
        with self.assertRaises(cuegui.Exception.CueGuiException) as context:
            raise cuegui.Exception.CueGuiException(message)
        self.assertEqual(str(context.exception), message)

    def test_catch_as_base_exception(self):
        """Test that CueGuiException can be caught as base Exception."""
        message = "Test exception"
        with self.assertRaises(Exception) as context:
            raise cuegui.Exception.CueGuiException(message)
        self.assertIsInstance(context.exception, cuegui.Exception.CueGuiException)
        self.assertEqual(str(context.exception), message)


class ApplicationNotRunningExceptionTests(unittest.TestCase):

    def test_instantiation(self):
        """Test basic instantiation of ApplicationNotRunningException."""
        exception = cuegui.Exception.ApplicationNotRunningException()
        self.assertIsInstance(exception, cuegui.Exception.ApplicationNotRunningException)
        self.assertIsInstance(exception, cuegui.Exception.CueGuiException)
        self.assertIsInstance(exception, Exception)

    def test_default_message(self):
        """Test that the default message is used when no message is provided."""
        exception = cuegui.Exception.ApplicationNotRunningException()
        expected_message = (
            'attempted to access the CueGUI application before cuegui.create_app() was called')
        self.assertEqual(str(exception), expected_message)

    def test_default_message_attribute(self):
        """Test the default_message class attribute."""
        expected_message = (
            'attempted to access the CueGUI application before cuegui.create_app() was called')
        self.assertEqual(
            cuegui.Exception.ApplicationNotRunningException.default_message,
            expected_message)

    def test_with_custom_message(self):
        """Test instantiation with a custom message."""
        custom_message = "Custom application not running message"
        exception = cuegui.Exception.ApplicationNotRunningException(custom_message)
        self.assertEqual(str(exception), custom_message)

    def test_with_none_message(self):
        """Test instantiation with None as message (should use default)."""
        exception = cuegui.Exception.ApplicationNotRunningException(None)
        expected_message = (
            'attempted to access the CueGUI application before cuegui.create_app() was called')
        self.assertEqual(str(exception), expected_message)

    def test_with_empty_string_message(self):
        """Test instantiation with empty string as message."""
        exception = cuegui.Exception.ApplicationNotRunningException("")
        self.assertEqual(str(exception), "")

    def test_inheritance_hierarchy(self):
        """Test that ApplicationNotRunningException properly inherits."""
        exception = cuegui.Exception.ApplicationNotRunningException()
        self.assertTrue(issubclass(
            cuegui.Exception.ApplicationNotRunningException,
            cuegui.Exception.CueGuiException))
        self.assertTrue(issubclass(
            cuegui.Exception.ApplicationNotRunningException,
            Exception))
        self.assertIsInstance(exception, cuegui.Exception.CueGuiException)
        self.assertIsInstance(exception, Exception)

    def test_raise_and_catch_specific(self):
        """Test raising and catching ApplicationNotRunningException specifically."""
        custom_message = "App not running test"
        with self.assertRaises(cuegui.Exception.ApplicationNotRunningException) as context:
            raise cuegui.Exception.ApplicationNotRunningException(custom_message)
        self.assertEqual(str(context.exception), custom_message)

    def test_catch_as_cuegui_exception(self):
        """Test that ApplicationNotRunningException can be caught as CueGuiException."""
        with self.assertRaises(cuegui.Exception.CueGuiException) as context:
            raise cuegui.Exception.ApplicationNotRunningException()
        self.assertIsInstance(context.exception, cuegui.Exception.ApplicationNotRunningException)

    def test_catch_as_base_exception(self):
        """Test that ApplicationNotRunningException can be caught as base Exception."""
        with self.assertRaises(Exception) as context:
            raise cuegui.Exception.ApplicationNotRunningException()
        self.assertIsInstance(context.exception, cuegui.Exception.ApplicationNotRunningException)

    def test_multiple_instantiations(self):
        """Test multiple instantiations with different messages."""
        # Default message
        exc1 = cuegui.Exception.ApplicationNotRunningException()
        expected_default = (
            'attempted to access the CueGUI application before cuegui.create_app() was called')
        self.assertEqual(str(exc1), expected_default)

        # Custom message
        custom_msg = "Custom error"
        exc2 = cuegui.Exception.ApplicationNotRunningException(custom_msg)
        self.assertEqual(str(exc2), custom_msg)

        # None message (should use default)
        exc3 = cuegui.Exception.ApplicationNotRunningException(None)
        self.assertEqual(str(exc3), expected_default)

    def test_exception_properties(self):
        """Test exception properties and attributes."""
        exception = cuegui.Exception.ApplicationNotRunningException()

        # Test that it has the expected attributes
        self.assertTrue(hasattr(exception, 'default_message'))
        self.assertTrue(hasattr(exception, 'args'))

        # Test args tuple
        expected_message = (
            'attempted to access the CueGUI application before cuegui.create_app() was called')
        self.assertEqual(exception.args, (expected_message,))


if __name__ == '__main__':
    unittest.main()
