#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import tempfile
import unittest

import cuesubmit.Config


CONFIG_YAML = b'''
# Some comment
UI_NAME : "OPENCUESUBMIT"
SUBMIT_APP_WINDOW_TITLE : "OpenCue Submit"
'''

CONFIG_YAML_INVALID = b' " some text in an unclosed quote'


class ConfigTests(unittest.TestCase):

    def testGetConfigValues(self):
        with tempfile.NamedTemporaryFile() as fp:
            fp.write(CONFIG_YAML)
            fp.flush()
            os.environ[cuesubmit.Config.CONFIG_FILE_ENV_VAR] = fp.name

            configData = cuesubmit.Config.getConfigValues()

            self.assertEqual('OPENCUESUBMIT', configData.get('UI_NAME'))
            self.assertEqual('OpenCue Submit', configData.get('SUBMIT_APP_WINDOW_TITLE'))
            self.assertEqual(None, configData.get('SOME_UNKNOWN_SETTING'))

    def testFailOnInvalidYaml(self):
        with tempfile.NamedTemporaryFile() as fp:
            fp.write(CONFIG_YAML_INVALID)
            fp.flush()
            os.environ[cuesubmit.Config.CONFIG_FILE_ENV_VAR] = fp.name

            with self.assertRaises(cuesubmit.Config.CuesubmitConfigError):
                cuesubmit.Config.getConfigValues()


if __name__ == '__main__':
    unittest.main()
