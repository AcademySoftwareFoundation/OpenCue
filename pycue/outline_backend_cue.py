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

"""
OpenCue backend module.

Uses the OpenCue Python API to submit the given job to OpenCue for processing.

See outline.backend for a description of the PyOutline backend system.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import logging
import sys
import time

import outline
import outline.depend
import outline.exception
import outline.util
import outline.versions.main

from outline.backend import serialize
from outline.backend import serialize_simple

import opencue

__all__ = ["launch",
           "serialize",
           "serialize_simple"]

logger = logging.getLogger("outline_backend_cue")

JOB_WAIT_PERIOD_SEC = 5



def launch(launcher, use_pycuerun=True):
    """
    Launch the given L{OutlineLauncher}.

    :type launcher: L{OutlineLauncher}
    :param launcher: The OutlineLauncher to launch.
    :type use_pycuerun: bool
    :param use_pycuerun: Enable/Disable pycuerun.

    :rtype: opencue.Entity.Job
    :return: The opencue job that was launched.
    """

    if launcher.get("server"):
        opencue.Cuebot.setHosts([launcher.get("server")])
        logger.info("cuebot host set to: %s", launcher.get("server"))

    jobs = opencue.api.launchSpecAndWait(launcher.serialize(use_pycuerun=use_pycuerun))

    if launcher.get("wait"):
        wait(jobs[0])
    elif launcher.get("test"):
        test(jobs[0])

    return jobs


def test(job):
    """
    Test the given job.  This function returns immediately
    when the given job completes, or throws an L{OutlineException}
    if the job fails in any way.

    :type job: opencue.Entity.Job
    :param job: The job to test.
    """
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Entering test mode for job: %s", job.data.name)

    # Unpause the job.
    job.resume()

    try:
        while True:
            try:
                job = opencue.api.getJob(job.id())
                if job.data.job_stats.dead_frames + job.data.job_stats.eaten_frames > 0:
                    raise outline.exception.OutlineException(
                        "Job test failed, dead or eaten frames on: %s" % job.data.name)
                if job.data.state == opencue.api.job_pb2.FINISHED:
                    break
                logger.debug(
                    "waiting on %s job to complete: %d/%d", job.data.name,
                    job.data.job_stats.succeeded_frames, job.data.job_stats.total_frames)
            except opencue.CueException as ie:
                raise outline.exception.OutlineException(
                    "test for job %s failed: %s" % (job.data.name, ie))
            time.sleep(5)
    finally:
        job.kill()


def wait(job):
    """
    Wait for the given job to complete before returning.

    :type job: opencue.Entity.Job
    :param job: The job to wait on.
    """
    while True:
        try:
            if not opencue.api.isJobPending(job.data.name):
                break
            logger.debug(
                "waiting on %s job to complete: %d/%d", job.data.name,
                job.data.job_stats.succeeded_frames, job.data.job_stats.total_frames)
        except opencue.CueException as ie:
            print(
                "opencue error waiting on job: %s, %s. Will continue to wait." % (
                    job.data.name, ie),
                file=sys.stderr)
        time.sleep(JOB_WAIT_PERIOD_SEC)
