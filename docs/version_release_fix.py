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

import os,re
from pathlib import Path

conf_py = Path('./conf.py')
version_in = Path('../VERSION.in')

with open(conf_py, 'r') as f:
    old_file = f.read()

# Get version and release
version = open(version_in, 'r').readline().strip()
release = str(os.popen('git describe --tags').read()).strip()

# Update version
new_file = re.sub(r"version = u'[0-9.]+'", \
	f"version = u'{version}'", old_file)

# Update release
new_file = re.sub(r"release = u'[0-9.]+'", \
	f"release = u'{release}'", new_file)

with open(conf_py, 'w') as f:
    f.write(new_file)