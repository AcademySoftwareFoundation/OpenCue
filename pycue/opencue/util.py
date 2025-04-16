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

"""Utility methods used throughout the opencue module."""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
import functools
import future.utils
import logging
import os
import time

import grpc

import opencue

logger = logging.getLogger('opencue')


def grpcExceptionParser(grpcFunc):
    """Decorator to wrap functions making GRPC calls.
    Attempts to throw the appropriate exception based on grpc status code."""
    def _decorator(*args, **kwargs):
        triesRemaining = opencue.exception.getRetryCount() + 1
        while triesRemaining > 0:
            triesRemaining -= 1
            try:
                return grpcFunc(*args, **kwargs)
            except grpc.RpcError as exc:
                # pylint: disable=no-member
                code = exc.code()
                details = exc.details() or "No details found. Check server logs."
                # pylint: enable=no-member
                exception = opencue.exception.EXCEPTION_MAP.get(code)
                if exception:
                    if exception.retryable and triesRemaining >= 1:
                        logger.warning(exception.retryMsg)
                        time.sleep(exception.retryBackoff)
                    else:
                        future.utils.raise_with_traceback(
                            exception(exception.failMsg.format(details=details)))
                else:
                    future.utils.raise_with_traceback(opencue.exception.CueException(
                        "Encountered a server error. {code} : {details}".format(
                            code=code, details=details)))

    return functools.wraps(grpcFunc)(_decorator)


# pylint: disable=redefined-builtin
def id(value):
    """extract(entity)
    extracts a string unique ID from a opencue entity or
    list of opencue entities.
    """
    def _extract(item):
        try:
            return item.id()
        # pylint: disable=bare-except
        except:
            pass
        return item

    if isinstance(value, (tuple, list, set)):
        return [_extract(v) for v in value]
    return _extract(value)


@grpcExceptionParser
def proxy(idOrObject, cls):
    """Helper function for getting proto objects back from Cuebot.

    :type  idOrObject: str, list<str>, protobuf Message, list<protobuf Message>
    :param idOrObject: The id/item, or list of ids/items to look up
    :type cls: str
    :param cls: The Name of the protobuf message class to use.
    :rtype:  protobuf Message or list
    :return: Cue object or list of objects"""
    def _proxy(idString):
        proto = opencue.Cuebot.PROTO_MAP.get(cls.lower())
        if proto:
            requestor = getattr(proto, "{cls}Get{cls}Request".format(cls=cls))
            getMethod = getattr(opencue.Cuebot.getStub(cls.lower()), "Get{}".format(cls))
            return getMethod(requestor(id=idString))
        raise AttributeError('Could not find a proto for {}'.format(cls))

    def _proxies(entities):
        messages = []
        for item in entities:
            if hasattr(item, 'id'):
                messages.append(_proxy(item.id))
            else:
                messages.append(_proxy(item))
        return messages

    if hasattr(idOrObject, 'id'):
        return _proxy(idOrObject.id)
    if isinstance(idOrObject, str):
        return _proxy(idOrObject)
    return _proxies(idOrObject)


def rep(entity):
    """rep(entity)
    Extracts a string representation of a opencue entity"""
    try:
        return entity.name
    # pylint: disable=bare-except
    except:
        return str(entity)


def logPath(job, frame=None):
    """logPath(job, frame=None)
        Extracts the log path from a job or a job/frame
    """
    if frame:
        return os.path.join(job.data.log_dir, "%s.%s.rqlog" % (job.data.name, frame.data.name))
    return job.data.log_dir
