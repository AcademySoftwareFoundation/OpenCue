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

"""Monitoring and Historical Data Access Wrappers.

This module provides access to historical render farm statistics including
job history, frame history, layer memory usage, and host metrics over time.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

# Import monitoring_pb2 - this module should only be used when monitoring is available
try:
    from opencue_proto import monitoring_pb2
except ImportError:
    monitoring_pb2 = None

from opencue.cuebot import Cuebot
from opencue import util


class HistoricalJob:
    """Represents a historical job record from the monitoring system."""

    def __init__(self, data):
        self.data = data

    @property
    def id(self):
        """Returns the job ID."""
        return self.data.id

    @property
    def name(self):
        """Returns the job name."""
        return self.data.name

    @property
    def show(self):
        """Returns the show name."""
        return self.data.show

    @property
    def shot(self):
        """Returns the shot name."""
        return self.data.shot

    @property
    def user(self):
        """Returns the username who submitted the job."""
        return self.data.user

    @property
    def facility(self):
        """Returns the facility name."""
        return self.data.facility

    @property
    def finalState(self):
        """Returns the final job state."""
        return self.data.final_state

    @property
    def startTime(self):
        """Returns the job start time as Unix timestamp."""
        return self.data.start_time

    @property
    def stopTime(self):
        """Returns the job stop time as Unix timestamp."""
        return self.data.stop_time

    @property
    def priority(self):
        """Returns the job priority."""
        return self.data.priority

    @property
    def totalFrames(self):
        """Returns the total number of frames."""
        return self.data.total_frames

    @property
    def succeededFrames(self):
        """Returns the number of succeeded frames."""
        return self.data.succeeded_frames

    @property
    def failedFrames(self):
        """Returns the number of failed frames."""
        return self.data.failed_frames

    @property
    def totalCoreSeconds(self):
        """Returns total core-seconds consumed."""
        return self.data.total_core_seconds

    @property
    def totalGpuSeconds(self):
        """Returns total GPU-seconds consumed."""
        return self.data.total_gpu_seconds

    @property
    def maxRss(self):
        """Returns maximum RSS memory usage in KB."""
        return self.data.max_rss

    def __repr__(self):
        return f"HistoricalJob({self.name})"


class HistoricalFrame:
    """Represents a historical frame record from the monitoring system."""

    def __init__(self, data):
        self.data = data

    @property
    def id(self):
        """Returns the frame ID."""
        return self.data.id

    @property
    def name(self):
        """Returns the frame name."""
        return self.data.name

    @property
    def layerName(self):
        """Returns the layer name."""
        return self.data.layer_name

    @property
    def jobName(self):
        """Returns the job name."""
        return self.data.job_name

    @property
    def show(self):
        """Returns the show name."""
        return self.data.show

    @property
    def frameNumber(self):
        """Returns the frame number."""
        return self.data.frame_number

    @property
    def finalState(self):
        """Returns the final frame state."""
        return self.data.final_state

    @property
    def exitStatus(self):
        """Returns the exit status code."""
        return self.data.exit_status

    @property
    def retryCount(self):
        """Returns the number of retries."""
        return self.data.retry_count

    @property
    def startTime(self):
        """Returns the start time as Unix timestamp."""
        return self.data.start_time

    @property
    def stopTime(self):
        """Returns the stop time as Unix timestamp."""
        return self.data.stop_time

    @property
    def maxRss(self):
        """Returns maximum RSS memory usage in KB."""
        return self.data.max_rss

    @property
    def lastHost(self):
        """Returns the last host that ran this frame."""
        return self.data.last_host

    @property
    def totalCoreTime(self):
        """Returns total core time in seconds."""
        return self.data.total_core_time

    @property
    def totalGpuTime(self):
        """Returns total GPU time in seconds."""
        return self.data.total_gpu_time

    def __repr__(self):
        return f"HistoricalFrame({self.name})"


class HistoricalLayer:
    """Represents a historical layer record from the monitoring system."""

    def __init__(self, data):
        self.data = data

    @property
    def id(self):
        """Returns the layer ID."""
        return self.data.id

    @property
    def name(self):
        """Returns the layer name."""
        return self.data.name

    @property
    def jobName(self):
        """Returns the job name."""
        return self.data.job_name

    @property
    def show(self):
        """Returns the show name."""
        return self.data.show

    @property
    def layerType(self):
        """Returns the layer type."""
        return self.data.type

    @property
    def tags(self):
        """Returns the layer tags."""
        return list(self.data.tags)

    @property
    def services(self):
        """Returns the layer services."""
        return list(self.data.services)

    @property
    def totalFrames(self):
        """Returns the total number of frames."""
        return self.data.total_frames

    @property
    def succeededFrames(self):
        """Returns the number of succeeded frames."""
        return self.data.succeeded_frames

    @property
    def failedFrames(self):
        """Returns the number of failed frames."""
        return self.data.failed_frames

    @property
    def totalCoreSeconds(self):
        """Returns total core-seconds consumed."""
        return self.data.total_core_seconds

    @property
    def totalGpuSeconds(self):
        """Returns total GPU-seconds consumed."""
        return self.data.total_gpu_seconds

    @property
    def maxRss(self):
        """Returns maximum RSS memory usage in KB."""
        return self.data.max_rss

    @property
    def avgFrameSeconds(self):
        """Returns average frame render time in seconds."""
        return self.data.avg_frame_seconds

    def __repr__(self):
        return f"HistoricalLayer({self.name})"


class LayerMemoryRecord:
    """Represents a historical layer memory usage record."""

    def __init__(self, data):
        self.data = data

    @property
    def jobName(self):
        """Returns the job name."""
        return self.data.job_name

    @property
    def layerName(self):
        """Returns the layer name."""
        return self.data.layer_name

    @property
    def show(self):
        """Returns the show name."""
        return self.data.show

    @property
    def timestamp(self):
        """Returns the timestamp as Unix epoch."""
        return self.data.timestamp

    @property
    def maxRss(self):
        """Returns maximum RSS memory usage in KB."""
        return self.data.max_rss

    @property
    def reservedMemory(self):
        """Returns reserved memory in KB."""
        return self.data.reserved_memory

    @property
    def frameCount(self):
        """Returns the number of frames in this record."""
        return self.data.frame_count

    @property
    def avgFrameMemory(self):
        """Returns average frame memory usage in KB."""
        return self.data.avg_frame_memory

    @property
    def p95FrameMemory(self):
        """Returns 95th percentile frame memory usage in KB."""
        return self.data.p95_frame_memory

    def __repr__(self):
        return f"LayerMemoryRecord({self.layerName}@{self.timestamp})"


class FarmStatistics:
    """Represents a snapshot of farm-wide statistics."""

    def __init__(self, data):
        self.data = data

    @property
    def snapshotTime(self):
        """Returns the timestamp of this snapshot."""
        return self.data.snapshot_time

    @property
    def totalJobs(self):
        """Returns total number of jobs."""
        return self.data.total_jobs

    @property
    def pendingJobs(self):
        """Returns number of pending jobs."""
        return self.data.pending_jobs

    @property
    def finishedJobs(self):
        """Returns number of finished jobs."""
        return self.data.finished_jobs

    @property
    def totalFrames(self):
        """Returns total number of frames."""
        return self.data.total_frames

    @property
    def waitingFrames(self):
        """Returns number of waiting frames."""
        return self.data.waiting_frames

    @property
    def runningFrames(self):
        """Returns number of running frames."""
        return self.data.running_frames

    @property
    def succeededFrames(self):
        """Returns number of succeeded frames."""
        return self.data.succeeded_frames

    @property
    def deadFrames(self):
        """Returns number of dead frames."""
        return self.data.dead_frames

    @property
    def totalHosts(self):
        """Returns total number of hosts."""
        return self.data.total_hosts

    @property
    def upHosts(self):
        """Returns number of hosts in UP state."""
        return self.data.up_hosts

    @property
    def downHosts(self):
        """Returns number of hosts in DOWN state."""
        return self.data.down_hosts

    @property
    def totalCores(self):
        """Returns total cores in the farm."""
        return self.data.total_cores

    @property
    def runningCores(self):
        """Returns number of cores currently running frames."""
        return self.data.running_cores

    @property
    def idleCores(self):
        """Returns number of idle cores."""
        return self.data.idle_cores

    @property
    def showStats(self):
        """Returns per-show statistics."""
        return [ShowStatistics(s) for s in self.data.show_stats]

    def __repr__(self):
        return f"FarmStatistics({self.snapshotTime})"


class ShowStatistics:
    """Represents per-show statistics within a farm snapshot."""

    def __init__(self, data):
        self.data = data

    @property
    def show(self):
        """Returns the show name."""
        return self.data.show

    @property
    def pendingJobs(self):
        """Returns number of pending jobs for this show."""
        return self.data.pending_jobs

    @property
    def runningFrames(self):
        """Returns number of running frames for this show."""
        return self.data.running_frames

    @property
    def waitingFrames(self):
        """Returns number of waiting frames for this show."""
        return self.data.waiting_frames

    @property
    def reservedCores(self):
        """Returns reserved cores for this show."""
        return self.data.reserved_cores

    @property
    def reservedGpus(self):
        """Returns reserved GPUs for this show."""
        return self.data.reserved_gpus

    def __repr__(self):
        return f"ShowStatistics({self.show})"


class TimeRange:
    """Represents a time range for historical queries."""

    def __init__(self, start_time, end_time):
        """
        Create a time range.

        :param start_time: Start time as Unix epoch milliseconds
        :param end_time: End time as Unix epoch milliseconds
        """
        self.start_time = start_time
        self.end_time = end_time

    def toProto(self):
        """Convert to protobuf TimeRange message."""
        return monitoring_pb2.TimeRange(
            start_time=self.start_time,
            end_time=self.end_time
        )


# API Functions for Historical Data Access

@util.grpcExceptionParser
def getJobHistory(shows=None, users=None, shots=None, job_name_regex=None,
                  states=None, time_range=None, page=1, page_size=100, max_results=1000):
    """
    Query historical job records with optional filters.

    :param shows: List of show names to filter by
    :param users: List of usernames to filter by
    :param shots: List of shot names to filter by
    :param job_name_regex: Regular expression pattern for job names
    :param states: List of job states to filter by
    :param time_range: TimeRange object for time-based filtering
    :param page: Page number for pagination (1-indexed)
    :param page_size: Number of results per page
    :param max_results: Maximum total results to return
    :rtype: list[HistoricalJob]
    :return: List of HistoricalJob objects
    """
    request = monitoring_pb2.GetJobHistoryRequest(
        shows=shows or [],
        users=users or [],
        shots=shots or [],
        job_name_regex=job_name_regex or [],
        states=states or [],
        page=page,
        page_size=page_size,
        max_results=max_results
    )

    if time_range:
        request.time_range.CopyFrom(time_range.toProto())

    response = Cuebot.getStub('monitoring').GetJobHistory(
        request, timeout=Cuebot.Timeout)

    return [HistoricalJob(j) for j in response.jobs]


@util.grpcExceptionParser
def getFrameHistory(job_id=None, job_name=None, layer_names=None, states=None,
                    time_range=None, page=1, page_size=100):
    """
    Query historical frame records for a specific job.

    :param job_id: Job ID to query (required if job_name not provided)
    :param job_name: Job name to query (required if job_id not provided)
    :param layer_names: List of layer names to filter by
    :param states: List of frame states to filter by
    :param time_range: TimeRange object for time-based filtering
    :param page: Page number for pagination (1-indexed)
    :param page_size: Number of results per page
    :rtype: list[HistoricalFrame]
    :return: List of HistoricalFrame objects
    """
    request = monitoring_pb2.GetFrameHistoryRequest(
        job_id=job_id or "",
        job_name=job_name or "",
        layer_names=layer_names or [],
        states=states or [],
        page=page,
        page_size=page_size
    )

    if time_range:
        request.time_range.CopyFrom(time_range.toProto())

    response = Cuebot.getStub('monitoring').GetFrameHistory(
        request, timeout=Cuebot.Timeout)

    return [HistoricalFrame(f) for f in response.frames]


@util.grpcExceptionParser
def getLayerHistory(job_id=None, job_name=None, time_range=None, page=1, page_size=100):
    """
    Query historical layer records for a specific job.

    :param job_id: Job ID to query (required if job_name not provided)
    :param job_name: Job name to query (required if job_id not provided)
    :param time_range: TimeRange object for time-based filtering
    :param page: Page number for pagination (1-indexed)
    :param page_size: Number of results per page
    :rtype: list[HistoricalLayer]
    :return: List of HistoricalLayer objects
    """
    request = monitoring_pb2.GetLayerHistoryRequest(
        job_id=job_id or "",
        job_name=job_name or "",
        page=page,
        page_size=page_size
    )

    if time_range:
        request.time_range.CopyFrom(time_range.toProto())

    response = Cuebot.getStub('monitoring').GetLayerHistory(
        request, timeout=Cuebot.Timeout)

    return [HistoricalLayer(layer) for layer in response.layers]


@util.grpcExceptionParser
def getLayerMemoryHistory(layer_name, shows=None, time_range=None, max_results=1000):
    """
    Query historical memory usage for a specific layer type.
    This is useful for memory prediction based on historical data.

    :param layer_name: Layer name pattern to query
    :param shows: List of show names to filter by
    :param time_range: TimeRange object for time-based filtering
    :param max_results: Maximum number of records to return
    :rtype: list[LayerMemoryRecord]
    :return: List of LayerMemoryRecord objects
    """
    request = monitoring_pb2.GetLayerMemoryHistoryRequest(
        layer_name=layer_name,
        shows=shows or [],
        max_results=max_results
    )

    if time_range:
        request.time_range.CopyFrom(time_range.toProto())

    response = Cuebot.getStub('monitoring').GetLayerMemoryHistory(
        request, timeout=Cuebot.Timeout)

    return [LayerMemoryRecord(r) for r in response.records]


@util.grpcExceptionParser
def getFarmStatistics(time_range=None, interval_minutes=60, shows=None):
    """
    Query aggregated farm statistics over a time range.

    :param time_range: TimeRange object for time-based filtering
    :param interval_minutes: Aggregation interval in minutes
    :param shows: List of show names to filter by
    :rtype: list[FarmStatistics]
    :return: List of FarmStatistics snapshots
    """
    request = monitoring_pb2.GetFarmStatisticsRequest(
        interval_minutes=interval_minutes,
        shows=shows or []
    )

    if time_range:
        request.time_range.CopyFrom(time_range.toProto())

    response = Cuebot.getStub('monitoring').GetFarmStatistics(
        request, timeout=Cuebot.Timeout)

    return [FarmStatistics(s) for s in response.statistics]
