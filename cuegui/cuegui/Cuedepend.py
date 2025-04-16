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


"""Utility functions for creating depends.

Dependency Types:
    The long and short version of dependency types are valid. In most cases its not required
    to actually specify a dependency type.

    JobOnJob / joj       JobOnLayer / jol       JobOnFrame / jof
    LayerOnJob / loj     LayerOnLayer / lol     LayerOnFrame / lof
    FrameOnJob / foj     FrameOnLayer / fol     FrameOnFrame / fof
    FrameByFrame / fbf   HardDepend / hd
"""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import logging

import opencue
from opencue_proto import depend_pb2


logger = logging.getLogger(__file__)


ERR_INVALID_ON_JOB = (
    "Error, a dependency of this type requires a valid job name to depend on.  See -on-job.")
ERR_INVALID_ON_LAYER = (
    "Error, a dependency of this type requires a valid layer name to depend on. See -on-layer.")
ERR_INVALID_ON_FRAME = (
    "Error, a dependency of this type requires a valid frame name to depend on. See -on-frame.")
ERR_INVALID_ER_JOB = (
    "Error, a dependency of this type requires a valid job name to depend on.  See -job.")
ERR_INVALID_ER_LAYER = (
    "Error, a dependency of this type requires a valid layer name to depend on. See -layer.")
ERR_INVALID_ER_FRAME = (
    "Error, a dependency of this type requires a valid frame name to depend on. See -frame.")


def __is_valid(value, error):
    """Minor depend validation. The gRPC library takes care of everything else."""
    if not value:
        raise ValueError(error)
    if isinstance(value, str) and len(value) < 1:
        raise ValueError(error)


def createDepend(depend_type, job, layer, frame, onjob, onlayer, onframe):
    """Creates a new dependency of the specified type.
    @type  depend_type: string
    @param depend_type: The type of dependency
    @type  job: string
    @param job: The name of the dependant job
    @type  layer: string
    @param layer: The name of the dependant layer
    @type  frame: int
    @param frame: The dependant frame number
    @type  onjob: string
    @param onjob: the name of the job to depend on
    @type  onlayer: string
    @param onlayer: the name of the layer to depend on
    @type  onframe: int
    @param onframe: the number of the frame to depend on
    @rtype:  Depend
    @return: The newly created dependency"""

    if not onjob and not onlayer and not onframe:
        raise ValueError(
            "You must specify something to depend on, see -on-job, -on-layer, -on-frame")

    if not onjob:
        logger.debug("assuming internal depend")
        onjob = job

    typeName = depend_pb2.DependType.Name(depend_type)
    if typeName in ("HARD_DEPEND", "hd"):
        depend = createHardDepend(job, onjob)
    elif typeName in ("JOB_ON_JOB", "joj"):
        depend = createJobOnJobDepend(job, onjob)
    elif typeName in ("JOB_ON_LAYER", "jol"):
        depend = createJobOnLayerDepend(job, onjob, onlayer)
    elif typeName in ("JOB_ON_FRAME", "jof"):
        depend = createJobOnFrameDepend(job, onjob, onlayer, onframe)
    elif typeName in ("LAYER_ON_JOB", "loj"):
        depend = createLayerOnJobDepend(job, layer, onjob)
    elif typeName in ("LAYER_ON_LAYER", "lol"):
        depend = createLayerOnLayerDepend(job, layer, onjob, onlayer)
    elif typeName in ("LAYER_ON_FRAME", "lof"):
        depend = createLayerOnFrameDepend(job, layer, onjob, onlayer, onframe)
    elif typeName in ("FRAME_ON_JOB", "foj"):
        depend = createFrameOnJobDepend(job, layer, frame, onjob)
    elif typeName in ("FRAME_ON_LAYER", "fol"):
        depend = createFrameOnLayerDepend(job, layer, frame, onjob, onlayer)
    elif typeName in ("FRAME_ON_FRAME", "fof"):
        depend = createFrameOnFrameDepend(job, layer, frame, onjob, onlayer, onframe)
    elif typeName in ("FRAME_BY_FRAME", "fbf"):
        depend = createFrameByFrameDepend(job, layer, onjob, onlayer)
    elif typeName in ("LAYER_ON_SIM_FRAME", "los"):
        depend = createLayerOnSimFrameDepend(job, layer, onjob, onlayer, onframe)
    else:
        raise Exception("invalid dependency type: %s" % depend_type)

    return depend


def createHardDepend(job, onjob):
    """Creates a frame by frame dependency for all non-preprocess/refshow layers
    (Hard Depend)
    @type job: string
    @param job: the name of the dependant job
    @type onjob: string
    @param onjob: the name of the job to depend on
    @rtype: list<Depend>
    @return: the created dependency"""

    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(onjob, ERR_INVALID_ON_JOB)

    depends = []

    logger.debug("creating hard depend from %s to %s", job, onjob)
    onLayers = opencue.api.findJob(onjob).getLayers()
    for depend_er_layer in opencue.api.findJob(job).getLayers():
        for depend_on_layer in onLayers:
            if depend_er_layer.data.type == depend_on_layer.data.type:
                depends.append(depend_er_layer.createFrameByFrameDependency(depend_on_layer))
    return depends


def createJobOnJobDepend(job, onjob):
    """Creates a job on job dependency.
    (Soft Depend)
    @type job: string
    @param job: the name of the dependant job
    @type onjob: string
    @param onjob: the name of the job to depend on
    @rtype: Depend
    @return: the created dependency"""
    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(onjob, ERR_INVALID_ON_JOB)

    logger.debug("creating joj depend from %s to %s", job, onjob)
    depend_er_job = opencue.api.findJob(job)
    return depend_er_job.createDependencyOnJob(opencue.api.findJob(onjob))


def createJobOnLayerDepend(job, onjob, onlayer):
    """Creates a job on layer dependency
    @type job: string
    @param job: the name of the dependant job
    @type onjob: string
    @param onjob: the name of the job to depend on
    @type onlayer: string
    @param onlayer: the name of the layer to depend on
    @rtype: Depend
    @return: the created dependency"""
    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(onjob, ERR_INVALID_ON_JOB)
    __is_valid(onlayer, ERR_INVALID_ON_LAYER)

    logger.debug("creating jol depend from %s to %s/%s", job, onjob, onlayer)
    depend_er_job = opencue.api.findJob(job)
    depend_on_layer = opencue.api.findLayer(onjob, onlayer)
    return depend_er_job.createDependencyOnLayer(depend_on_layer)


def createJobOnFrameDepend(job, onjob, onlayer, onframe):
    """Creates a job on frame dependency
    @type job: string
    @param job: the name of the dependant job
    @type onjob: string
    @param onjob: the name of the job to depend on
    @type onlayer: string
    @param onlayer: the name of the layer to depend on
    @type onframe: int
    @param onframe: the number of the frame to depend on
    @rtype: Depend
    @return: the created dependency"""
    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(onjob, ERR_INVALID_ER_JOB)
    __is_valid(onlayer, ERR_INVALID_ON_LAYER)
    __is_valid(onframe, ERR_INVALID_ON_FRAME)

    logger.debug("creating jof depend from %s to %s/%s-%04d", job, onjob, onlayer, onframe)
    depend_er_job = opencue.api.findJob(job)
    depend_on_frame = opencue.api.findFrame(onjob, onlayer, onframe)
    return depend_er_job.createDependencyOnFrame(depend_on_frame)


def createLayerOnJobDepend(job, layer, onjob):
    """Creates a layer on job dependency
    @type job: string
    @param job: the name of the dependant job
    @type layer: string
    @param layer: the name of the dependant layer
    @type onjob: string
    @param onjob: the name of the job to depend on
    @rtype: Depend
    @return: the created dependency"""

    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(layer, ERR_INVALID_ER_LAYER)
    __is_valid(onjob, ERR_INVALID_ON_JOB)

    logger.debug("creating loj depend from %s/%s to %s", job, layer, onjob)
    depend_er_layer = opencue.api.findLayer(job, layer)
    return depend_er_layer.createDependencyOnJob(opencue.api.findJob(onjob))


def createLayerOnLayerDepend(job, layer, onjob, onlayer):
    """Creates a layer on layer dependency
    @type job: string
    @param job: the name of the dependant job
    @type layer: string
    @param layer: the name of the dependant layer
    @type onjob: string
    @param onjob: the name of the job to depend on
    @type onlayer: string
    @param onlayer: the name of the layer to depend on
    @rtype: Depend
    @return: the created dependency"""

    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(layer, ERR_INVALID_ER_LAYER)
    __is_valid(onjob, ERR_INVALID_ON_JOB)
    __is_valid(onlayer, ERR_INVALID_ON_LAYER)

    logger.debug("creating lol depend from %s/%s to %s/%s", job, layer, onjob, onlayer)
    depend_er_layer = opencue.api.findLayer(job,layer)
    depend_on_layer = opencue.api.findLayer(onjob, onlayer)
    return depend_er_layer.createDependencyOnLayer(depend_on_layer)


def createLayerOnFrameDepend(job, layer, onjob, onlayer, onframe):
    """Creates a layer on frame dependency
    @type job: string
    @param job: the name of the dependant job
    @type layer: string
    @param layer: the name of the dependant layer
    @type onjob: string
    @param onjob: the name of the job to depend on
    @type onlayer: string
    @param onlayer: the name of the layer to depend on
    @type onframe: int
    @param onframe: the number of the frame to depend on
    @rtype: Depend
    @return: the created dependency"""

    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(layer, ERR_INVALID_ER_LAYER)
    __is_valid(onjob, ERR_INVALID_ON_JOB)
    __is_valid(onlayer, ERR_INVALID_ON_LAYER)
    __is_valid(onframe, ERR_INVALID_ON_FRAME)

    logger.debug(
        "creating lof depend from %s/%s to %s/%s-%04d", job, layer, onjob, onlayer, onframe)
    depend_er_layer = opencue.api.findLayer(job,layer)
    depend_on_frame = opencue.api.findFrame(onjob, onlayer, onframe)
    return depend_er_layer.createDependencyOnFrame(depend_on_frame)


def createFrameOnJobDepend(job, layer, frame, onjob):
    """Creates a frame on job dependency
    @type job: string
    @param job: the name of the dependant job
    @type layer: string
    @param layer: the name of the dependant layer
    @type frame: int
    @param frame: the number of the dependant frame
    @type onjob: string
    @param onjob: the name of the job to depend on
    @rtype: Depend
    @return: the created dependency"""

    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(layer, ERR_INVALID_ER_LAYER)
    __is_valid(frame, ERR_INVALID_ER_FRAME)
    __is_valid(onjob, ERR_INVALID_ON_JOB)

    logger.debug("creating foj depend from %s/%s-%04d to %s", job, layer, frame, onjob)
    depend_er_frame = opencue.api.findFrame(job, layer, frame)
    return depend_er_frame.createDependencyOnJob(opencue.api.findJob(onjob))


def createFrameOnLayerDepend(job, layer, frame, onjob, onlayer):
    """Creates a frame on layer dependency
    @type job: string
    @param job: the name of the dependant job
    @type layer: string
    @param layer: the name of the dependant layer
    @type frame: int
    @param frame: the number of the dependant frame
    @type onjob: string
    @param onjob: the name of the job to depend on
    @type onlayer: string
    @param onlayer: the name of the layer to depend on
    @rtype: Depend
    @return: the created dependency"""
    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(layer, ERR_INVALID_ER_LAYER)
    __is_valid(frame, ERR_INVALID_ER_FRAME)
    __is_valid(onjob, ERR_INVALID_ON_JOB)
    __is_valid(onlayer, ERR_INVALID_ON_LAYER)

    logger.debug("creating fol depend from %s/%s-%04d to %s/%s", job, layer, frame, onjob, onlayer)
    depend_er_frame = opencue.api.findFrame(job, layer, frame)
    depend_on_layer = opencue.api.findLayer(onjob, onlayer)
    return depend_er_frame.createDependencyOnLayer(depend_on_layer)


def createFrameOnFrameDepend(job, layer, frame, onjob, onlayer, onframe):
    """Creates a frame on frame dependency
    @type job: string
    @param job: the name of the dependant job
    @type layer: string
    @param layer: the name of the dependant layer
    @type frame: int
    @param frame: the number of the dependant frame
    @type onjob: string
    @param onjob: the name of the job to depend on
    @type onlayer: string
    @param onlayer: the name of the layer to depend on
    @type onframe: int
    @param onframe: the number of the frame to depend on
    @rtype: Depend
    @return: the created dependency"""

    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(layer, ERR_INVALID_ER_LAYER)
    __is_valid(frame, ERR_INVALID_ER_FRAME)
    __is_valid(onjob, ERR_INVALID_ON_JOB)
    __is_valid(onlayer, ERR_INVALID_ON_LAYER)
    __is_valid(onframe, ERR_INVALID_ON_FRAME)

    logger.debug(
        "creating fof depend from %s/%s-%04d to %s/%s-%04d",
        job, layer, frame, onjob, onlayer, onframe)
    depend_er_frame = opencue.api.findFrame(job, layer, frame)
    depend_on_frame = opencue.api.findFrame(onjob, onlayer, onframe)
    return depend_er_frame.createDependencyOnFrame(depend_on_frame)


def createFrameByFrameDepend(job, layer, onjob, onlayer):
    """Creates a frame by frame dependency
    @type job: string
    @param job: the name of the dependant job
    @type layer: string
    @param layer: the name of the dependant layer
    @type onjob: string
    @param onjob: the name of the job to depend on
    @type onlayer: string
    @param onlayer: the name of the layer to depend on
    @rtype: Depend
    @return: the created dependency"""

    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(layer, ERR_INVALID_ER_LAYER)
    __is_valid(onjob, ERR_INVALID_ON_JOB)
    __is_valid(onlayer, ERR_INVALID_ON_LAYER)

    logger.debug("creating fbf depend from %s/%s to %s/%s", job, layer, onjob, onlayer)

    depend_er_layer = opencue.api.findLayer(job, layer)
    depend_on_layer = opencue.api.findLayer(onjob, onlayer)
    return depend_er_layer.createFrameByFrameDependency(depend_on_layer)


def createLayerOnSimFrameDepend(job, layer, onjob, onlayer, onframe):
    """Creates a layer on sim frame dependency
    @type job: string
    @param job: the name of the dependant job
    @type layer: string
    @param layer: the name of the dependant layer
    @type onjob: string
    @param onjob: the name of the job to depend on
    @type onlayer: string
    @param onlayer: the name of the layer to depend on
    @type onframe: int
    @param onframe: the number of the frame to depend on
    @rtype: Depend
    @return: the created dependency"""

    __is_valid(job, ERR_INVALID_ER_JOB)
    __is_valid(layer, ERR_INVALID_ER_LAYER)
    __is_valid(onjob, ERR_INVALID_ON_JOB)
    __is_valid(onlayer, ERR_INVALID_ON_LAYER)
    __is_valid(onframe, ERR_INVALID_ON_FRAME)

    logger.debug(
        "creating los depend from %s/%s to %s/%s-%04d", job, layer, onjob, onlayer, onframe)
    depend_er_layer = opencue.api.findLayer(job,layer)
    depend_on_frame = opencue.api.findFrame(onjob, onlayer, onframe)

    depends = []
    for depend_er_frame in depend_er_layer.getFrames():
        depends.append(depend_er_frame.createDependencyOnFrame(depend_on_frame))
    return depends


def dropDepend(depend_id):
    """deactivates a dependency by GUID
    @type depend_id: string
    @param depend_id: the GUID of the dependency"""
    opencue.api.getDepend(depend_id).satisfy()
