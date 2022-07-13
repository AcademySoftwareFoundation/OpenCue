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

"""Tests for `opencue.config`."""

import os
import unittest

import mock
import pyfakefs.fake_filesystem_unittest

import opencue.config


EXPECTED_DEFAULT_CONFIG = {
    'logger.format': '%(levelname)-9s %(module)-10s %(message)s',
    'logger.level': 'WARNING',
    'cuebot.protocol': 'tcp',
    'cuebot.grpc_port': 8443,
    'cuebot.timeout': 10000,
    'cuebot.max_message_bytes': 104857600,
    'cuebot.exception_retries': 3,
    'cuebot.facility_default': 'local',
    'cuebot.facility': {
        'local': ['localhost:8443'],
        'dev': ['cuetest02-vm.example.com:8443'],
        'cloud': [
            'cuebot1.example.com:8443',
            'cuebot2.example.com:8443',
            'cuebot3.example.com:8443'
        ],
    },
}

USER_CONFIG = """
cuebot.facility_default: fake-facility-01
cuebot.facility:
  fake-facility-01:
    - fake-cuebot-01:1234
  fake-facility-02:
    - fake-cuebot-02:5678
    - fake-cuebot-03:9012
"""


class ConfigTests(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.fs.add_real_file(
            os.path.join(os.path.dirname(opencue.__file__), 'default.yaml'), read_only=True)
        if 'OPENCUE_CONFIG_FILE' in os.environ:
            del os.environ['OPENCUE_CONFIG_FILE']
        if 'OPENCUE_CONF' in os.environ:
            del os.environ['OPENCUE_CONF']

    @mock.patch('platform.system', new=mock.Mock(return_value='Linux'))
    @mock.patch('os.path.expanduser', new=mock.Mock(return_value='/home/username'))
    def test__should_return_config_dir_unix(self):
        self.assertEqual('/home/username/.config/opencue', opencue.config.config_base_directory())

    @mock.patch('platform.system', new=mock.Mock(return_value='Windows'))
    @mock.patch(
        'os.path.expandvars', new=mock.Mock(return_value='C:/Users/username/AppData/Roaming'))
    def test__should_return_config_dir_windows(self):
        self.assertEqual(
            'C:/Users/username/AppData/Roaming/opencue', opencue.config.config_base_directory())

    def test__should_load_default_config(self):
        self.assertIsNone(os.environ.get('OPENCUE_CONFIG_FILE'))
        self.assertIsNone(os.environ.get('OPENCUE_CONF'))

        config = opencue.config.load_config_from_file()

        self.assertEqual(EXPECTED_DEFAULT_CONFIG, config)

    def test__should_load_user_config(self):
        config_file_path = '/path/to/config.yaml'
        self.fs.create_file(config_file_path, contents=USER_CONFIG)
        os.environ['OPENCUE_CONFIG_FILE'] = config_file_path
        # Define some invalid config using the old setting name, this ensures the old env var
        # will be ignored if the new one is set.
        config_file_path_legacy = '/path/to/legacy/config.yaml'
        self.fs.create_file(config_file_path_legacy, contents='invalid yaml')
        os.environ['OPENCUE_CONF'] = config_file_path_legacy

        config = opencue.config.load_config_from_file()

        self.assertEqual('fake-facility-01', config['cuebot.facility_default'])
        self.assertEqual(['fake-cuebot-01:1234'], config['cuebot.facility']['fake-facility-01'])
        self.assertEqual(
            ['fake-cuebot-02:5678', 'fake-cuebot-03:9012'],
            config['cuebot.facility']['fake-facility-02'])
        # Settings not defined in user config should still have default values.
        self.assertEqual(10000, config['cuebot.timeout'])
        self.assertEqual(3, config['cuebot.exception_retries'])

    def test__should_load_user_config_from_legacy_var(self):
        config_file_path = '/path/to/legacy/config.yaml'
        self.fs.create_file(config_file_path, contents=USER_CONFIG)
        os.environ['OPENCUE_CONF'] = config_file_path

        config = opencue.config.load_config_from_file()

        self.assertEqual('fake-facility-01', config['cuebot.facility_default'])
        self.assertEqual(['fake-cuebot-01:1234'], config['cuebot.facility']['fake-facility-01'])
        self.assertEqual(
            ['fake-cuebot-02:5678', 'fake-cuebot-03:9012'],
            config['cuebot.facility']['fake-facility-02'])
        # Settings not defined in user config should still have default values.
        self.assertEqual(10000, config['cuebot.timeout'])
        self.assertEqual(3, config['cuebot.exception_retries'])

    @mock.patch('platform.system', new=mock.Mock(return_value='Linux'))
    @mock.patch('os.path.expanduser', new=mock.Mock(return_value='/home/username'))
    def test__should_load_user_config_from_user_profile(self):
        config_file_path = '/home/username/.config/opencue/opencue.yaml'
        self.fs.create_file(config_file_path, contents=USER_CONFIG)

        config = opencue.config.load_config_from_file()

        self.assertEqual('fake-facility-01', config['cuebot.facility_default'])
        self.assertEqual(['fake-cuebot-01:1234'], config['cuebot.facility']['fake-facility-01'])
        self.assertEqual(
            ['fake-cuebot-02:5678', 'fake-cuebot-03:9012'],
            config['cuebot.facility']['fake-facility-02'])
        # Settings not defined in user config should still have default values.
        self.assertEqual(10000, config['cuebot.timeout'])
        self.assertEqual(3, config['cuebot.exception_retries'])


if __name__ == '__main__':
    unittest.main()
