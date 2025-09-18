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
import unittest
import mock

import opencue


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


if __name__ == '__main__':
    unittest.main()
