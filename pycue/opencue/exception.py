#  Copyright Contributors to the OpenCue Project
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

"""Custom exception classes for API error handling."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import grpc

import opencue


class CueException(Exception):
    """A Base class for all client side cue exceptions"""
    failMsg = 'Caught an unknown server exception. Please check the server logs. {details}'
    retryMsg = 'Caught an unknown server exception, checking again...'
    retryable = False
    retryBackoff = 0.5  # seconds


class DeadlineExceededException(CueException):
    """Raised when the deadline for response has been exceeded."""
    failMsg = 'Request deadline exceeded. {details}'
    retryMsg = 'Request deadline exceeded, checking again...'


class EntityAlreadyExistsException(CueException):
    """Raised when the entity was not created because it already exists on the server"""
    failMsg = 'Object already exists. {details}'
    retryMsg = 'Object already exists, checking again...'


class EntityNotFoundException(CueException):
    """Raised when the entity was not found on the server."""
    failMsg = 'Object does not exist. {details}'
    retryMsg = 'Object does not exist, checking again...'


class CueInternalErrorException(CueException):
    """Raised when the server encountered a catchable error"""
    failMsg = 'Server caught an internal exception. {details}'
    retryMsg = 'Server caught an internal exception, checking again...'


class ConnectionException(CueException):
    """Raised when unable to connect to grpc server."""
    failMsg = 'Unable to contact grpc server. {details}'
    retryMsg = 'Unable to contact grpc server, checking again...'
    retryable = True


def getRetryCount():
    """Return the configured number of retries a cuebot call can make.
    If not specified in the config, all retryable calls will be called once and retried 3 times."""
    return opencue.cuebot.Cuebot.getConfig().get('cuebot.exception_retries', 3)


EXCEPTION_MAP = {
    grpc.StatusCode.NOT_FOUND: EntityNotFoundException,
    grpc.StatusCode.ALREADY_EXISTS: EntityAlreadyExistsException,
    grpc.StatusCode.DEADLINE_EXCEEDED: DeadlineExceededException,
    grpc.StatusCode.INTERNAL: CueInternalErrorException,
    grpc.StatusCode.UNAVAILABLE: ConnectionException
}
