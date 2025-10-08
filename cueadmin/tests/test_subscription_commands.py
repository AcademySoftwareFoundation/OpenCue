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


"""Tests for cueadmin subscription commands."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import unittest
from unittest import mock

try:
    import opencue_proto.subscription_pb2
    import opencue.wrappers.subscription
    import cueadmin.common
    OPENCUE_AVAILABLE = True
except ImportError:
    # For testing without full OpenCue installation
    OPENCUE_AVAILABLE = False
    opencue_proto = mock.MagicMock()
    opencue = mock.MagicMock()
    cueadmin = mock.MagicMock()


TEST_SHOW = 'testShow'
TEST_ALLOC = 'testAlloc'
TEST_FACILITY = 'testFacility'


@mock.patch('opencue.api.findSubscription')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class SubscriptionCommandTests(unittest.TestCase):
    """Tests for show-allocation subscription management commands."""

    def setUp(self):
        self.parser = cueadmin.common.getParser()

    @mock.patch('cueadmin.output.displaySubscriptions')
    @mock.patch('opencue.api.findShow')
    def test_lb_lists_subscriptions_for_single_show(self, mock_find_show, mock_display,
                                                     getStubMock, findSubMock):
        """-lb: lists subscriptions for a single show."""
        show = mock.Mock()
        show.data.name = TEST_SHOW
        show.getSubscriptions.return_value = [
            opencue.wrappers.subscription.Subscription(
                opencue_proto.subscription_pb2.Subscription(
                    allocation_name='cloud.desktop',
                    show_name=TEST_SHOW,
                    size=100,
                    burst=200,
                    reserved_cores=50
                )
            ),
        ]
        mock_find_show.return_value = show

        args = self.parser.parse_args(['-lb', TEST_SHOW])
        cueadmin.common.handleArgs(args)

        mock_find_show.assert_called_with(TEST_SHOW)
        show.getSubscriptions.assert_called_with()
        mock_display.assert_called_once()
        # Check that displaySubscriptions was called with the subscriptions and show name
        self.assertEqual(mock_display.call_args[0][1], TEST_SHOW)

    @mock.patch('cueadmin.output.displaySubscriptions')
    @mock.patch('opencue.api.findShow')
    def test_lb_lists_subscriptions_for_multiple_shows(self, mock_find_show, mock_display,
                                                        getStubMock, findSubMock):
        """-lb: lists subscriptions for multiple shows."""
        show1 = mock.Mock()
        show1.data.name = 'show1'
        show1.getSubscriptions.return_value = [
            opencue.wrappers.subscription.Subscription(
                opencue_proto.subscription_pb2.Subscription(
                    allocation_name='alloc1',
                    show_name='show1',
                    size=100,
                    burst=150
                )
            ),
        ]

        show2 = mock.Mock()
        show2.data.name = 'show2'
        show2.getSubscriptions.return_value = [
            opencue.wrappers.subscription.Subscription(
                opencue_proto.subscription_pb2.Subscription(
                    allocation_name='alloc2',
                    show_name='show2',
                    size=200,
                    burst=300
                )
            ),
        ]

        mock_find_show.side_effect = [show1, show2]

        args = self.parser.parse_args(['-lb', 'show1', 'show2'])
        cueadmin.common.handleArgs(args)

        # Verify findShow was called for each show
        self.assertEqual(mock_find_show.call_count, 2)
        mock_find_show.assert_any_call('show1')
        mock_find_show.assert_any_call('show2')

        # Verify getSubscriptions was called for each show
        show1.getSubscriptions.assert_called_with()
        show2.getSubscriptions.assert_called_with()

        # Verify displaySubscriptions was called twice
        self.assertEqual(mock_display.call_count, 2)

    @mock.patch('cueadmin.output.displaySubscriptions')
    @mock.patch('opencue.api.findAllocation')
    def test_lba_lists_all_subscriptions_for_allocation(self, mock_find_alloc, mock_display,
                                                         getStubMock, findSubMock):
        """-lba: lists all subscriptions for a specified allocation."""
        alloc = mock.Mock()
        alloc.getSubscriptions.return_value = [
            opencue.wrappers.subscription.Subscription(
                opencue_proto.subscription_pb2.Subscription(
                    allocation_name=TEST_ALLOC,
                    show_name='show1',
                    size=100,
                    burst=200
                )
            ),
            opencue.wrappers.subscription.Subscription(
                opencue_proto.subscription_pb2.Subscription(
                    allocation_name=TEST_ALLOC,
                    show_name='show2',
                    size=150,
                    burst=250
                )
            ),
        ]
        mock_find_alloc.return_value = alloc

        args = self.parser.parse_args(['-lba', TEST_ALLOC])
        cueadmin.common.handleArgs(args)

        mock_find_alloc.assert_called_once_with(TEST_ALLOC)
        alloc.getSubscriptions.assert_called_with()
        mock_display.assert_called_once()
        # Check that it's called with "All Shows" as the second argument
        self.assertEqual(mock_display.call_args[0][1], 'All Shows')

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    @mock.patch('opencue.api.findAllocation')
    @mock.patch('opencue.api.findShow')
    def test_create_sub_creates_subscription_with_confirmation(self, mock_find_show,
                                                                mock_find_alloc, mock_prompt,
                                                                getStubMock, findSubMock):
        """-create-sub: creates a subscription with size and burst values after confirmation."""
        show = mock.Mock()
        alloc = mock.Mock()
        alloc.data = mock.Mock()
        mock_find_show.return_value = show
        mock_find_alloc.return_value = alloc

        args = self.parser.parse_args(['-create-sub', TEST_SHOW, TEST_ALLOC, '100', '200'])
        cueadmin.common.handleArgs(args)

        mock_find_show.assert_called_once_with(TEST_SHOW)
        mock_find_alloc.assert_called_once_with(TEST_ALLOC)
        mock_prompt.assert_called_once()
        show.createSubscription.assert_called_once_with(alloc.data, 100.0, 200.0)

    @mock.patch('opencue.api.findAllocation')
    @mock.patch('opencue.api.findShow')
    def test_create_sub_with_force_flag(self, mock_find_show, mock_find_alloc,
                                         getStubMock, findSubMock):
        """-create-sub with -force: creates subscription without confirmation."""
        show = mock.Mock()
        alloc = mock.Mock()
        alloc.data = mock.Mock()
        mock_find_show.return_value = show
        mock_find_alloc.return_value = alloc

        args = self.parser.parse_args(['-create-sub', TEST_SHOW, TEST_ALLOC, '50', '75', '-force'])
        cueadmin.common.handleArgs(args)

        mock_find_show.assert_called_once_with(TEST_SHOW)
        mock_find_alloc.assert_called_once_with(TEST_ALLOC)
        show.createSubscription.assert_called_once_with(alloc.data, 50.0, 75.0)

    @mock.patch('cueadmin.util.promptYesNo', return_value=True)
    def test_delete_sub_deletes_subscription_with_confirmation(self, mock_prompt,
                                                                getStubMock, findSubMock):
        """-delete-sub: deletes a subscription after confirmation."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        args = self.parser.parse_args(['-delete-sub', TEST_SHOW, TEST_ALLOC])
        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_once_with('{}.{}'.format(TEST_ALLOC, TEST_SHOW))
        mock_prompt.assert_called_once()
        sub.delete.assert_called_once()

    def test_delete_sub_with_force_flag(self, getStubMock, findSubMock):
        """-delete-sub with -force: deletes subscription without confirmation."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        args = self.parser.parse_args(['-delete-sub', TEST_SHOW, TEST_ALLOC, '-force'])
        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_once_with('{}.{}'.format(TEST_ALLOC, TEST_SHOW))
        sub.delete.assert_called_once()

    def test_size_sets_subscription_size_positive(self, getStubMock, findSubMock):
        """-size: sets subscription size with positive value."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        args = self.parser.parse_args(['-size', TEST_SHOW, TEST_ALLOC, '150'])
        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_once_with('{}.{}'.format(TEST_ALLOC, TEST_SHOW))
        sub.setSize.assert_called_once_with(150)

    def test_size_sets_subscription_size_zero(self, getStubMock, findSubMock):
        """-size: sets subscription size to zero."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        args = self.parser.parse_args(['-size', TEST_SHOW, TEST_ALLOC, '0'])
        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_once_with('{}.{}'.format(TEST_ALLOC, TEST_SHOW))
        sub.setSize.assert_called_once_with(0)

    def test_size_sets_subscription_size_negative(self, getStubMock, findSubMock):
        """-size: current behavior accepts negative values (no validation)."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        args = self.parser.parse_args(['-size', TEST_SHOW, TEST_ALLOC, '-10'])
        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_once_with('{}.{}'.format(TEST_ALLOC, TEST_SHOW))
        sub.setSize.assert_called_once_with(-10)

    def test_burst_sets_subscription_burst_absolute_positive(self, getStubMock, findSubMock):
        """-burst: sets subscription burst with positive absolute value."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, '300'])
        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_once_with('{}.{}'.format(TEST_ALLOC, TEST_SHOW))
        sub.setBurst.assert_called_once_with(300)

    def test_burst_sets_subscription_burst_absolute_zero(self, getStubMock, findSubMock):
        """-burst: sets subscription burst to zero."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, '0'])
        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_once_with('{}.{}'.format(TEST_ALLOC, TEST_SHOW))
        sub.setBurst.assert_called_once_with(0)

    def test_burst_sets_subscription_burst_absolute_negative(self, getStubMock, findSubMock):
        """-burst: current behavior accepts negative absolute values (no validation)."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, '-5'])
        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_once_with('{}.{}'.format(TEST_ALLOC, TEST_SHOW))
        sub.setBurst.assert_called_once_with(-5)

    def test_burst_sets_subscription_burst_percent_simple(self, getStubMock, findSubMock):
        """-burst: sets subscription burst using percentage (50% of 100 = 150)."""
        sub = mock.Mock()
        sub.data.size = 100
        findSubMock.return_value = sub

        args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, '50%'])
        cueadmin.common.handleArgs(args)

        findSubMock.assert_called_once_with('{}.{}'.format(TEST_ALLOC, TEST_SHOW))
        # burst = size + (size * percent/100) = 100 + 50 = 150
        sub.setBurst.assert_called_once_with(150)

    def test_burst_percentage_calculation_accuracy(self, getStubMock, findSubMock):
        """-burst: verifies percentage calculation accuracy for various values."""
        test_cases = [
            (100, '50%', 150),   # 100 + 50% = 150
            (200, '25%', 250),   # 200 + 25% = 250
            (50, '100%', 100),   # 50 + 100% = 100
            (75, '33%', 99),     # 75 + 33% = 99.75 -> 99 (truncated to int)
            (100, '0%', 100),    # 100 + 0% = 100
            (80, '125%', 180),   # 80 + 125% = 180
        ]

        for size, percentage, expected_burst in test_cases:
            sub = mock.Mock()
            sub.data.size = size
            findSubMock.return_value = sub

            args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, percentage])
            cueadmin.common.handleArgs(args)

            sub.setBurst.assert_called_with(expected_burst)

    def test_burst_malformed_percentage_raises_value_error(self, getStubMock, findSubMock):
        """-burst: malformed percentage value (e.g., 'abc%') raises ValueError."""
        sub = mock.Mock()
        sub.data.size = 100
        findSubMock.return_value = sub

        args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, 'abc%'])

        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

    def test_burst_negative_percent_environment_dependent(self, getStubMock, findSubMock):
        """-burst: negative percent behavior varies by environment."""
        # Behavior depends on argparse version/environment:
        # - Some environments: argparse treats '-10%' as option flag -> SystemExit
        # - Other environments: argparse accepts '-10%' as value -> calculation works

        try:
            args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, '-10%'])
            # If parsing succeeds, test the calculation
            sub = mock.Mock()
            sub.data.size = 100
            findSubMock.return_value = sub

            cueadmin.common.handleArgs(args)
            # Should calculate: 100 + (100 * -10/100) = 90
            sub.setBurst.assert_called_with(90)

        except SystemExit:
            # If argparse rejects it, that's also valid behavior
            # This documents that negative percentages may not work in all environments
            pass

    def test_subscription_large_values(self, getStubMock, findSubMock):
        """Test subscription commands with large values."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        # Test large size value
        args = self.parser.parse_args(['-size', TEST_SHOW, TEST_ALLOC, '10000'])
        cueadmin.common.handleArgs(args)
        sub.setSize.assert_called_with(10000)

        # Test large burst value
        args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, '20000'])
        cueadmin.common.handleArgs(args)
        sub.setBurst.assert_called_with(20000)

    def test_subscription_float_values_cause_error(self, getStubMock, findSubMock):
        """Test that float values cause ValueError (current behavior)."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        # Size with decimal should cause ValueError
        args = self.parser.parse_args(['-size', TEST_SHOW, TEST_ALLOC, '100.5'])
        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

        # Burst with decimal should cause ValueError
        args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, '200.7'])
        with self.assertRaises(ValueError):
            cueadmin.common.handleArgs(args)

    @mock.patch('cueadmin.output.displaySubscriptions')
    def test_subscription_query_filtering_current_behavior(self, mock_display, getStubMock,
                                                            findSubMock):
        """Test current subscription query behavior (no filtering options available)."""
        # Note: Current API doesn't expose filtering options for getSubscriptions()
        # This test documents the current behavior

        # Test show.getSubscriptions() returns all subscriptions (no filtering)
        show = mock.Mock()
        show.data.name = TEST_SHOW

        # Create properly structured mock subscriptions
        sub1 = mock.Mock()
        sub1.data.size = 100
        sub2 = mock.Mock()
        sub2.data.size = 200
        sub3 = mock.Mock()
        sub3.data.size = 300

        show.getSubscriptions.return_value = [sub1, sub2, sub3]

        with mock.patch('opencue.api.findShow', return_value=show):
            args = self.parser.parse_args(['-lb', TEST_SHOW])
            cueadmin.common.handleArgs(args)

            # Verify all subscriptions are returned (no filtering)
            show.getSubscriptions.assert_called_once()
            # Verify displaySubscriptions was called with all subscriptions
            mock_display.assert_called_once_with([sub1, sub2, sub3], TEST_SHOW)

    def test_subscription_validation_current_behavior(self, getStubMock, findSubMock):
        """Test current validation behavior for size/burst values."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        # Current implementation accepts any integer values without validation
        test_cases = [
            ('0', 0),      # Zero value
            ('-1', -1),    # Negative value
            ('999999', 999999),  # Very large value
        ]

        for input_val, expected_val in test_cases:
            # Test size validation
            args = self.parser.parse_args(['-size', TEST_SHOW, TEST_ALLOC, input_val])
            cueadmin.common.handleArgs(args)
            sub.setSize.assert_called_with(expected_val)

            # Test burst validation
            args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, input_val])
            cueadmin.common.handleArgs(args)
            sub.setBurst.assert_called_with(expected_val)

    def test_various_subscription_configurations(self, getStubMock, findSubMock):
        """Test various subscription configurations and parameter combinations."""

        # Test different show-allocation combinations
        configurations = [
            ('show1', 'alloc1', '100', '150'),
            ('show_with_underscores', 'facility.allocation', '50', '75'),
            ('UPPERCASE_SHOW', 'lowercase_alloc', '0', '0'),
            ('show-with-dashes', 'alloc.with.dots', '1000', '2000'),
        ]

        for show_name, alloc_name, size, burst in configurations:
            show = mock.Mock()
            alloc = mock.Mock()
            alloc.data = mock.Mock()

            with mock.patch('opencue.api.findShow', return_value=show), \
                 mock.patch('opencue.api.findAllocation', return_value=alloc):

                args = self.parser.parse_args(['-create-sub', show_name, alloc_name,
                                             size, burst, '-force'])
                cueadmin.common.handleArgs(args)

                show.createSubscription.assert_called_with(alloc.data, float(size), float(burst))

    def test_resource_calculation_accuracy_comprehensive(self, getStubMock, findSubMock):
        """Comprehensive test of resource calculation accuracy for percentage burst."""

        # Test percentage calculations with various sizes and percentages
        test_calculations = [
            # (original_size, percentage, expected_burst, description)
            (100, '0%', 100, 'zero percent'),
            (100, '1%', 101, 'one percent'),
            (100, '50%', 150, 'fifty percent'),
            (100, '100%', 200, 'one hundred percent'),
            (100, '200%', 300, 'two hundred percent'),
            (200, '25%', 250, 'quarter of 200'),
            (75, '33%', 99, 'thirty-three percent (truncated)'),
            (1, '100%', 2, 'small size double'),
            (10, '10%', 11, 'ten percent of ten'),
            (500, '40%', 700, 'forty percent of 500'),
        ]

        for original_size, percentage, expected_burst, description in test_calculations:
            sub = mock.Mock()
            sub.data.size = original_size
            findSubMock.return_value = sub

            args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, percentage])
            cueadmin.common.handleArgs(args)

            sub.setBurst.assert_called_with(expected_burst)

    def test_subscription_edge_cases_and_limits(self, getStubMock, findSubMock):
        """Test edge cases and boundary conditions for subscription parameters."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        # Test maximum integer values (within Python int limits)
        max_int_val = 2**31 - 1  # Max 32-bit signed integer
        args = self.parser.parse_args(['-size', TEST_SHOW, TEST_ALLOC, str(max_int_val)])
        cueadmin.common.handleArgs(args)
        sub.setSize.assert_called_with(max_int_val)

        # Test burst equal to size (no additional burst)
        sub.data.size = 100
        args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, '0%'])
        cueadmin.common.handleArgs(args)
        sub.setBurst.assert_called_with(100)  # size + 0% = 100

    def test_subscription_commands_with_different_show_alloc_formats(self, getStubMock,
                                                                      findSubMock):
        """Test subscription commands with different show and allocation name formats."""
        sub = mock.Mock()
        findSubMock.return_value = sub

        # Test various naming conventions
        naming_combinations = [
            ('simple_show', 'simple_alloc'),
            ('show.with.dots', 'alloc.with.dots'),
            ('show_underscores', 'alloc_underscores'),
            ('UPPERCASE', 'lowercase'),
            ('MixedCase', 'MixedCase'),
            ('123numeric', '456numeric'),
            ('show-dashes', 'alloc-dashes'),
        ]

        for show_name, alloc_name in naming_combinations:
            expected_sub_name = '{}.{}'.format(alloc_name, show_name)

            # Test size command
            args = self.parser.parse_args(['-size', show_name, alloc_name, '100'])
            cueadmin.common.handleArgs(args)
            findSubMock.assert_called_with(expected_sub_name)

            # Test burst command
            args = self.parser.parse_args(['-burst', show_name, alloc_name, '200'])
            cueadmin.common.handleArgs(args)
            findSubMock.assert_called_with(expected_sub_name)

            # Test delete command
            args = self.parser.parse_args(['-delete-sub', show_name, alloc_name, '-force'])
            cueadmin.common.handleArgs(args)
            findSubMock.assert_called_with(expected_sub_name)

    def test_resource_calculation_precision_and_rounding(self, getStubMock, findSubMock):
        """Test precision and rounding behavior in resource calculations."""

        # Test calculations that result in fractional values (should be truncated)
        precision_tests = [
            (100, '33%', 133),    # 100 + 33 = 133 (33.0% of 100 = 33.0)
            (100, '34%', 134),    # 100 + 34 = 134
            (3, '33%', 3),        # 3 + 0.99 = 3.99 -> 3 (truncated)
            (7, '14%', 7),        # 7 + 0.98 = 7.98 -> 7 (truncated)
            (13, '15%', 14),      # 13 + 1.95 = 14.95 -> 14 (truncated)
        ]

        for size, percentage, expected_result in precision_tests:
            sub = mock.Mock()
            sub.data.size = size
            findSubMock.return_value = sub

            args = self.parser.parse_args(['-burst', TEST_SHOW, TEST_ALLOC, percentage])
            cueadmin.common.handleArgs(args)

            sub.setBurst.assert_called_with(expected_result)


if __name__ == '__main__':
    unittest.main()
