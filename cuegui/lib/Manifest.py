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


## imports the libary's default configurtion
import os
import sys
import time

QT5_VERSION = "5.11.2"

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import Cue3

import FileSequence

import Constants
import yaml
CueConfig = yaml.load(open(Constants.DEFAULT_YAML).read())
