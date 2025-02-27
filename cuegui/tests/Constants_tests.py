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


"""Tests for cuegui.Constants"""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import importlib
import os

import mock
import pyfakefs.fake_filesystem_unittest

import cuegui.Constants


CONFIG_YAML = '''
unused_setting: some value
version: 98.707.68
refresh.job_update_delay: 30000

logger.level: INFO
'''


# pylint: disable=import-outside-toplevel,redefined-outer-name,reimported
class ConstantsTests(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.fs.add_real_file(
            os.path.join(os.path.dirname(cuegui.__file__), 'config', 'cuegui.yaml'), read_only=True)
        if 'CUEGUI_CONFIG_FILE' in os.environ:
            del os.environ['CUEGUI_CONFIG_FILE']

    def test__should_load_user_config_from_env_var(self):
        config_file_path = '/path/to/config.yaml'
        self.fs.create_file(config_file_path, contents=CONFIG_YAML)
        os.environ['CUEGUI_CONFIG_FILE'] = config_file_path

        import cuegui.Constants
        result = importlib.reload(cuegui.Constants)

        self.assertEqual('98.707.68', result.VERSION)
        self.assertEqual(30000, result.JOB_UPDATE_DELAY)
        self.assertEqual(10000, result.LAYER_UPDATE_DELAY)

    @mock.patch('platform.system', new=mock.Mock(return_value='Linux'))
    @mock.patch('os.path.expanduser', new=mock.Mock(return_value='/home/username'))
    def test__should_load_user_config_from_user_profile(self):
        config_file_path = '/home/username/.config/opencue/cuegui.yaml'
        self.fs.create_file(config_file_path, contents=CONFIG_YAML)

        import cuegui.Constants
        result = importlib.reload(cuegui.Constants)

        self.assertEqual('98.707.68', result.VERSION)
        self.assertEqual(30000, result.JOB_UPDATE_DELAY)
        self.assertEqual(10000, result.LAYER_UPDATE_DELAY)

    @mock.patch('platform.system', new=mock.Mock(return_value='Darwin'))
    def test__should_use_mac_editor(self):
        import cuegui.Constants
        result = importlib.reload(cuegui.Constants)

        self.assertEqual('open -t', result.DEFAULT_EDITOR)
