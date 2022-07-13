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


"""Tests for cuegui.Config"""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import shutil
import tempfile
import unittest

from PySide2 import QtCore

import cuegui.Config


CONFIG_INI = '''
[General]
Version=0.14

[CueCommander]
Open=true
Title=CustomWindowTitle
OtherAttr=arbitrary-value
'''

CONFIG_WITH_RESTORE_FLAG = '''
[General]
Version=0.14
RevertLayout=true

[CueCommander]
OtherAttr=arbitrary-value
'''


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.config_dir = tempfile.mkdtemp()
        QtCore.QSettings.setPath(
            QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, self.config_dir)

    def tearDown(self):
        shutil.rmtree(self.config_dir)

    def test__should_load_user_config(self):
        app_name = 'arbitraryapp'
        config_file_path = os.path.join(self.config_dir, '.%s' % app_name, 'config.ini')
        os.mkdir(os.path.dirname(config_file_path))
        with open(config_file_path, 'w') as fp:
            fp.write(CONFIG_INI)

        settings = cuegui.Config.startup(app_name)

        self.assertEqual('0.14', settings.value('Version'))
        self.assertEqual('true', settings.value('CueCommander/Open'))
        self.assertEqual('CustomWindowTitle', settings.value('CueCommander/Title'))
        self.assertEqual('arbitrary-value', settings.value('CueCommander/OtherAttr'))

    def test__should_load_default_config(self):
        settings = cuegui.Config.startup('CueCommander')

        self.assertEqual('false', settings.value('CueCommander/Open'))
        self.assertEqual('CueCommander', settings.value('CueCommander/Title'))
        self.assertFalse(settings.value('CueCommander/OtherAttr', False))

    def test__should_restore_default_config(self):
        config_file_path = os.path.join(self.config_dir, '.cuecommander', 'config.ini')
        os.mkdir(os.path.dirname(config_file_path))
        with open(config_file_path, 'w') as fp:
            fp.write(CONFIG_WITH_RESTORE_FLAG)

        settings = cuegui.Config.startup('CueCommander')

        self.assertEqual('false', settings.value('CueCommander/Open'))
        self.assertEqual('CueCommander', settings.value('CueCommander/Title'))
        self.assertFalse(settings.value('CueCommander/OtherAttr', False))
