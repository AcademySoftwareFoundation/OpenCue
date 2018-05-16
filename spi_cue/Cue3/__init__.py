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



import sys
import os
import logging

import ice_loader
ice_loader.load_ice()
del ice_loader

import Ice
from Ice import ObjectNotExistException, UnknownLocalException, \
                ConnectionRefusedException, UnknownException

slice_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'slice'))

slice_path = "--all -I{path}/cue/ "\
             "-I{path}/spi/ "\
             "{path}/cue/cue_ice.ice "\
             "{path}/cue/cue_client.ice "\
             "{path}/cue/cue_types.ice " \
             "{path}/spi/spi_search_criteria.ice".format(path=slice_dir)

Ice.loadSlice(slice_path)

from cuebot import Cuebot

Cuebot.init()


import cue.CueClientIce as Entity

import spi.SpiIce as SpiIce

from api import *
from cue.CueClientIce import CommentData
from cue.CueIce import *

class __NullHandler(logging.Handler):
    def emit(self, record):
        pass

__logger = logging.getLogger("cue3")
__logger.addHandler(__NullHandler())

from util import _loadWrappers
_loadWrappers()

