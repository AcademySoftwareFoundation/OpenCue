# Copyright Contributors to the OpenCue Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
Unit tests for CueAdmin subscription commands.
"""

import unittest
from unittest.mock import MagicMock, patch

from cueadmin.common import getParser, handleArgs


class TestSubscriptionCommands(unittest.TestCase):
    """Tests for show-allocation subscription management commands. """

    def parse(self, argv):
        """Parse an argv list into a Namespace using the real CueAdmin parser."""
        parser = getParser()
        return parser.parse_args(argv)

    @patch('cueadmin.common.cueadmin.output.displaySubscriptions')
    @patch('cueadmin.common.opencue.api.findShow')
    def test_lb_lists_subscriptions_for_shows(self, mock_find_show, mock_display):
        """-lb: lists subscriptions for each provided show and prints results per show."""
        show1 = MagicMock()
        show1.data.name = 'showA'
        show1.getSubscriptions.return_value = ['subA1', 'subA2']
        show2 = MagicMock()
        show2.data.name = 'showB'
        show2.getSubscriptions.return_value = ['subB1']

        # resolveShowNames in common.py uses opencue.api.findShow(name) in a loop
        mock_find_show.side_effect = [show1, show2]

        args = self.parse(['-lb', 'showA', 'showB'])
        handleArgs(args)

        # displaySubscriptions called once per show with the list and the show name
        expected = [(['subA1', 'subA2'], 'showA'), (['subB1'], 'showB')]
        actual = [c.args for c in mock_display.call_args_list]
        self.assertEqual(actual, expected)

    @patch('cueadmin.common.cueadmin.output.displaySubscriptions')
    @patch('cueadmin.common.opencue.api.findAllocation')
    def test_lba_lists_subscriptions_for_allocation(self, mock_find_alloc, mock_display):
        """-lba: lists all subscriptions for a specified allocation."""
        alloc = MagicMock()
        alloc.getSubscriptions.return_value = ['subX', 'subY']
        mock_find_alloc.return_value = alloc

        args = self.parse(['-lba', 'allocA'])
        handleArgs(args)

        mock_find_alloc.assert_called_once_with('allocA')
        mock_display.assert_called_once_with(['subX', 'subY'], 'All Shows')

    @patch('cueadmin.common.cueadmin.util.promptYesNo', return_value=True)
    @patch('cueadmin.common.opencue.api.findAllocation')
    @patch('cueadmin.common.opencue.api.findShow')
    def test_create_sub_creates_subscription(self, mock_find_show, mock_find_alloc, _prompt):
        """-create-sub: creates a subscription with size and burst values after confirm."""
        show = MagicMock()
        alloc = MagicMock()
        alloc.data = MagicMock()
        mock_find_show.return_value = show
        mock_find_alloc.return_value = alloc

        args = self.parse(['-create-sub', 'showA', 'allocA', '10', '20'])
        # Force confirmation bypass via promptYesNo patched to True
        handleArgs(args)

        mock_find_show.assert_called_once_with('showA')
        mock_find_alloc.assert_called_once_with('allocA')
        show.createSubscription.assert_called_once()
        pos = show.createSubscription.call_args[0]
        self.assertIs(pos[0], alloc.data)
        self.assertEqual(pos[1], 10.0)
        self.assertEqual(pos[2], 20.0)

    @patch('cueadmin.common.cueadmin.util.promptYesNo', return_value=True)
    @patch('cueadmin.common.opencue.api.findSubscription')
    def test_delete_sub_deletes_subscription(self, mock_find_sub, _prompt):
        """-delete-sub: deletes a subscription for a show/allocation pair after confirm."""
        sub = MagicMock()
        mock_find_sub.return_value = sub

        args = self.parse(['-delete-sub', 'showA', 'allocA'])
        handleArgs(args)

        mock_find_sub.assert_called_once_with('allocA.showA')
        sub.delete.assert_called_once()

    @patch('cueadmin.common.opencue.api.findSubscription')
    def test_size_sets_subscription_size(self, mock_find_sub):
        """-size: sets subscription size using an absolute integer value."""
        sub = MagicMock()
        mock_find_sub.return_value = sub

        args = self.parse(['-size', 'showA', 'allocA', '15'])
        handleArgs(args)

        mock_find_sub.assert_called_once_with('allocA.showA')
        sub.setSize.assert_called_once_with(15)

    @patch('cueadmin.common.opencue.api.findSubscription')
    def test_size_negative_sets_subscription_size_current_behavior(self, mock_find_sub):
        """-size: current behavior accepts negative values (no validation in implementation)."""
        sub = MagicMock()
        mock_find_sub.return_value = sub

        args = self.parse(['-size', 'showA', 'allocA', '-1'])
        handleArgs(args)

        mock_find_sub.assert_called_once_with('allocA.showA')
        sub.setSize.assert_called_once_with(-1)

    @patch('cueadmin.common.opencue.api.findSubscription')
    def test_burst_sets_subscription_burst_absolute(self, mock_find_sub):
        """-burst: sets subscription burst using an absolute integer value."""
        sub = MagicMock()
        mock_find_sub.return_value = sub

        args = self.parse(['-burst', 'showA', 'allocA', '30'])
        handleArgs(args)

        mock_find_sub.assert_called_once_with('allocA.showA')
        sub.setBurst.assert_called_once_with(30)

    @patch('cueadmin.common.opencue.api.findSubscription')
    def test_burst_sets_subscription_burst_negative_absolute_current_behavior(self, mock_find_sub):
        """-burst: current behavior accepts negative absolute values (no validation)."""
        sub = MagicMock()
        mock_find_sub.return_value = sub

        args = self.parse(['-burst', 'showA', 'allocA', '-5'])
        handleArgs(args)

        mock_find_sub.assert_called_once_with('allocA.showA')
        sub.setBurst.assert_called_once_with(-5)

    @patch('cueadmin.common.opencue.api.findSubscription')
    def test_burst_sets_subscription_burst_percent(self, mock_find_sub):
        """-burst: sets subscription burst using a percentage of the current size."""
        # burst = size + (size * percent/100)
        sub = MagicMock()
        sub.data.size = 100
        mock_find_sub.return_value = sub

        args = self.parse(['-burst', 'showA', 'allocA', '50%'])
        handleArgs(args)

        sub.setBurst.assert_called_once_with(150)

    @patch('cueadmin.common.opencue.api.findSubscription')
    def test_burst_negative_percent_rejected_by_cli(self, mock_find_sub):
        """-burst: negative percent value is rejected by argparse (parse error)."""
        # Values that start with '-' and end with '%' are interpreted as options by argparse
        # and cause a parse error before handleArgs is invoked.
        with self.assertRaises(SystemExit):
            self.parse(['-burst', 'showA', 'allocA', '-10%'])

    @patch('cueadmin.common.opencue.api.findSubscription')
    def test_burst_bad_percent_format_raises_value_error(self, mock_find_sub):
        """-burst: malformed percentage value (e.g., 'abc%') should raise ValueError."""
        sub = MagicMock()
        sub.data.size = 100
        mock_find_sub.return_value = sub

        args = self.parse(['-burst', 'showA', 'allocA', 'abc%'])
        with self.assertRaises(ValueError):
            handleArgs(args)

if __name__ == '__main__':
    unittest.main()
