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


"""Tests for cuegui.SubscriptionsWidget."""


import unittest

import mock
import qtpy.QtCore
import qtpy.QtWidgets

import opencue_proto.show_pb2
import opencue_proto.subscription_pb2
import opencue.wrappers.show
import opencue.wrappers.subscription

import cuegui.Style
import cuegui.SubscriptionsWidget

from . import test_utils


def _show(name):
    return opencue.wrappers.show.Show(opencue_proto.show_pb2.Show(id=name, name=name))


def _subscription(name):
    return opencue.wrappers.subscription.Subscription(
        opencue_proto.subscription_pb2.Subscription(id=name, name=name))


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class SubscriptionsTreeWidgetTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        self.parentWidget = qtpy.QtWidgets.QWidget()
        self.tree = cuegui.SubscriptionsWidget.SubscriptionsTreeWidget(self.parentWidget)

    def _isLocked(self):
        if self.tree._itemsLock.tryLockForWrite():
            self.tree._itemsLock.unlock()
            return False
        return True

    def test_setShowShowsSubscriptions(self):
        show = _show('show1')
        with mock.patch.object(show, 'getSubscriptions',
                               return_value=[_subscription('sub1'), _subscription('sub2')]):
            self.tree.setShow(show)

        self.assertIs(show, self.tree.getShow())
        self.assertEqual(['Subscription.sub1', 'Subscription.sub2'], sorted(self.tree._items))

    def test_getUpdateDoesNotHoldLockDuringRpc(self):
        show = _show('show1')
        locked = []

        def getSubscriptions():
            locked.append(self._isLocked())
            return []

        with mock.patch.object(show, 'getSubscriptions', side_effect=getSubscriptions):
            self.tree.setShow(show)

        self.assertEqual([False], locked)

    def test_setShowDoesNotHoldLockDuringRpcs(self):
        show = _show('show1')
        locked = []

        def findShow(name):
            locked.append(self._isLocked())
            return show

        with mock.patch('opencue.api.findShow', side_effect=findShow), \
                mock.patch.object(self.tree, '_update',
                                  side_effect=lambda: locked.append(self._isLocked())):
            self.tree.setShow('show1')

        self.assertIs(show, self.tree.getShow())
        self.assertEqual([False, False], locked)

    def test_subscriptionsOfPreviousShowAreDropped(self):
        show1 = _show('show1')
        show2 = _show('show2')
        with mock.patch.object(self.tree, '_update'):
            self.tree.setShow(show1)
        with mock.patch.object(show1, 'getSubscriptions', return_value=[_subscription('sub1')]):
            update = self.tree._getUpdate()
        with mock.patch.object(self.tree, '_update'):
            self.tree.setShow(show2)

        self.tree._processUpdate(None, update)

        self.assertEqual({}, self.tree._items)


if __name__ == '__main__':
    unittest.main()
