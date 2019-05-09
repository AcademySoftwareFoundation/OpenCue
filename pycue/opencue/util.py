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
Module: util.py
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
from future.utils import raise_from
import functools
import grpc
import logging
import os
import six

import opencue

logger = logging.getLogger('opencue')


def grpcExceptionParser(grpcFunc):
    """Decorator to wrap functions making GRPC calls.
    Attempts to throw the appropriate exception based on grpc status code."""
    def _decorator(*args, **kwargs):
        try:
            return grpcFunc(*args, **kwargs)
        except grpc.RpcError as exc:
            code = exc.code()
            details = exc.details() or "No details found. Check server logs."
            if code == grpc.StatusCode.NOT_FOUND:
                raise_from(opencue.exception.EntityNotFoundException(
                    "Object does not exist. {}".format(details)), exc)
            elif code == grpc.StatusCode.ALREADY_EXISTS:
                raise_from(opencue.exception.EntityAlreadyExistsException(
                    "Object already exists. {}".format(details)), exc)
            elif code == grpc.StatusCode.DEADLINE_EXCEEDED:
                raise_from(opencue.exception.DeadlineExceededException(
                    "Request deadline exceeded. {}".format(details)), exc)
            elif code == grpc.StatusCode.INTERNAL:
                raise_from(opencue.exception.CueInternalErrorException(
                    "Server caught an internal exception. {}".format(details)), exc)
            else:
                raise_from(opencue.exception.CueException(
                    "Encountered a server error. {code} : {details}".format(
                        code=code, details=details)), exc)
    return functools.wraps(grpcFunc)(_decorator)


def id(value):
    """extract(entity)
    extracts a string unique ID from a opencue entity or
    list of opencue entities.
    """
    def _extract(item):
        try:
            return item.id()
        except:
            pass
        return item

    if isinstance(value, (tuple, list, set)):
        return [_extract(v) for v in value]
    else:
        return _extract(value)


@grpcExceptionParser
def proxy(idOrObject, cls):
    """Helper function for getting proto objects back from Cuebot.
    @type  idOrObject: str, list<str>, protobuf Message, list<protobuf Message>
    @param idOrObject: The id/item, or list of ids/items to look up
    @type cls: str
    @param cls: The Name of the protobuf message class to use.
    @rtype:  protobuf Message or list
    @return: Cue object or list of objects"""
    def _proxy(idString):
        proto = opencue.Cuebot.PROTO_MAP.get(cls.lower())
        if proto:
            requestor = getattr(proto, "{cls}Get{cls}Request".format(cls=cls))
            getMethod = getattr(opencue.Cuebot.getStub(cls.lower()), "Get{}".format(cls))
            return getMethod(requestor(id=idString))
        else:
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
    elif isinstance(idOrObject, six.string_types):
        return _proxy(idOrObject)
    else:
        return _proxies(idOrObject)


def rep(entity):
    """rep(entity)
    Extracts a string repesentation of a opencue entity"""
    try:
        return entity.name
    except:
        return str(entity)


def logPath(job, frame=None):
    """logPath(job, frame=None)
        Extracts the log path from a job or a job/frame
    """
    if frame:
        return os.path.join(job.data.log_dir, "%s.%s.rqlog" % (job.data.name, frame.data.name))
    else:
        return job.data.log_dir
