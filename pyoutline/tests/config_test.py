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

"""Tests for the outline.config module."""

import getpass
import os.path
import unittest

import mock
import pyfakefs.fake_filesystem_unittest

import opencue
import outline
# The local import is necessary as `outline.config` will point to the ConfigParser after the
# first import.
from outline.config import read_config_from_disk


USER_CONFIG = '''
[outline]
home = /some/users/home/dir
session_dir = {HOME}/.opencue/sessions
wrapper_dir = %(home)s/wrappers
user_dir = /arbitrary/user/dir
spec_version = 1.9
facility = cloud

[plugin:local]
module=outline.plugins.local
enable=1
'''


class ConfigTest(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.fs.add_real_file(
            os.path.join(os.path.dirname(opencue.__file__), 'default.yaml'), read_only=True)
        if 'OL_CONFIG' in os.environ:
            del os.environ['OL_CONFIG']
        if 'OUTLINE_CONFIG_FILE' in os.environ:
            del os.environ['OUTLINE_CONFIG_FILE']

    @mock.patch('tempfile.gettempdir', new=mock.Mock(return_value='/path/to/tmp/dir'))
    def test__should_load_default_values(self):
        self.assertIsNone(os.environ.get('OL_CONF'))
        self.assertIsNone(os.environ.get('OUTLINE_CONFIG_FILE'))
        self.fs.add_real_file(
            os.path.join(os.path.dirname(outline.__file__), 'outline.cfg'),
            read_only=True)

        config = read_config_from_disk()

        default_home = os.path.dirname(os.path.dirname(__file__))
        self.assertEqual(default_home, config.get('outline', 'home'))
        self.assertEqual('{HOME}/.opencue/sessions', config.get('outline', 'session_dir'))
        self.assertEqual(
            os.path.join(default_home, 'wrappers'), config.get('outline', 'wrapper_dir'))
        self.assertEqual(
            '/path/to/tmp/dir/opencue/outline/%s' % getpass.getuser(),
            config.get('outline', 'user_dir'))
        self.assertEqual(
            os.path.join(default_home, 'bin'), config.get('outline', 'bin_dir'))
        self.assertEqual('cue', config.get('outline', 'backend'))
        self.assertEqual('local', config.get('outline', 'facility'))
        self.assertEqual('example.com', config.get('outline', 'domain'))
        self.assertEqual('2', config.get('outline', 'maxretries'))
        self.assertEqual('testing', config.get('outline', 'default_show'))
        self.assertEqual('default', config.get('outline', 'default_shot'))
        self.assertEqual('outline.plugins.local', config.get('plugin:local', 'module'))
        self.assertEqual('1', config.get('plugin:local', 'enable'))

    def test__should_load_user_config_from_env_var(self):
        config_file_path = '/path/to/outline.cfg'
        self.fs.create_file(config_file_path, contents=USER_CONFIG)
        os.environ['OUTLINE_CONFIG_FILE'] = config_file_path

        config = read_config_from_disk()

        custom_home = '/some/users/home/dir'
        self.assertEqual(custom_home, config.get('outline', 'home'))
        self.assertEqual('{HOME}/.opencue/sessions', config.get('outline', 'session_dir'))
        self.assertEqual(
            os.path.join(custom_home, 'wrappers'), config.get('outline', 'wrapper_dir'))
        self.assertEqual('/arbitrary/user/dir', config.get('outline', 'user_dir'))
        self.assertEqual('1.9', config.get('outline', 'spec_version'))
        self.assertEqual('cloud', config.get('outline', 'facility'))

    def test__should_load_user_config_from_legacy_env_var(self):
        config_file_path = '/path/to/outline.cfg'
        self.fs.create_file(config_file_path, contents=USER_CONFIG)
        os.environ['OL_CONFIG'] = config_file_path

        config = read_config_from_disk()

        custom_home = '/some/users/home/dir'
        self.assertEqual(custom_home, config.get('outline', 'home'))
        self.assertEqual('{HOME}/.opencue/sessions', config.get('outline', 'session_dir'))
        self.assertEqual(
            os.path.join(custom_home, 'wrappers'), config.get('outline', 'wrapper_dir'))
        self.assertEqual('/arbitrary/user/dir', config.get('outline', 'user_dir'))
        self.assertEqual('1.9', config.get('outline', 'spec_version'))
        self.assertEqual('cloud', config.get('outline', 'facility'))

    @mock.patch('platform.system', new=mock.Mock(return_value='Linux'))
    @mock.patch('os.path.expanduser', new=mock.Mock(return_value='/home/username'))
    def test__should_load_user_config_from_user_profile(self):
        config_file_path = '/home/username/.config/opencue/outline.cfg'
        self.fs.create_file(config_file_path, contents=USER_CONFIG)
        os.environ['OL_CONFIG'] = config_file_path

        config = read_config_from_disk()

        custom_home = '/some/users/home/dir'
        self.assertEqual(custom_home, config.get('outline', 'home'))
        self.assertEqual('{HOME}/.opencue/sessions', config.get('outline', 'session_dir'))
        self.assertEqual(
            os.path.join(custom_home, 'wrappers'), config.get('outline', 'wrapper_dir'))
        self.assertEqual('/arbitrary/user/dir', config.get('outline', 'user_dir'))
        self.assertEqual('1.9', config.get('outline', 'spec_version'))
        self.assertEqual('cloud', config.get('outline', 'facility'))


if __name__ == '__main__':
    unittest.main()
