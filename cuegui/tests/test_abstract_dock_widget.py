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


"""Tests for cuegui.AbstractDockWidget."""


import unittest

import mock
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import QtGui

import cuegui.AbstractDockWidget

from . import test_utils


class AbstractDockWidgetTests(unittest.TestCase):
    def setUp(self):
        self.app = test_utils.createApplication()
        self.main_window = QtWidgets.QMainWindow()
        self.widget_name = "TestDockWidget"
        self.dock_widget = cuegui.AbstractDockWidget.AbstractDockWidget(
            self.main_window, self.widget_name)

    def tearDown(self):
        self.dock_widget.deleteLater()
        self.main_window.deleteLater()

    def test_init(self):
        # Test inheritance
        self.assertIsInstance(self.dock_widget, QtWidgets.QDockWidget)
        self.assertIsInstance(self.dock_widget, cuegui.Plugins.Plugin)

        # Test widget properties
        self.assertEqual(self.dock_widget.windowTitle(), self.widget_name)
        self.assertEqual(self.dock_widget.objectName(), self.widget_name)
        self.assertEqual(self.dock_widget.parent, self.main_window)

    def test_init_with_custom_area(self):
        # Test with right dock area
        dock_right = cuegui.AbstractDockWidget.AbstractDockWidget(
            self.main_window, "RightDock", QtCore.Qt.RightDockWidgetArea)

        # Check that it was added to the main window
        self.assertIn(dock_right, self.main_window.findChildren(QtWidgets.QDockWidget))

        dock_right.deleteLater()

    def test_allowed_areas(self):
        # Check that all dock areas are allowed
        allowed_areas = self.dock_widget.allowedAreas()
        self.assertEqual(allowed_areas, QtCore.Qt.AllDockWidgetAreas)

    def test_features(self):
        # Check that the widget is closable and movable
        features = self.dock_widget.features()
        self.assertTrue(features & QtWidgets.QDockWidget.DockWidgetClosable)
        self.assertTrue(features & QtWidgets.QDockWidget.DockWidgetMovable)
        self.assertFalse(features & QtWidgets.QDockWidget.DockWidgetFloatable)

    def test_layout(self):
        # Test that layout is properly set up
        layout = self.dock_widget.layout()
        self.assertIsInstance(layout, QtWidgets.QVBoxLayout)

        # Test layout properties
        margins = layout.contentsMargins()
        self.assertEqual(margins.left(), 0)
        self.assertEqual(margins.top(), 0)
        self.assertEqual(margins.right(), 0)
        self.assertEqual(margins.bottom(), 0)

    def test_widget_setup(self):
        # Test that a widget is set as the dock widget's main widget
        self.assertIsNotNone(self.dock_widget.widget())
        self.assertIsInstance(self.dock_widget.widget(), QtWidgets.QWidget)

        # Test that the layout is applied to the widget
        self.assertEqual(self.dock_widget.widget().layout(), self.dock_widget.layout())

    def test_add_widgets_to_layout(self):
        # Test adding widgets to the layout
        test_label = QtWidgets.QLabel("Test Label")
        test_button = QtWidgets.QPushButton("Test Button")

        self.dock_widget.layout().addWidget(test_label)
        self.dock_widget.layout().addWidget(test_button)

        # Check that widgets were added
        self.assertEqual(self.dock_widget.layout().count(), 2)
        self.assertEqual(self.dock_widget.layout().itemAt(0).widget(), test_label)
        self.assertEqual(self.dock_widget.layout().itemAt(1).widget(), test_button)

    def test_close_event_signal(self):
        # Test that closed signal is emitted on close
        signal_spy = []
        self.dock_widget.closed.connect(signal_spy.append)

        # Simulate close event
        close_event = QtGui.QCloseEvent()
        self.dock_widget.closeEvent(close_event)

        # Check that signal was emitted with correct argument
        self.assertEqual(len(signal_spy), 1)
        self.assertEqual(signal_spy[0], self.dock_widget)

    def test_show_event_signal(self):
        # Test that enabled signal is emitted on show
        signal_spy = []
        self.dock_widget.enabled.connect(lambda: signal_spy.append(True))

        # Simulate show event
        show_event = QtGui.QShowEvent()
        self.dock_widget.showEvent(show_event)

        # Check that signal was emitted
        self.assertEqual(len(signal_spy), 1)
        self.assertTrue(signal_spy[0])

    def test_multiple_instances(self):
        # Test creating multiple dock widgets
        dock2 = cuegui.AbstractDockWidget.AbstractDockWidget(
            self.main_window, "DockWidget2", QtCore.Qt.RightDockWidgetArea)
        dock3 = cuegui.AbstractDockWidget.AbstractDockWidget(
            self.main_window, "DockWidget3", QtCore.Qt.BottomDockWidgetArea)

        # Check that all widgets are added to main window
        dock_widgets = self.main_window.findChildren(QtWidgets.QDockWidget)
        self.assertIn(self.dock_widget, dock_widgets)
        self.assertIn(dock2, dock_widgets)
        self.assertIn(dock3, dock_widgets)

        # Check that they have different names
        self.assertNotEqual(self.dock_widget.objectName(), dock2.objectName())
        self.assertNotEqual(dock2.objectName(), dock3.objectName())

        dock2.deleteLater()
        dock3.deleteLater()

    def test_parent_reference(self):
        # Test that parent reference is correctly stored
        self.assertEqual(self.dock_widget.parent, self.main_window)
        self.assertIs(self.dock_widget.parent, self.main_window)

    @mock.patch('cuegui.Plugins.Plugin.__init__')
    def test_plugin_initialization(self, mock_plugin_init):
        # Create a new dock widget to test Plugin.__init__ is called
        test_dock = cuegui.AbstractDockWidget.AbstractDockWidget(
            self.main_window, "TestPluginInit")

        # Verify Plugin.__init__ was called
        mock_plugin_init.assert_called()

        test_dock.deleteLater()

    def test_dock_widget_areas(self):
        # Test all possible dock areas
        areas = [
            QtCore.Qt.LeftDockWidgetArea,
            QtCore.Qt.RightDockWidgetArea,
            QtCore.Qt.TopDockWidgetArea,
            QtCore.Qt.BottomDockWidgetArea
        ]

        for area in areas:
            dock = cuegui.AbstractDockWidget.AbstractDockWidget(
                self.main_window, f"DockArea{area}", area)

            # Check that widget is created successfully
            self.assertIsNotNone(dock)
            self.assertIn(dock, self.main_window.findChildren(QtWidgets.QDockWidget))

            dock.deleteLater()


if __name__ == '__main__':
    unittest.main()
