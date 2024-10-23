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
# pylint: disable=missing-function-docstring,missing-module-docstring

import unittest

def create_test_suite():
    loader = unittest.TestLoader()
    start_dir = '.'  # Specify the directory where your test files reside
    suite = loader.discover(start_dir, pattern='*_tests.py')
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    test_suite = create_test_suite()
    runner.run(test_suite)
