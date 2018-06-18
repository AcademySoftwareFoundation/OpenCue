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

QT4_VERSION = "4.4.3"

import PyQt4.QtCore as QtCore
import PyQt4.QtGui as QtGui
import PyQt4.Qt as Qt

import Cue3

import FileSequence

import Constants
import yaml
CueConfig = yaml.load(open(Constants.DEFAULT_YAML).read())
