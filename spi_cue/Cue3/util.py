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

import Ice
from cuebot import Cuebot
import os

logger = logging.getLogger('cue3')

def id(value):
    """extract(entity)
    extracts a string unique ID from a Cue3 entity or
    list of Cue3 entities.
    """
    def _extract(item):
        try:
            return item.ice_getIdentity().name
        except:
            pass
        try:
            return item.proxy.ice_getIdentity().name
        except:
            pass
        return item

    if isinstance(value, (tuple, list, set)):
        return [_extract(v) for v in value]
    else:
        return _extract(value)

def proxy(item, cls=None):
    """proxy(entity)
    Extracts a proxy out of an Cue3 entity.  If you have
    the unique ID, pass in the optional class name to create
    a proxy.
    """
    def _proxy(entity, cls=None):
        try:
            return entity.proxy
        except:
            pass

        if hasattr(entity, "ice_toString"):
            return entity

        if not cls:
            raise ValueError("Unable to extract proxy from %s try passing in a class name." % entity)

        cls = cls.title()
        return Cuebot.buildProxy("%sInterface" % cls, "manage%s/%s" % (cls, entity))

    if isinstance(item, (tuple, list, set)):
        return [_proxy(i, cls) for i in item]
    else:
        return _proxy(item, cls)

def rep(entity):
    """rep(entity)
    Extracts a string repesentation of a Cue3 entity"""
    try:
        return entity.data.name
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

def _loadWrappers():
    import wrappers
    try:
        Cuebot.register(wrappers.job.Job, "::CueClientIce::Job")
        Cuebot.register(wrappers.comment.Comment, "::CueClientIce::Comment")
        Cuebot.register(wrappers.job.NestedJob, "::CueClientIce::NestedJob")
        Cuebot.register(wrappers.group.Group, "::CueClientIce::Group")
        Cuebot.register(wrappers.group.NestedGroup, "::CueClientIce::NestedGroup")
        Cuebot.register(wrappers.layer.Layer, "::CueClientIce::Layer")
        Cuebot.register(wrappers.frame.Frame, "::CueClientIce::Frame")
        Cuebot.register(wrappers.host.Host, "::CueClientIce::Host")
        Cuebot.register(wrappers.host.NestedHost, "::CueClientIce::NestedHost")
        Cuebot.register(wrappers.proc.Proc, "::CueClientIce::Proc ")
        Cuebot.register(wrappers.proc.NestedProc, "::CueClientIce::NestedProc")
        Cuebot.register(wrappers.show.Show, "::CueClientIce::Show")
        Cuebot.register(wrappers.task.Task, "::CueClientIce::Task")
        Cuebot.register(wrappers.depend.Depend, "::CueClientIce::Depend")
        Cuebot.register(wrappers.filter.Filter, "::CueClientIce::Filter")
        Cuebot.register(wrappers.filter.Action, "::CueClientIce::Action")
        Cuebot.register(wrappers.filter.Matcher, "::CueClientIce::Matcher")
        Cuebot.register(wrappers.allocation.Allocation, "::CueClientIce::Allocation")
        Cuebot.register(wrappers.subscription.Subscription, "::CueClientIce::Subscription")
    except Ice.AlreadyRegisteredException:
        msg = 'Cue3 wrappers has already been registered, skipping.'
        print(msg)
        logger.warn(msg)

def loadWrappers():
    """
    loadWrappers
    @deprecated
    """
    msg = 'Cue3.loadWrappers has been deprecated. Wrappers are loaded automatically and does not require manual load'
    print(msg)
    logger.warn(msg)

