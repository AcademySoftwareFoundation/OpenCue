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


"""Tests for cuegui.LicensesWidget."""


import unittest

import mock
import qtpy.QtCore
import qtpy.QtWidgets

import opencue.wrappers.license
import opencue_proto.license_pb2

import cuegui.LicensesWidget
import cuegui.Style

from . import test_utils


def _license(name='hengine', feature='Houdini Engine', host_based=True):
    return opencue.wrappers.license.License(
        opencue_proto.license_pb2.License(
            name=name,
            feature=feature,
            total=800,
            available=794,
            host_based=host_based,
            headroom=5,
            running_frames=12,
            running_hosts=3,
            provider_host_count=2))


def _status(configured=True, has_sample=True, stale=False, licenses=None):
    return opencue.wrappers.license.LicensingStatus(
        opencue_proto.license_pb2.LicenseGetAllResponse(
            source=opencue_proto.license_pb2.LicenseSourceStatus(
                configured=configured,
                provider='http://lic-reporter:9101/licenses' if configured else '',
                env_key='CUE_LICENSES',
                poll_seconds=20,
                stale_seconds=300,
                has_sample=has_sample,
                age_seconds=17 if has_sample else 0,
                stale=stale),
            licenses=licenses or []))


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class LicensesWidgetTests(unittest.TestCase):

    def setUp(self):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        # Kept as instance attr so the parent isn't garbage-collected mid-test.
        self.parentWidget = qtpy.QtWidgets.QWidget()
        self.widget = cuegui.LicensesWidget.LicensesWidget(self.parentWidget)
        self.tree = self.widget.findChild(cuegui.LicensesWidget.LicensesTreeWidget)
        self.label = self.widget.findChild(qtpy.QtWidgets.QLabel)

    def test_itemDisplaysLicenseColumns(self):
        item = cuegui.LicensesWidget.LicenseWidgetItem(_license(), self.tree)

        displayRole = qtpy.QtCore.Qt.DisplayRole
        self.assertEqual('hengine', item.data(0, displayRole))
        self.assertEqual('Houdini Engine', item.data(1, displayRole))
        self.assertEqual('Host-based', item.data(2, displayRole))
        self.assertEqual('800', item.data(3, displayRole))
        self.assertEqual('794', item.data(4, displayRole))
        self.assertEqual('6', item.data(5, displayRole))
        self.assertEqual('5', item.data(6, displayRole))
        self.assertEqual('12', item.data(7, displayRole))
        self.assertEqual('3', item.data(8, displayRole))
        self.assertEqual('2', item.data(9, displayRole))

    def test_floatingTypeString(self):
        item = cuegui.LicensesWidget.LicenseWidgetItem(
            _license(name='maya', host_based=False), self.tree)

        self.assertEqual('Floating', item.data(2, qtpy.QtCore.Qt.DisplayRole))

    def test_updateFillsTableAndStatusLine(self):
        status = _status(licenses=[
            opencue_proto.license_pb2.License(name='hengine', feature='Houdini Engine')])

        with mock.patch.object(opencue.api, 'getLicensingStatus', return_value=status):
            # pylint: disable=protected-access
            rpcObjects = self.tree._getUpdate()
            self.tree._processUpdate(None, rpcObjects)

        self.assertEqual(1, self.tree.topLevelItemCount())
        self.assertIn('http://lic-reporter:9101/licenses', self.label.text())
        self.assertNotIn('STALE', self.label.text())

    def test_staleSampleIsCalledOutInStatusLine(self):
        status = _status(stale=True)

        with mock.patch.object(opencue.api, 'getLicensingStatus', return_value=status):
            # pylint: disable=protected-access
            self.tree._processUpdate(None, self.tree._getUpdate())

        self.assertIn('STALE', self.label.text())
        self.assertIn('held', self.label.text())

    def test_unconfiguredProviderIsExplained(self):
        status = _status(configured=False, has_sample=False)

        with mock.patch.object(opencue.api, 'getLicensingStatus', return_value=status):
            # pylint: disable=protected-access
            self.tree._processUpdate(None, self.tree._getUpdate())

        self.assertIn('not configured', self.label.text())

    def test_failedFetchKeepsGoing(self):
        with mock.patch.object(
                opencue.api, 'getLicensingStatus',
                side_effect=opencue.exception.CueException('boom')):
            # pylint: disable=protected-access
            rpcObjects = self.tree._getUpdate()

        self.assertEqual([], rpcObjects)

    def test_failedRefreshDoesNotKeepPromisingAHealthyProvider(self):
        # A good refresh, then Cuebot goes away: the table empties, so the
        # status line must stop showing the stale healthy provider text.
        good = _status(licenses=[
            opencue_proto.license_pb2.License(name='hengine', feature='Houdini Engine')])
        with mock.patch.object(opencue.api, 'getLicensingStatus', return_value=good):
            # pylint: disable=protected-access
            self.tree._processUpdate(None, self.tree._getUpdate())
        self.assertIn('http://lic-reporter:9101/licenses', self.label.text())

        with mock.patch.object(
                opencue.api, 'getLicensingStatus',
                side_effect=opencue.exception.CueException('boom')):
            # pylint: disable=protected-access
            self.tree._processUpdate(None, self.tree._getUpdate())

        self.assertEqual(0, self.tree.topLevelItemCount())
        self.assertIn('unavailable', self.label.text())
        self.assertNotIn('http://lic-reporter:9101/licenses', self.label.text())


if __name__ == '__main__':
    unittest.main()
