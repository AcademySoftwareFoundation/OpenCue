#!/usr/bin/env python
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

"""Basic script that waits for a job to complete."""

import argparse
import datetime
import logging
import sys
import time

import opencue
from opencue.wrappers.job import Job


def wait_for_job(job_name, timeout_sec=None):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    logging.info('Waiting for job %s...', job_name)
    start_time = datetime.datetime.now()
    while True:
        if (datetime.datetime.now() - start_time).seconds > timeout_sec:
            logging.error('Timed out')
            return False
        jobs = opencue.api.getJobs(job=[job_name], include_finished=True)
        if not jobs:
            logging.error("Job %s not found", job_name)
            return False
        job = jobs[0]
        logging.info('Job state = %s', Job.JobState(job.state()).name)
        if job.state() == Job.JobState.FINISHED:
            logging.info('Job succeeded')
            return True
        if job.deadFrames() > 0:
            logging.error('Job is failing')
            return False
        time.sleep(5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("job_name", help="name of the job to wait for")
    parser.add_argument("--timeout", help="number of seconds to wait before timing out", type=int)
    args = parser.parse_args()
    result = wait_for_job(args.job_name, timeout_sec=args.timeout)
    if not result:
        sys.exit(1)
