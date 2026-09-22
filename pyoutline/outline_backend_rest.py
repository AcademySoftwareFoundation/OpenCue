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

import base64
import hashlib
import hmac
import json
import logging
import sys
import time

import requests

import outline
import outline.depend
import outline.exception
import outline.util
import outline.versions.main

from outline.backend import serialize
from outline.backend import serialize_simple

__all__ = ["launch",
           "serialize",
           "serialize_simple"]

logger = logging.getLogger("outline_backend_rest")

JOB_WAIT_PERIOD_SEC = 5
TIMEOUT = 10
CUEREST_GATEWAY_URL = outline.config.get("backend:rest", "cuerest_gateway_url")
CUEREST_SESSION = None


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

    session = _get_restgateway_session()
    spec = launcher.serialize(use_pycuerun=use_pycuerun)
    json_data = {"spec": spec}
    response = session.post(f"{CUEREST_GATEWAY_URL}/job.JobInterface/LaunchSpecAndWait",
                            json=json_data,
                            timeout=TIMEOUT)
    response.raise_for_status()
    jobs = response.json().get("jobs", {}).get("jobs", {})
    session.close()

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

    :type job: dict
    :param job: The job data dictionary to test.
    """
    logging.basicConfig(level=logging.DEBUG)
    job_data = job.get("data", job) if isinstance(job, dict) else job.data
    job_name = job_data.get("name") if isinstance(job_data, dict) else job.name()
    job_id = job_data.get("id") if isinstance(job_data, dict) else job.id()
    logger.info("Entering test mode for job: %s", job_name)

    session = _get_restgateway_session()
    try:
        # Unpause the job.
        session.post(
            f"{CUEREST_GATEWAY_URL}/job.JobInterface/Resume",
            json={"job": {"id": job_id}},
            timeout=TIMEOUT,
        ).raise_for_status()

        while True:
            try:
                response = session.post(
                    f"{CUEREST_GATEWAY_URL}/job.JobInterface/GetJob",
                    json={"id": job_id},
                    timeout=TIMEOUT,
                )
                if response.status_code == 404:
                    break
                response.raise_for_status()
                job_info = response.json().get("job", {})
                stats = job_info.get("jobStats", {})

                dead_frames = stats.get("deadFrames", 0)
                eaten_frames = stats.get("eatenFrames", 0)
                if dead_frames + eaten_frames > 0:
                    raise outline.exception.OutlineException(
                        "Job test failed, dead or eaten frames on: %s" % job_name
                    )

                state = job_info.get("state")
                if state in ("FINISHED", 1):
                    break

                logger.debug(
                    "waiting on %s job to complete: %d/%d",
                    job_name,
                    stats.get("succeededFrames", 0),
                    stats.get("totalFrames", 0),
                )
            except requests.RequestException as ie:
                raise outline.exception.OutlineException(
                    "test for job %s failed: %s" % (job_name, ie)
                )
            time.sleep(5)
    finally:
        try:
            session.post(
                f"{CUEREST_GATEWAY_URL}/job.JobInterface/Kill",
                json={"job": {"id": job_id}},
                timeout=TIMEOUT,
            )
        except Exception:
            print("Excepted error while killing job: %s" % job_name, file=sys.stderr)
        session.close()


def wait(job):
    """
    Wait for the given job to complete before returning.

    :type job: dict
    :param job: The job data dictionary to wait on.
    """
    job_id = job.get("id") if isinstance(job, dict) else job.data.id
    session = _get_restgateway_session()
    try:
        while True:
            try:
                job_response = session.post(
                    f"{CUEREST_GATEWAY_URL}/job.JobInterface/GetJob",
                    json={"id": job_id},
                    timeout=TIMEOUT,
                )
                job_response.raise_for_status()
                job_data = job_response.json().get("job", {})
                if job_data.get("state") in ("FINISHED", 1):
                    break
                stats = job_data.get("job_stats", {})

                logger.debug(
                    "waiting on %s job to complete: %d/%d",
                    job_id,
                    stats.get("succeeded_frames", 0),
                    stats.get("total_frames", 0),
                )
            except requests.RequestException as ie:
                print(
                    "opencue error waiting on job: %s, %s. Will continue to wait."
                    % (job_id, ie),
                    file=sys.stderr,
                )
            time.sleep(JOB_WAIT_PERIOD_SEC)
    finally:
        session.close()

def _get_jwt_token():
    jwt_secret = outline.config.get("backend:rest", "jwt_secret")
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": "jimmy", "exp": int(time.time()) + 3600}
    h = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    m = f"{h}.{p}"
    s = (
        base64.urlsafe_b64encode(
            hmac.new(
                jwt_secret.encode(),
                m.encode(),
                hashlib.sha256,
            ).digest()
        )
        .decode()
        .rstrip("=")
    )
    return f'{m}.{s}'

def _get_restgateway_session():
    rest_gateway_session = requests.Session()
    rest_gateway_session.headers.update({"Authorization": f"Bearer {_get_jwt_token()}"})
    return rest_gateway_session
