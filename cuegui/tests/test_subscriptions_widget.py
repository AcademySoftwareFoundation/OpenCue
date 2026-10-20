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

    def test_olderUpdateLandingLastIsDropped(self):
        show = _show('show1')
        with mock.patch.object(self.tree, '_update'):
            self.tree.setShow(show)
        app = self.tree.app
        app.threadpool = mock.Mock()
        self.addCleanup(setattr, app, 'threadpool', None)

        self.tree._update()
        self.tree._update()
        older, newer = [call[0][1] for call in app.threadpool.queue.call_args_list]
        newer(None, (show, [_subscription('sub2')]))
        older(None, (show, [_subscription('sub1')]))

        self.assertEqual(['Subscription.sub2'], sorted(self.tree._items))


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
@mock.patch('opencue.wrappers.show.Show.getSubscriptions', new=mock.Mock(return_value=[]))
class SubscriptionsWidgetTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        # Holds the show listing back until the test hands it over.
        self.app.action_runner = mock.Mock()
        self.addCleanup(setattr, self.app, 'action_runner', None)
        self.widget = cuegui.SubscriptionsWidget.SubscriptionsWidget(None)
        self.combo = self.widget._SubscriptionsWidget__comboShows

    def _listShows(self, *names):
        _, callback, _ = self.app.action_runner.submit.call_args[0]
        callback({name: _show(name) for name in names}, None)

    def _comboItems(self):
        return [self.combo.itemText(i) for i in range(self.combo.count())]

    def test_setShowBeforeShowsAreListed(self):
        show = _show('show1')

        self.widget.setShow(show)

        self.assertIs(show, self.widget.getShow())
        self.assertEqual('show1', self.combo.currentText())

    def test_listingKeepsSelectedShow(self):
        self.widget.setShow(_show('show2'))

        self._listShows('show1', 'show2')

        self.assertEqual('show2', self.widget.getShowName())
        self.assertEqual('show2', self.combo.currentText())
        self.assertEqual(['Select Show:', 'show1', 'show2'], self._comboItems())

    def test_listingDropsUnlistedShow(self):
        self.widget.setShow(_show('show3'))

        self._listShows('show1')

        self.assertIsNone(self.widget.getShow())
        self.assertEqual(0, self.combo.currentIndex())
        self.assertEqual(['Select Show:', 'show1'], self._comboItems())

    def test_comboSelectsShow(self):
        self._listShows('show1', 'show2')

        self.combo.setCurrentIndex(2)

        self.assertEqual('show2', self.widget.getShowName())


if __name__ == '__main__':
    unittest.main()
