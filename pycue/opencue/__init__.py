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


import logging

from cuebot import Cuebot

Cuebot.init()

import api
import wrappers
import search

from exception import CueException
from exception import EntityNotFoundException
from util import id
from util import logPath
from util import proxy
from util import rep


class __NullHandler(logging.Handler):
    def emit(self, record):
        pass


__logger = logging.getLogger("opencue")
__logger.addHandler(__NullHandler())
