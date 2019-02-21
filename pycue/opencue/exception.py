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
Project: opencue Library

Module: exception.py - Provides opencue access to exceptions
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import


class CueException(Exception):
    """A Base class for all client side cue exceptions"""
    pass


class DeadlineExceededException(CueException):
    """Raised when the deadline for response has been exceeded."""
    pass


class EntityAlreadyExistsException(CueException):
    """Raised when the entity was not created because it already exists on the server"""
    pass


class EntityNotFoundException(CueException):
    """Raised when the entity was not found on the server."""
    pass


class CueInternalErrorException(CueException):
    """Raised when the server encountered a catchable error"""
    pass
