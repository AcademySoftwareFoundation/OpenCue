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



import os, setuptools, sys

# Only insert spi_cue3.version module to path
modulePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'spi_cue3')
sys.path.insert(0, modulePath)
from version import version
sys.path.remove(modulePath)


setuptools.setup(
    name='spi_cue3',
    # packages=['spi_cue3', 'spi_cue3.libice', 'spi_cue3.wrappers'],
    package_dir={'spi_cue3':'spi_cue3'},
    packages=setuptools.find_packages(),
    include_package_data=True,
    version=version,
    description='SPI Cue3 Python API sdk',
    maintainer='',
    maintainer_email='',
    url='',
    download_url='',
    keywords=['cue3', 'api'],
    classifiers=[],
    install_requires=['pyyaml'],
    long_description=open('README.md').read()
)

