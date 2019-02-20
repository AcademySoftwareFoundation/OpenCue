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


"""
Allows the creation of a logger.
"""


import logging

import Constants


__loggerFormat = logging.Formatter(Constants.LOGGER_FORMAT)
loggerStream = logging.StreamHandler()
loggerStream.setLevel(getattr(logging, Constants.LOGGER_LEVEL))
loggerStream.setFormatter(__loggerFormat)


def getLogger(name):
    """Returns or creates and returns a logger of the given name.
    @param name: The name of this logging handler
    @type  name: string
    @return: The new handler
    @rtype:  Handler"""
    logger = logging.getLogger(name)
    logger.addHandler(loggerStream)

    return logger
