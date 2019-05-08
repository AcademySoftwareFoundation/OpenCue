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

import os
from setuptools import find_packages
from setuptools import setup

pyoutline_dir = os.path.abspath(os.path.dirname(__file__))

version = 'unknown'
possible_version_paths = [
    os.path.join(pyoutline_dir, 'VERSION'),
    os.path.join(os.path.dirname(pyoutline_dir), 'VERSION'),
]
for possible_version_path in possible_version_paths:
    if os.path.exists(possible_version_path):
        with open(possible_version_path) as fp:
            version = fp.read().strip()

with open(os.path.join(pyoutline_dir, 'README.md')) as fp:
    long_description = fp.read()

setup(
    name='pyoutline',
    version=version,
    description='The OpenCue PyOutline library',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/imageworks/OpenCue',
    classifiers=[
        'License :: OSI Approved :: Apache Software License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    packages=find_packages(exclude=['tests']),
    data_files=[
        ('bin', ['bin/cuerunbase.py', 'bin/pycuerun', 'bin/util_qc_job_layer.py']),
        ('etc', ['etc/outline.cfg']),
        ('wrappers', ['wrappers/opencue_wrap_frame', 'wrappers/opencue_wrap_frame_no_ss', 'wrappers/local_wrap_frame']),
    ],
    test_suite='tests',
)
