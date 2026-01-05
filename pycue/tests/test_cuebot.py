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

"""Tests for `opencue.cuebot`."""

import os
import time
import unittest
import mock

import grpc

import opencue
from opencue import cuebot


TESTING_CONFIG = {
    "cuebot.facility_default": "fake-facility-01",
    "cuebot.facility": {
        "fake-facility-01": [
            "fake-cuebot-01",
        ],
        "fake-facility-02": [
            "fake-cuebot-02",
            "fake-cuebot-03",
        ],
    },
}


class CuebotTests(unittest.TestCase):
    def setUp(self):
        self.cuebot = opencue.Cuebot()
        # Mocking the cue service ensures the initial healthcheck request made to Cuebot
        # will succeed.
        self.cuebot.SERVICE_MAP['cue'] = mock.Mock()

    def test__should_set_hosts_and_channel(self):
        healthcheck_mock = mock.Mock()
        self.cuebot.SERVICE_MAP['cue'] = healthcheck_mock

        # Clear any existing overrides
        if 'CUEBOT_HOSTS' in os.environ:
            del os.environ['CUEBOT_HOSTS']
        self.cuebot.init(config=TESTING_CONFIG)

        self.assertEqual(["fake-cuebot-01"], self.cuebot.Hosts)
        self.assertIsNotNone(self.cuebot.RpcChannel)
        healthcheck_mock.assert_called_with(self.cuebot.RpcChannel)

    def test__should_set_known_facility(self):
        self.cuebot.init(config=TESTING_CONFIG)

        self.cuebot.setHostWithFacility('fake-facility-02')

        self.assertEqual(['fake-cuebot-02', 'fake-cuebot-03'], self.cuebot.Hosts)

    def test__should_ignore_unknown_facility(self):
        self.cuebot.init(config=TESTING_CONFIG)

        self.cuebot.setHostWithFacility('unknown-facility')

        self.assertEqual(['fake-cuebot-01'], self.cuebot.Hosts)


class ConnectionHealthTests(unittest.TestCase):
    """Tests for gRPC connection health tracking and recovery."""

    def setUp(self):
        """Reset connection health state before each test."""
        opencue.Cuebot._consecutiveFailures = 0
        opencue.Cuebot._lastSuccessfulCall = 0
        opencue.Cuebot._channelResetInProgress = False

    def tearDown(self):
        """Reset connection health state after each test."""
        opencue.Cuebot._consecutiveFailures = 0
        opencue.Cuebot._lastSuccessfulCall = 0
        opencue.Cuebot._channelResetInProgress = False

    def test__keepalive_constants_defined(self):
        """Test that keepalive constants are defined with expected values."""
        self.assertEqual(cuebot.DEFAULT_KEEPALIVE_TIME_MS, 30000)
        self.assertEqual(cuebot.DEFAULT_KEEPALIVE_TIMEOUT_MS, 10000)
        self.assertTrue(cuebot.DEFAULT_KEEPALIVE_PERMIT_WITHOUT_CALLS)

    def test__record_successful_call_updates_timestamp(self):
        """Test that recordSuccessfulCall updates the last successful call timestamp."""
        before = time.time()
        opencue.Cuebot.recordSuccessfulCall()
        after = time.time()

        self.assertGreaterEqual(opencue.Cuebot._lastSuccessfulCall, before)
        self.assertLessEqual(opencue.Cuebot._lastSuccessfulCall, after)

    def test__record_successful_call_resets_failure_counter(self):
        """Test that recordSuccessfulCall resets the consecutive failure counter."""
        opencue.Cuebot._consecutiveFailures = 2

        opencue.Cuebot.recordSuccessfulCall()

        self.assertEqual(opencue.Cuebot._consecutiveFailures, 0)

    def test__record_failed_call_increments_counter(self):
        """Test that recordFailedCall increments the consecutive failure counter."""
        self.assertEqual(opencue.Cuebot._consecutiveFailures, 0)

        opencue.Cuebot.recordFailedCall()
        self.assertEqual(opencue.Cuebot._consecutiveFailures, 1)

        opencue.Cuebot.recordFailedCall()
        self.assertEqual(opencue.Cuebot._consecutiveFailures, 2)

    @mock.patch.object(opencue.Cuebot, 'resetChannel')
    def test__record_failed_call_resets_channel_after_max_failures(self, mock_reset):
        """Test that recordFailedCall triggers channel reset after max consecutive failures."""
        # Simulate failures up to the threshold
        for i in range(opencue.Cuebot._maxConsecutiveFailures - 1):
            result = opencue.Cuebot.recordFailedCall()
            self.assertFalse(result)
            mock_reset.assert_not_called()

        # The next failure should trigger a reset
        result = opencue.Cuebot.recordFailedCall()
        self.assertTrue(result)
        mock_reset.assert_called_once()

        # Counter should be reset after channel reset
        self.assertEqual(opencue.Cuebot._consecutiveFailures, 0)

    @mock.patch.object(opencue.Cuebot, 'resetChannel')
    def test__record_failed_call_does_not_reset_when_already_in_progress(self, mock_reset):
        """Test that recordFailedCall doesn't trigger reset if one is already in progress."""
        opencue.Cuebot._channelResetInProgress = True
        opencue.Cuebot._consecutiveFailures = opencue.Cuebot._maxConsecutiveFailures

        result = opencue.Cuebot.recordFailedCall()

        self.assertFalse(result)
        mock_reset.assert_not_called()

    @mock.patch.object(opencue.Cuebot, 'getStub')
    def test__check_channel_health_returns_true_on_success(self, mock_get_stub):
        """Test that checkChannelHealth returns True when the health check succeeds."""
        mock_stub = mock.Mock()
        mock_get_stub.return_value = mock_stub
        opencue.Cuebot.RpcChannel = mock.Mock()

        result = opencue.Cuebot.checkChannelHealth()

        self.assertTrue(result)
        mock_get_stub.assert_called_with('cue')
        self.assertEqual(opencue.Cuebot._consecutiveFailures, 0)

    @mock.patch.object(opencue.Cuebot, 'getStub')
    @mock.patch.object(opencue.Cuebot, 'recordFailedCall')
    def test__check_channel_health_returns_false_on_unavailable(
            self, mock_record_failed, mock_get_stub):
        """Test that checkChannelHealth returns False on UNAVAILABLE error."""
        mock_stub = mock.Mock()
        error = grpc.RpcError()
        error.code = mock.Mock(return_value=grpc.StatusCode.UNAVAILABLE)
        error.details = mock.Mock(return_value="Connection refused")
        mock_stub.GetSystemStats.side_effect = error
        mock_get_stub.return_value = mock_stub
        opencue.Cuebot.RpcChannel = mock.Mock()

        result = opencue.Cuebot.checkChannelHealth()

        self.assertFalse(result)
        mock_record_failed.assert_called_once()

    def test__check_channel_health_returns_false_when_no_channel(self):
        """Test that checkChannelHealth returns False when RpcChannel is None."""
        opencue.Cuebot.RpcChannel = None

        result = opencue.Cuebot.checkChannelHealth()

        self.assertFalse(result)

    def test__max_consecutive_failures_default(self):
        """Test that the default max consecutive failures is set correctly."""
        self.assertEqual(opencue.Cuebot._maxConsecutiveFailures, 3)


if __name__ == '__main__':
    unittest.main()
