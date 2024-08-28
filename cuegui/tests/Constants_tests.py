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
from qtpy import QtGui

import opencue
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

    @mock.patch('platform.system', new=mock.Mock(return_value='Linux'))
    def test__should_use_default_values(self):
        import cuegui.Constants
        result = importlib.reload(cuegui.Constants)

        self.assertNotEqual('98.707.68', result.VERSION)
        self.assertEqual(0, result.STARTUP_NOTICE_DATE)
        self.assertEqual('', result.STARTUP_NOTICE_MSG)
        self.assertEqual(10000, result.JOB_UPDATE_DELAY)
        self.assertEqual(10000, result.LAYER_UPDATE_DELAY)
        self.assertEqual(10000, result.FRAME_UPDATE_DELAY)
        self.assertEqual(20000, result.HOST_UPDATE_DELAY)
        self.assertEqual(1000, result.AFTER_ACTION_UPDATE_DELAY)
        self.assertEqual(5, result.MINIMUM_UPDATE_INTERVAL)
        self.assertEqual('Luxi Sans', result.FONT_FAMILY)
        self.assertEqual(10, result.FONT_SIZE)
        self.assertEqual(
            os.path.join(os.path.dirname(cuegui.__file__), 'images'), result.RESOURCE_PATH)
        self.assertEqual(
            os.path.join(os.path.dirname(cuegui.__file__), 'config'), result.CONFIG_PATH)
        self.assertEqual(
            os.path.join(os.path.dirname(cuegui.__file__), 'config'), result.DEFAULT_INI_PATH)
        self.assertEqual(
            [os.path.join(os.path.dirname(cuegui.__file__), 'plugins')],
            result.DEFAULT_PLUGIN_PATHS)
        self.assertEqual('%(levelname)-9s %(module)-10s %(message)s', result.LOGGER_FORMAT)
        self.assertEqual('WARNING', result.LOGGER_LEVEL)
        self.assertEqual('cuemail: please check ', result.EMAIL_SUBJECT_PREFIX)
        self.assertEqual('Your Support Team requests that you check ', result.EMAIL_BODY_PREFIX)
        self.assertEqual('\n\n', result.EMAIL_BODY_SUFFIX)
        self.assertEqual('your.domain.com', result.EMAIL_DOMAIN)
        self.assertEqual(
            'https://github.com/AcademySoftwareFoundation/OpenCue/issues/new',
            result.GITHUB_CREATE_ISSUE_URL)
        self.assertEqual('https://www.opencue.io/docs/', result.URL_USERGUIDE)
        self.assertEqual(
            'https://github.com/AcademySoftwareFoundation/OpenCue/issues/new'
            '?labels=enhancement&template=enhancement.md', result.URL_SUGGESTION)
        self.assertEqual(
            'https://github.com/AcademySoftwareFoundation/OpenCue/issues/new'
            '?labels=bug&template=bug_report.md', result.URL_BUG)
        self.assertEqual(
            'gview -R -m -M -U %s +' % os.path.join(
                os.path.dirname(cuegui.__file__), 'config', 'gvimrc'),
            result.DEFAULT_EDITOR)
        self.assertEqual({
            'rhel7': '/shots',
            'linux': '/shots',
            'windows': 'S:',
            'mac': '/Users/shots',
            'darwin': '/Users/shots',
        }, result.LOG_ROOT_OS)
        self.assertEqual((
            'general', 'desktop', 'playblast', 'util', 'preprocess', 'wan', 'cuda', 'splathw',
            'naiad', 'massive'), result.ALLOWED_TAGS)
        self.assertEqual(
            os.path.join(os.path.dirname(cuegui.__file__), 'config', 'darkpalette.qss'),
            result.DARK_STYLE_SHEET)
        self.assertEqual('plastique', result.COLOR_THEME)
        self.assertEqual(QtGui.QColor(50, 50, 100), result.COLOR_USER_1)
        self.assertEqual(QtGui.QColor(100, 100, 50), result.COLOR_USER_2)
        self.assertEqual(QtGui.QColor(0, 50, 0), result.COLOR_USER_3)
        self.assertEqual(QtGui.QColor(50, 30, 00), result.COLOR_USER_4)
        self.assertEqual({
            opencue.api.job_pb2.DEAD: QtGui.QColor(255, 0, 0),
            opencue.api.job_pb2.DEPEND: QtGui.QColor(160, 32, 240),
            opencue.api.job_pb2.EATEN: QtGui.QColor(150, 0, 0),
            opencue.api.job_pb2.RUNNING: QtGui.QColor(200, 200, 55),
            opencue.api.job_pb2.SETUP: QtGui.QColor(160, 32, 240),
            opencue.api.job_pb2.SUCCEEDED: QtGui.QColor(55, 200, 55),
            opencue.api.job_pb2.WAITING: QtGui.QColor(135, 207, 235),
            opencue.api.job_pb2.CHECKPOINT: QtGui.QColor(61, 98, 247),
        }, result.RGB_FRAME_STATE)
        self.assertEqual(5242880, result.MEMORY_WARNING_LEVEL)
        self.assertEqual(
            ['error', 'aborted', 'fatal', 'failed', 'killed', 'command not found',
             'no licenses could be found', 'killMessage'], result.LOG_HIGHLIGHT_ERROR)
        self.assertEqual(['warning', 'not found'], result.LOG_HIGHLIGHT_WARN)
        self.assertEqual(['info:', 'rqd cmd:'], result.LOG_HIGHLIGHT_INFO)
        self.assertEqual(2147483647, result.QT_MAX_INT)
        self.assertEqual({
            'max_cores': 32,
            'max_gpu_memory': 128,
            'max_gpus': 8,
            'max_memory': 128,
            'max_proc_hour_cutoff': 30,
            'redirect_wasted_cores_threshold': 100,
        }, result.RESOURCE_LIMITS)

    @mock.patch('platform.system', new=mock.Mock(return_value='Darwin'))
    def test__should_use_mac_editor(self):
        import cuegui.Constants
        result = importlib.reload(cuegui.Constants)

        self.assertEqual('open -t', result.DEFAULT_EDITOR)
