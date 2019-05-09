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
import logging
import os
from functools import wraps
from six import string_types

from . import exception
import grpc
from opencue import Cuebot

logger = logging.getLogger('opencue')


def grpcExceptionParser(grpcFunc):
    """"""
    def _decorator(*args, **kwargs):
        try:
            return grpcFunc(*args, **kwargs)
        except grpc.RpcError as e:
            code = e.code()
            details = e.details() or "No details found. Check server logs."
            if code == grpc.StatusCode.NOT_FOUND:
                raise exception.EntityNotFoundException("Object does not exist. {}".format(details))
            elif code == grpc.StatusCode.ALREADY_EXISTS:
                raise exception.EntityAlreadyExistsException("Object already exists. {}"
                                                             .format(details))
            elif code == grpc.StatusCode.DEADLINE_EXCEEDED:
                raise exception.DeadlineExceededException("Request deadline exceeded. {}"
                                                          .format(details))
            elif code == grpc.StatusCode.INTERNAL:
                raise exception.CueInternalErrorException("Server caught an internal exception. {}"
                                                          .format(details))
            else:
                raise exception.CueException("Encountered a server error. {code} : {details}"
                                             .format(code=code, details=details))
    return wraps(grpcFunc)(_decorator)


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


def proxy(item, cls=None):
    """Helper function for getting proto objects back from Cuebot.
    @type  item: str, list<str>, protobuf Message, list<protobuf Message>
    @param item: The id/item, or list of ids/items to look up
    @type cls: str
    @param cls: The Name of the protobuf message class to use.
    @rtype:  protobuf Message or list
    @return: Cue object or list of objects
     """
    if cls is None:
        raise ValueError("cls must be specified")

    if isinstance(item, string_types):
        return getProtoFromIdAndClass(item, cls)

    elif hasattr(item, 'id'):
        return getProtoFromIdAndClass(item.id, cls)

    else:
        try:
            return getProtosFromItems(item, cls)
        except TypeError as e:
            logger.error('Cannot get rpc object of type {}. Allowed types are: '
                         'String, List<String>, protobuf object, List<protobuf object>'.format(
                              item.__class__))
            raise e


@grpcExceptionParser
def getProtoFromIdAndClass(id, cls):
    """Given an id and proto class name, return the full object from Cuebot."""
    getMethod = getattr(Cuebot.getStub(cls.lower()), "Get{}".format(cls))
    proto = Cuebot.PROTO_MAP.get(cls.lower())
    if proto:
        requestor = getattr(proto, "{cls}Get{cls}Request".format(cls=cls))
    else:
        raise AttributeError('Could not find a proto class object for {}'.format(cls))
    return getMethod(requestor(id=id))


def getProtosFromItems(items, cls):
    """Given a list of ids or items with ids, and their class name,
    return a list of objects from Cuebot"""
    protos = []
    for item in items:
        if isinstance(item, string_types):
            protos.append(getProtoFromIdAndClass(item, cls))
        else:
            if hasattr(item, 'id'):
                protos.append(getProtoFromIdAndClass(item.id, cls))
            else:
                raise ValueError("Could not get id from object {}".format(item))
    return protos


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
