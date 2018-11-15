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
Project: Cue3 Library
Module: util.py
"""

import logging
import os

from google.protobuf.pyext._message import RepeatedCompositeContainer
from Cue3 import Cuebot

logger = logging.getLogger('cue3')


def id(value):
    """extract(entity)
    extracts a string unique ID from a Cue3 entity or
    list of Cue3 entities.
    """
    def _extract(item):
        try:
            return item.id
        except:
            pass
        return item

    if isinstance(value, (tuple, list, set)):
        return [_extract(v) for v in value]
    else:
        return _extract(value)


def proxy(item, cls=None):
    """Lookup a rpc object from its id and cls"""
    def _proxy(entity, cls=None):
        if cls is None:
            raise ValueError("cls must be specified")
        stub = Cuebot.getStub(cls.lower())
        getMethod = getattr(stub, "Get{}".format(cls))
        proto = Cuebot.PROTO_MAP.get(cls.lower())
        if proto:
            requestor = getattr(proto, "{cls}Get{cls}Request".format(cls=cls))
            return getMethod(requestor(id=entity))
        else:
            raise AttributeError('Could not find a proto for {}'.format(cls))

    if isinstance(item, (tuple, list, set, RepeatedCompositeContainer)):
        return [_proxy(i, cls) for i in item]
    else:
        return _proxy(item, cls)


def rep(entity):
    """rep(entity)
    Extracts a string repesentation of a Cue3 entity"""
    try:
        return entity.name
    except:
        return str(entity)


def logPath(job, frame=None):
    """logPath(job, frame=None)
        Extracts the log path from a job or a job/frame
    """
    if frame:
        return os.path.join(job.data.logDir, "%s.%s.rqlog" % (job.data.name, frame.data.name))
    else:
        return job.data.logDir
