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


"""Tests for cuesubmit.Config"""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import unittest

import mock
import pyfakefs.fake_filesystem_unittest

import cuesubmit.Config


CONFIG_YAML = b'''
# Some comment
UI_NAME : "OPENCUESUBMIT"
SUBMIT_APP_WINDOW_TITLE : "OpenCue Submit"
'''

CONFIG_YAML_INVALID = b' " some text in an unclosed quote'


class ConfigTests(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        if 'CUESUBMIT_CONFIG_FILE' in os.environ:
            del os.environ['CUESUBMIT_CONFIG_FILE']

    def test__should_skip_missing_files_without_error(self):
        configData = cuesubmit.Config.getConfigValues()

        self.assertDictEqual({}, configData)

    def test__should_load_config_from_env_var(self):
        config_file_path = '/path/to/config.yaml'
        self.fs.create_file(config_file_path, contents=CONFIG_YAML)
        os.environ['CUESUBMIT_CONFIG_FILE'] = config_file_path

        configData = cuesubmit.Config.getConfigValues()

        self.assertEqual('OPENCUESUBMIT', configData.get('UI_NAME'))
        self.assertEqual('OpenCue Submit', configData.get('SUBMIT_APP_WINDOW_TITLE'))
        self.assertEqual(None, configData.get('SOME_UNKNOWN_SETTING'))

    @mock.patch('platform.system', new=mock.Mock(return_value='Linux'))
    @mock.patch('os.path.expanduser', new=mock.Mock(return_value='/home/username'))
    def test__should_load_config_from_user_profile(self):
        config_file_path = '/home/username/.config/opencue/cuesubmit.yaml'
        self.fs.create_file(config_file_path, contents=CONFIG_YAML)

        configData = cuesubmit.Config.getConfigValues()

        self.assertEqual('OPENCUESUBMIT', configData.get('UI_NAME'))
        self.assertEqual('OpenCue Submit', configData.get('SUBMIT_APP_WINDOW_TITLE'))
        self.assertEqual(None, configData.get('SOME_UNKNOWN_SETTING'))

    def test__should_fail_on_invalid_yaml(self):
        config_file_path = '/path/to/config.yaml'
        self.fs.create_file(config_file_path, contents=CONFIG_YAML_INVALID)
        os.environ['CUESUBMIT_CONFIG_FILE'] = config_file_path

        with self.assertRaises(cuesubmit.Config.CuesubmitConfigError):
            cuesubmit.Config.getConfigValues()


if __name__ == '__main__':
    unittest.main()
