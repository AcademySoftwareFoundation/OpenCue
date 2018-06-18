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
import sys

# This is a hack to allow plugins to work by replacing
# the proprietary SPI import library
path = os.path.realpath(os.path.dirname(__file__))
mod = path.split('/')[-1]
parent = os.path.dirname(path)
sys.path.insert(0, parent)
Cue3Gui = __import__(mod)
sys.modules['Cue3Gui'] = Cue3Gui

from Manifest import *

import Main

from AbstractDockWidget import AbstractDockWidget
from AbstractTreeWidget import AbstractTreeWidget
from AbstractWidgetItem import AbstractWidgetItem

import ApplicationConfig
import BugReportDialog
import Comments
import Constants
import EmailDialog
import ShowDialog
import FrameRangeSelection
import MiscDialog

from MenuActions import MenuActions
from HostMonitor import HostMonitor
from HostMonitorTree import HostMonitorTree
from ProcMonitor import ProcMonitor
from ProcMonitorTree import ProcMonitorTree
from CueJobMonitorTree import CueJobMonitorTree
from JobMonitorTree import JobMonitorTree
from LayerMonitorTree import LayerMonitorTree
from FrameMonitor import FrameMonitor
from FrameMonitorTree import FrameMonitorTree
from SubscriptionsWidget import SubscriptionsWidget
from ShowsWidget import ShowsWidget
from GraphSubscriptionsWidget import GraphSubscriptionsWidget
from CueStateBarWidget import CueStateBarWidget
from Plugins import Plugin
from Redirect import RedirectWidget
from ServiceDialog import *

import Style
import ThreadPool
import Utils
